/**
 * Canonical OKF v0.2 Specification Engine for Flow.
 *
 * Owns spec status, scaffolding, markdown document reading, plan import,
 * dependency DAG calculation, preflight checks, zero-token checklist/frontmatter sync,
 * claim release, and spec closeout across CLI, workflows, MCP, and Studio UI.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import {
  expectedMarkerForState,
  isClosedState,
  isExistingDir,
  readJsonSafe,
  readTextSafe,
  resolveConfinedPath,
  sha256Hex,
  sharedParseMemo,
  stateFromChecklistMarker,
  toPosixRelative,
  uriToWorkspacePath,
  walkMarkdownFiles,
  writeJsonAtomic,
  writeTextAtomic,
} from "../core/fs-io.mjs";
import {
  FrontmatterCodec,
  FrontmatterDocument,
  extractHeadings,
  extractTruthBlock,
  hasOrderedRequiredHeadings,
  scanWikilinks,
} from "../core/frontmatter.mjs";
import { resolveWorktreeContext } from "../core/worktree.mjs";
import { SpecComment, SpecFeedbackStore, resolveAuthorIdentity } from "./feedback.mjs";

const VALID_SLUG_RE = /^[a-z0-9][a-z0-9-]{1,62}$/;
const HEX_SHA_RE = /^[0-9a-fA-F]{7,40}$/;
const CHECKLIST_LINE_RE = /^(\s*-\s*)\[([ xX~!>-])\](\s*)(?:\[([0-9a-fA-F]{6,40})\]\s*)?(.+)$/;

export const FULL_TASK_HEADINGS = Object.freeze([
  "Objective & Scope Boundary",
  "Bounded Read Manifest",
  "Symbol & Signature Contracts",
  "Edge Cases & Error Semantics",
  "Public-Seam Test Blueprint",
  "Verification",
  "Acceptance Criteria",
  "Notes & Discoveries",
]);

export const COMPACT_TASK_HEADINGS = Object.freeze([
  "Objective & Scope Boundary",
  "Bounded Read Manifest",
  "Contracts & Edge Cases",
  "Test Matrix",
  "Verification",
  "Acceptance Criteria",
]);

/**
 * Parse a file's frontmatter through the process mtime-keyed parse memo.
 *
 * @param {string} absPath
 * @returns {FrontmatterDocument | null}
 */
function parseFileMemoized(absPath) {
  return sharedParseMemo.readAndParse(absPath, (raw) => FrontmatterDocument.parse(raw));
}

/**
 * Read task worksheet Markdown into a normalized task object.
 *
 * @param {string} taskFile
 * @param {string} agentsBaseRoot
 * @param {{ flowId: string, chapterId?: string | null }} context
 */
function readTaskWorksheet(taskFile, agentsBaseRoot, { flowId, chapterId = null }) {
  const raw = readTextSafe(taskFile) || "";
  const doc = FrontmatterDocument.parse(raw);
  const filename = path.basename(taskFile);
  const fileBase = path.basename(taskFile, ".md");
  const stem = fileBase.split("-")[0];
  const chPrefix = chapterId ? chapterId.split("-")[0] : null;
  const fallbackId = chPrefix ? `${flowId}:${chPrefix}:${stem}` : `${flowId}:${stem}`;
  const rawId = doc.text("id") || doc.text("task_id") || fallbackId;
  const shortId = rawId.includes(":") ? rawId.split(":").pop() : stem;
  const headingTitle = doc.body.match(/^#\s+(.+?)\s*$/m)?.[1] || fileBase;
  const title = doc.text("title") || headingTitle;
  const state = (doc.text("state") || doc.text("status") || "pending").toLowerCase();

  let inFence = false;
  let inVerification = false;
  let verificationBody = "";
  const symbolRefs = [];
  for (const line of doc.body.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) {
      if (inVerification) verificationBody += `${line}\n`;
      continue;
    }
    if (line.trim().startsWith("## ")) {
      inVerification = line.trim().slice(3).trim() === "Verification";
      continue;
    }
    if (inVerification && line.trim()) verificationBody += `${line}\n`;
    for (const m of line.matchAll(/`([^`\s]+::[A-Za-z_][\w.]*)`/g)) {
      symbolRefs.push(m[1]);
    }
  }

  return {
    id: rawId,
    short_id: shortId,
    stem,
    filename,
    chapter_id: chapterId || doc.text("chapter_id") || null,
    title,
    state,
    worksheet_format: (doc.text("worksheet_format") || "compact").toLowerCase(),
    verification_strategy: doc.text("verification_strategy") || doc.text("verification") || null,
    has_verification_body: Boolean(verificationBody.trim()),
    depends_on: doc.textList("depends_on"),
    read_set: doc.textList("read_set"),
    files: doc.textList("files"),
    tests: doc.textList("tests"),
    estimated_loc: doc.integer("estimated_loc"),
    plan_revision: doc.integer("plan_revision"),
    commit: doc.text("commit_sha") || doc.text("commit") || null,
    claimed_by: doc.text("claimed_by") || null,
    claimed_at: doc.text("claimed_at") || null,
    headings: extractHeadings(doc.body, { minLevel: 2, maxLevel: 2 }).map((h) => h.text),
    symbol_refs: symbolRefs,
    abs_path: taskFile,
    rel_path: toPosixRelative(agentsBaseRoot, taskFile),
  };
}

/**
 * Reconcile checklist markers and SHAs from an owning `spec.md` onto parsed tasks.
 *
 * @param {string} body
 * @param {ReturnType<typeof readTaskWorksheet>[]} tasks
 * @param {{ flowId: string, chapterId?: string | null, specRelPath: string, specAbsPath: string }} ctx
 */
function reconcileChecklistWithTasks(body, tasks, { flowId, chapterId = null, specRelPath, specAbsPath }) {
  const checklistItems = [];
  let inFence = false;
  for (const line of String(body || "").split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = line.match(CHECKLIST_LINE_RE);
    if (!m) continue;
    checklistItems.push({
      state: stateFromChecklistMarker(m[2]),
      commit: m[4] || null,
      label: m[5].trim(),
    });
  }

  if (tasks.length === 0) {
    return checklistItems.map((item, idx) => {
      const short = `t${String(idx + 1).padStart(2, "0")}`;
      const chPrefix = chapterId ? `${chapterId.split("-")[0]}:` : "";
      return {
        id: `${flowId}:${chPrefix}${short}`,
        short_id: short,
        stem: short,
        filename: null,
        chapter_id: chapterId,
        title: item.label,
        state: item.state,
        worksheet_format: "checklist",
        verification_strategy: null,
        has_verification_body: false,
        depends_on: [],
        read_set: [],
        files: [],
        tests: [],
        estimated_loc: null,
        plan_revision: null,
        commit: item.commit,
        claimed_by: null,
        claimed_at: null,
        headings: [],
        symbol_refs: [],
        abs_path: specAbsPath,
        rel_path: specRelPath,
      };
    });
  }

  for (const task of tasks) {
    const hit = checklistItems.find((item) => {
      if (task.filename && (item.label.includes(`tasks/${task.filename}`) || item.label.includes(`(${task.filename})`))) {
        return true;
      }
      if (item.label.includes(task.id)) return true;
      if (task.short_id && new RegExp(`\\b${task.short_id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i").test(item.label)) {
        return true;
      }
      return false;
    });
    if (hit) {
      if (task.state === "pending" && hit.state !== "pending") task.state = hit.state;
      if (!task.commit && hit.commit) task.commit = hit.commit;
    }
  }
  return tasks;
}

/**
 * Compute zero-based topological layers for DAG visualization.
 *
 * @param {string[]} ids
 * @param {Map<string, string[]>} depsMap
 * @returns {Map<string, number>}
 */
function computeTopologicalLayers(ids, depsMap) {
  const idSet = new Set(ids);
  /** @type {Map<string, number>} */
  const memo = new Map();
  /** @type {Set<string>} */
  const visiting = new Set();

  const visit = (id) => {
    if (memo.has(id)) return memo.get(id);
    if (visiting.has(id)) return 0;
    visiting.add(id);
    let maxDep = -1;
    for (const depId of depsMap.get(id) || []) {
      if (depId === id || !idSet.has(depId) || visiting.has(depId)) continue;
      const layer = visit(depId);
      if (layer > maxDep) maxDep = layer;
    }
    visiting.delete(id);
    const out = maxDep + 1;
    memo.set(id, out);
    return out;
  };
  for (const id of ids) visit(id);
  return memo;
}

/**
 * Resolve `rawDep` against `allTasks` matching full ids first and bare ids strictly within the same chapter.
 *
 * @param {any} ownerTask
 * @param {string} rawDep
 * @param {any[]} allTasks
 * @param {string} flowId
 */
export function resolveTaskDependency(ownerTask, rawDep, allTasks, flowId) {
  const dep = String(rawDep || "").trim();
  if (!dep) return null;
  const byId = allTasks.find((t) => t.id === dep);
  if (byId) return byId;

  const sameChapter = (cand, chHint) => {
    if (!chHint) return cand.chapter_id === ownerTask.chapter_id;
    return cand.chapter_id === chHint || (cand.chapter_id && cand.chapter_id.split("-")[0] === chHint.split("-")[0]);
  };
  const matchesTail = (cand, tail) =>
    cand.short_id === tail ||
    cand.stem === tail ||
    (cand.filename && cand.filename.replace(/\.md$/i, "") === tail);

  if (dep.includes(":")) {
    const parts = dep.split(":").filter(Boolean);
    const tail = parts[parts.length - 1];
    if (parts.length >= 3) {
      return allTasks.find((s) => sameChapter(s, parts[1]) && matchesTail(s, tail)) || null;
    }
    if (parts.length === 2) {
      const prefix = parts[0];
      if (prefix === flowId) {
        return allTasks.find((s) => sameChapter(s, null) && matchesTail(s, tail)) || null;
      }
      return allTasks.find((s) => sameChapter(s, prefix) && matchesTail(s, tail)) || null;
    }
  }
  return allTasks.find((s) => sameChapter(s, null) && matchesTail(s, dep)) || null;
}

export class SpecEngine {
  /**
   * @param {string | { workspacePath: string, env?: NodeJS.ProcessEnv }} workspaceOrOpts
   */
  constructor(workspaceOrOpts) {
    const isOpts = typeof workspaceOrOpts === "object" && workspaceOrOpts !== null;
    this.workspace = path.resolve(isOpts ? workspaceOrOpts.workspacePath : workspaceOrOpts);
    this.env = (isOpts && workspaceOrOpts.env) || process.env;
    this.worktree = resolveWorktreeContext(this.workspace);
    this.effectiveRoot = this.worktree.effectiveAgentsRoot;
    this.bundleRel = this.worktree.bundleRel;
    this.bundleDir = path.join(this.effectiveRoot, this.bundleRel);
    this.specsDir = path.join(this.bundleDir, "specs");
    this.feedback = new SpecFeedbackStore(this.workspace);
  }

  /**
   * Ensure `.agents/` setup-state and bundle root exist (`local-only` when `plugin.json` is present).
   *
   * @param {{ ignorePolicy?: string }} [options]
   */
  ensureInitialized({ ignorePolicy = null } = {}) {
    const agentsDir = path.join(this.effectiveRoot, ".agents");
    const setupPath = path.join(agentsDir, "setup-state.json");
    const existing = readJsonSafe(setupPath) || {};
    const hasPlugin = fs.existsSync(path.join(this.effectiveRoot, "plugin.json"));
    const policy =
      ignorePolicy ||
      existing?.workflow_preferences?.ignore_policy ||
      existing?.ignore_policy ||
      (hasPlugin ? "local-only" : "shared");

    fs.mkdirSync(this.bundleDir, { recursive: true });
    if (!fs.existsSync(setupPath)) {
      writeJsonAtomic(setupPath, {
        ...existing,
        setup_status: "complete",
        bundle_root: this.bundleRel,
        okf_version: "0.2",
        workflow_preferences: {
          ...(existing.workflow_preferences || {}),
          ignore_policy: policy,
        },
      });
    }
    if (policy === "local-only") {
      const gitExclude = path.join(this.effectiveRoot, ".git", "info", "exclude");
      if (fs.existsSync(path.dirname(gitExclude))) {
        const cur = readTextSafe(gitExclude) || "";
        if (!cur.split("\n").some((l) => l.trim() === ".agents/" || l.trim() === ".agents/*")) {
          writeTextAtomic(gitExclude, `${cur.trimEnd()}${cur.trimEnd() ? "\n" : ""}.agents/\n`);
        }
      }
    }
    const indexMd = path.join(this.bundleDir, "index.md");
    if (!fs.existsSync(indexMd)) {
      writeTextAtomic(
        indexMd,
        `---\nokf_version: "0.2"\nbundle: ${path.basename(this.effectiveRoot)}\n---\n\n# ${path.basename(this.effectiveRoot)} Bundle\n`,
      );
    }
    return { bundle_dir: this.bundleDir, ignore_policy: policy };
  }

  /**
   * List all specs sorted by lifecycle activity.
   *
   * @param {{ includeArchived?: boolean }} [options]
   */
  listSpecs({ includeArchived = false } = {}) {
    if (!isExistingDir(this.specsDir)) return [];
    const items = [];
    for (const ent of fs.readdirSync(this.specsDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!ent.isDirectory()) continue;
      const spec = this.#readSpecDir(path.join(this.specsDir, ent.name));
      if (!spec) continue;
      if (!includeArchived && spec.state === "archived") continue;
      items.push(spec);
    }
    const rank = { active: 0, in_progress: 0, planned: 1, draft: 2, paused: 3, completed: 4, archived: 5 };
    return items.sort((a, b) => (rank[a.state] ?? 3) - (rank[b.state] ?? 3) || a.flow_id.localeCompare(b.flow_id));
  }

  /**
   * Return single-spec or workspace-wide status summary + next runnable tasks.
   *
   * @param {string | null} [flowId]
   */
  status(flowId = null) {
    if (flowId) {
      const cleanId = String(flowId).trim();
      if (!cleanId || /[\\/]|\.\./.test(cleanId)) throw new Error(`Invalid flowId '${flowId}'`);
      const specDir = path.join(this.specsDir, cleanId);
      const spec = this.#readSpecDir(specDir);
      if (!spec) throw new Error(`Spec '${cleanId}' not found under ${this.bundleRel}/specs/.`);
      return {
        workspace: this.workspace,
        effective_root: this.effectiveRoot,
        bundle_root: this.bundleRel,
        spec,
        next_runnable: this.#computeNextForSpec(spec),
      };
    }
    const specs = this.listSpecs({ includeArchived: false });
    let nextRunnable = null;
    for (const s of specs) {
      if (isClosedState(s.state) || s.state === "paused") continue;
      nextRunnable = this.#computeNextForSpec(s);
      if (nextRunnable) break;
    }
    return {
      workspace: this.workspace,
      effective_root: this.effectiveRoot,
      bundle_root: this.bundleRel,
      specs,
      next_runnable: nextRunnable,
    };
  }

  /**
   * Read an arbitrary bundle/workspace Markdown document safely with headings and feedback attached.
   *
   * @param {string} relPath
   */
  readDocument(relPath) {
    const clean = String(relPath || "").replace(/\\/g, "/").trim();
    const baseRoot = clean.startsWith(".agents/") ? this.effectiveRoot : this.workspace;
    const target = resolveConfinedPath(baseRoot, clean);
    const raw = readTextSafe(target);
    if (raw === null) throw new Error(`Markdown document not found: ${relPath}`);
    const doc = FrontmatterDocument.parse(raw);
    const allLines = raw.split("\n");
    const headings = extractHeadings(doc.body, { minLevel: 1, maxLevel: 4, lineOffset: doc.frontmatterEndLine });
    const normalizedRel = toPosixRelative(baseRoot, target);
    const comments = this.feedback.list(normalizedRel);
    return {
      relPath: normalizedRel,
      title: doc.text("title") || headings[0]?.text || path.basename(target, ".md"),
      frontmatter: doc.data,
      frontmatterEndLine: doc.frontmatterEndLine,
      truthBlock: extractTruthBlock(doc.body),
      headings,
      raw,
      lines: allLines.map((text, idx) => ({ lineNumber: idx + 1, text })),
      comments,
      flowId: doc.text("flow_id") || this.feedback.inferFlowId(normalizedRel),
    };
  }

  /**
   * Scaffold a new Feature Spec or Master PRD inside `.agents/bundles/specs/<flow_id>/`.
   *
   * @param {Record<string, any>} payload
   */
  scaffold(payload = {}) {
    const rawId = String(payload.flowId || payload.flow_id || "").trim();
    const slugSrc = rawId || String(payload.title || payload.problem || "").trim();
    let flowId = slugSrc
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 63)
      .replace(/-+$/g, "");
    if (!rawId && flowId.length === 1) flowId = `${flowId}-spec`;
    if (!VALID_SLUG_RE.test(flowId)) {
      throw new Error(`Invalid spec slug '${payload.flowId || flowId}'. Use lowercase letters, digits, and hyphens.`);
    }

    this.ensureInitialized();
    const specDir = path.join(this.specsDir, flowId);
    const specFile = path.join(specDir, "spec.md");
    if (fs.existsSync(specFile)) {
      throw new Error(`Specification '${flowId}' already exists at ${this.bundleRel}/specs/${flowId}/spec.md`);
    }

    const title = String(payload.title || "").trim() || flowId;
    const kind = payload.kind === "PRD" ? "PRD" : "Spec";
    const hasChapters = Boolean(payload.hasChapters || kind === "PRD");
    const problem = String(payload.problem || "Define problem context and target outcomes.").trim();
    const goals = String(payload.goals || "- Establish public-seam contracts and verification gates.").trim();

    const fmLines = [
      "---",
      `type: ${kind}`,
      `flow_id: ${flowId}`,
      `title: ${JSON.stringify(title)}`,
      `description: ${JSON.stringify(problem.split("\n")[0].slice(0, 140))}`,
      "status: draft",
      "state: draft",
      `has_chapters: ${hasChapters ? "true" : "false"}`,
      ...(payload.parentPrd ? [`parent_prd: ${String(payload.parentPrd).trim()}`] : []),
      ...(hasChapters && kind === "Spec" ? ["current_chapter: ch01-foundation"] : []),
      "---",
      "",
    ];
    const bodyLines = [
      `# ${title}`,
      "",
      "## 1. Problem & Context",
      "",
      problem,
      "",
      "## 2. Goals & Non-Goals",
      "",
      goals,
      "",
      "## 3. Architecture & Public Seams",
      "",
      "- Document module boundaries, alternatives evaluated, and verification strategy.",
      "",
      "## 4. Roadmap Checklist",
      "",
      hasChapters
        ? "- [ ] `ch01-foundation` — Initial vertical-slice foundation"
        : "- [ ] `t01` — Initial vertical-slice implementation",
      "",
    ];
    writeTextAtomic(specFile, `${fmLines.join("\n")}${bodyLines.join("\n")}`);

    if (hasChapters && kind === "Spec") {
      const ch01 = path.join(specDir, "chapters", "ch01-foundation");
      fs.mkdirSync(path.join(ch01, "tasks"), { recursive: true });
      writeTextAtomic(
        path.join(specDir, "chapters", "index.md"),
        `# ${title} — Chapter Catalog\n\n- [ ] [ch01-foundation](ch01-foundation/spec.md) — Initial vertical-slice foundation\n`,
      );
      writeTextAtomic(
        path.join(ch01, "spec.md"),
        [
          "---",
          "type: Spec",
          `flow_id: ${flowId}`,
          "chapter_id: ch01-foundation",
          `title: ${JSON.stringify(`${title} — Chapter 01`)}`,
          "status: draft",
          "state: pending",
          "planning_status: complete",
          "---",
          "",
          "# Chapter 01 — Foundation",
          "",
          "- [ ] `t01` — Define public seam and vertical-slice tests",
          "",
        ].join("\n"),
      );
    }

    const relPath = toPosixRelative(this.effectiveRoot, specFile);
    return {
      flowId,
      kind,
      title,
      relPath,
      absPath: specFile,
      dispatchCommand: kind === "PRD" ? `/flow:prd ${flowId} — ${title}` : `/flow:spec ${flowId} — ${title}`,
    };
  }

  /**
   * Materialize an implementation plan Markdown file directly into `.agents/bundles/specs/<flow_id>/`,
   * extracting real `[MODIFY]` / `[NEW]` / `[DELETE]` and workspace `file://` links into `files:`/`tests:`.
   *
   * @param {{ markdownText: string, sourcePath?: string | null, flowId?: string | null, title?: string | null }} options
   */
  importPlan({ markdownText, sourcePath = null, flowId = null, title = null } = {}) {
    const raw = String(markdownText || "").trim();
    if (!raw) throw new Error("Plan Markdown text is empty.");
    this.ensureInitialized();

    const h1 = raw.match(/^#\s+(.+)$/m)?.[1]?.trim();
    const inferredTitle = String(title || h1 || "Imported Plan").trim();
    const rawSlug = String(flowId || inferredTitle)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48);
    const cleanId = VALID_SLUG_RE.test(rawSlug) ? rawSlug : `plan-${Date.now().toString(36)}`;
    const goalMatch = raw.match(/##\s*(?:\[?Goal(?:\s+Description)?\]?|Summary)\s*\n+([^\n#][\s\S]*?)(?=\n##\s|$)/i);
    const cleanDesc = goalMatch ? goalMatch[1].trim().split(/\n+/)[0].slice(0, 220) : `${inferredTitle} plan.`;

    const sections = [];
    let current = null;
    let inFence = false;
    for (const line of raw.split(/\r?\n/)) {
      if (/^\s*(```|~~~)/.test(line)) {
        inFence = !inFence;
        continue;
      }
      if (inFence) continue;
      const h3 = line.match(/^###\s+(.+)$/);
      if (h3) {
        if (current && current.lines.length > 0) sections.push(current);
        current = { title: h3[1].trim(), lines: [] };
        continue;
      }
      const h4 = line.match(/^####\s+\[(?:MODIFY|NEW|DELETE)[^\]]*\]\s+(.+)$/i);
      if (h4) {
        if (!current) current = { title: inferredTitle, lines: [] };
        current.lines.push(h4[0]);
        continue;
      }
      if (/^##\s+(?!Verification|User Review|Open Questions)/i.test(line)) {
        if (current && current.lines.length > 0) sections.push(current);
        current = null;
        continue;
      }
      if (current) current.lines.push(line);
    }
    if (current && current.lines.length > 0) sections.push(current);

    const rootNorm = this.effectiveRoot.replace(/\\/g, "/").replace(/\/+$/, "");
    const extractPaths = (text) => {
      const files = [];
      const tests = [];
      const pushPath = (cand) => {
        let clean = String(cand || "").trim().replace(/^`+|`+$/g, "");
        if (!clean) return;
        if (/^file:\/\//i.test(clean)) {
          const decoded = uriToWorkspacePath(clean.split("#")[0]);
          if (!decoded) return;
          clean = decoded.replace(/\\/g, "/");
        } else {
          clean = clean.split("#")[0];
        }
        clean = clean.split("::")[0].trim();
        if (!clean || clean.includes("://")) return;
        if (clean.startsWith(`${rootNorm}/`)) {
          clean = clean.slice(rootNorm.length + 1);
        } else if (path.isAbsolute(clean)) {
          return;
        }
        clean = clean.replace(/^\.\//, "");
        if (!/[./]/.test(clean)) return;
        if (/(?:^|\/)tests?\//.test(clean) || /(?:^|\/)test_[^/]+\.py$/.test(clean)) {
          if (!tests.includes(clean)) tests.push(clean);
        } else if (!files.includes(clean)) {
          files.push(clean);
        }
      };
      for (const m of text.matchAll(/\[[^\]]+\]\(([^)\s]+)\)/g)) pushPath(m[1]);
      for (const m of text.matchAll(/`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+(?:::[A-Za-z0-9_.]+)?)`/g)) pushPath(m[1]);
      return { files, tests };
    };

    const parsedTasks = [];
    for (const sec of sections) {
      if (/^(?:Automated Tests|Manual Verification)$/i.test(sec.title)) continue;
      const bodyText = sec.lines.join("\n");
      const { files, tests } = extractPaths(bodyText);
      const slugBase = sec.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32);
      const short = `t${String(parsedTasks.length + 1).padStart(2, "0")}`;
      parsedTasks.push({
        short,
        slug: `${short}-${slugBase || "slice"}`,
        taskId: `${cleanId}:${short}`,
        title: sec.title,
        description: sec.lines.find((l) => l.trim().startsWith("- "))?.trim().slice(2) || sec.title,
        files,
        tests,
        read_set: [...files, ...tests],
      });
    }

    if (parsedTasks.length === 0) {
      const { files, tests } = extractPaths(raw);
      parsedTasks.push({
        short: "t01",
        slug: "t01-deliverable",
        taskId: `${cleanId}:t01`,
        title: inferredTitle,
        description: cleanDesc,
        files,
        tests,
        read_set: [...files, ...tests],
      });
    }

    const specDir = path.join(this.specsDir, cleanId);
    const written = [];
    const nowIso = new Date().toISOString();
    const headSha = this.#headSha() || "0000000";
    const sourceRel = sourcePath && !path.isAbsolute(sourcePath) ? sourcePath : "implementation_plan.md";
    const checklist = parsedTasks.map((t) => `- [ ] ${t.short} — ${t.title} (tasks/${t.slug}.md)`).join("\n");

    const specMd = [
      "---",
      "type: Spec",
      `flow_id: ${cleanId}`,
      `title: ${JSON.stringify(inferredTitle)}`,
      `description: ${JSON.stringify(cleanDesc)}`,
      "status: draft",
      "state: planned",
      "has_chapters: false",
      "plan_revision: 1",
      `plan_commit: ${headSha}`,
      `current_task: ${JSON.stringify(parsedTasks[0].taskId)}`,
      "last_reviewed_commit: null",
      `created_at: ${nowIso}`,
      "sources:",
      "  - id: plan-src",
      `    resource: ${sourceRel}`,
      "    title: Imported implementation plan",
      "tags: [imported]",
      "---",
      "",
      `# ${inferredTitle}`,
      "",
      "<!-- truth: start -->",
      `- ${cleanDesc}[^plan-src]`,
      "<!-- truth: end -->",
      "",
      "## 1. Specification, Context & Provenance",
      "",
      `${cleanDesc}[^plan-src]`,
      "",
      "## 2. Requirements, Concrete Contracts & Architecture",
      "",
      `- ${cleanDesc}`,
      "",
      "## 3. Documentation & OKF Knowledge Plan",
      "",
      `- Keep \`${this.bundleRel}/index.md\` synchronized in present tense.`,
      "",
      "## 4. Requirement-to-Task Traceability Matrix",
      "",
      "| Requirement | Task | Verification |",
      "| --- | --- | --- |",
      ...parsedTasks.map((t) => `| R1 | ${t.taskId} | \`make check\` |`),
      "",
      "## 5. Implementation Plan",
      "",
      checklist,
      "",
      "## 6. Current State & Remaining Plan Snapshot",
      "",
      `- Active task: \`${parsedTasks[0].taskId}\`.`,
      "",
      `[^plan-src]: \`${sourceRel}\``,
      "",
    ].join("\n");

    const specPath = path.join(specDir, "spec.md");
    writeTextAtomic(specPath, specMd);
    written.push(toPosixRelative(this.effectiveRoot, specPath));

    for (const t of parsedTasks) {
      const taskPath = path.join(specDir, "tasks", `${t.slug}.md`);
      const taskMd = [
        "---",
        "type: Task",
        `id: ${JSON.stringify(t.taskId)}`,
        `title: ${JSON.stringify(t.title)}`,
        `description: ${JSON.stringify(t.description)}`,
        "status: draft",
        "state: pending",
        "priority: P1",
        "worksheet_format: compact",
        "verification_strategy: behavior_tdd",
        "depends_on: []",
        ...FrontmatterCodec.formatFieldLines("read_set", t.read_set),
        ...FrontmatterCodec.formatFieldLines("files", t.files),
        ...FrontmatterCodec.formatFieldLines("tests", t.tests),
        "estimated_loc: 120",
        "plan_revision: 1",
        `plan_commit: ${headSha}`,
        "commit: null",
        "claimed_by: null",
        "claimed_at: null",
        "sources:",
        "  - id: task-src",
        `    resource: ${t.files[0] || t.tests[0] || sourceRel}`,
        `    title: ${JSON.stringify(t.title)}`,
        "tags: [imported]",
        "---",
        "",
        "## Objective & Scope Boundary",
        "",
        `${t.description}[^task-src]`,
        "",
        "## Bounded Read Manifest",
        "",
        ...(t.read_set.length > 0 ? t.read_set.map((p) => `- \`${p}\``) : ["- See owning spec.md"]),
        "",
        "## Contracts & Edge Cases",
        "",
        "- Preserve public module seams and error semantics.",
        "",
        "## Test Matrix",
        "",
        ...(t.tests.length > 0 ? t.tests.map((p) => `- \`${p}\``) : ["- Add targeted public-seam tests."]),
        "",
        "## Verification",
        "",
        "```bash",
        "make check",
        "```",
        "",
        "## Acceptance Criteria",
        "",
        "- [ ] Implementation and tests pass cleanly.",
        "",
        `[^task-src]: \`${t.files[0] || t.tests[0] || sourceRel}\``,
        "",
      ].join("\n");
      writeTextAtomic(taskPath, taskMd);
      written.push(toPosixRelative(this.effectiveRoot, taskPath));
    }

    return { flow_id: cleanId, spec_dir: toPosixRelative(this.effectiveRoot, specDir), written_files: written };
  }

  /**
   * Build the chapter + task dependency DAG and compute disjoint parallel lanes.
   *
   * @param {string} flowId
   */
  buildDag(flowId) {
    const { spec } = this.status(flowId);
    const openComments = this.feedback
      .listForFlow(spec.flow_id)
      .filter((c) => c.state === "open" && c.commentKind !== "approval");

    const chIds = spec.chapters.map((c) => c.chapter_id);
    const chDepsMap = new Map(spec.chapters.map((c) => [c.chapter_id, c.depends_on_chapters]));
    const chLayers = computeTopologicalLayers(chIds, chDepsMap);
    const closedCh = new Set(spec.chapters.filter((c) => isClosedState(c.state)).map((c) => c.chapter_id));

    const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
    const taskDepsMap = new Map();
    const resolvedEdges = new Map();
    for (const t of allTasks) {
      const deps = [];
      const edgeSrcs = [];
      for (const rawDep of t.depends_on) {
        const src = resolveTaskDependency(t, rawDep, allTasks, spec.flow_id);
        if (src && !deps.includes(src.id)) {
          deps.push(src.id);
          edgeSrcs.push(src);
        }
      }
      taskDepsMap.set(t.id, deps);
      resolvedEdges.set(t.id, edgeSrcs);
    }
    const taskLayers = computeTopologicalLayers(allTasks.map((t) => t.id), taskDepsMap);

    /** @type {Map<string, { chKey: string, layer: number, tasks: any[] }>} */
    const buckets = new Map();
    for (const t of allTasks) {
      const chKey = t.chapter_id || "_root";
      const layer = taskLayers.get(t.id) ?? 0;
      const bKey = `${chKey}::${layer}`;
      if (!buckets.has(bKey)) buckets.set(bKey, { chKey, layer, tasks: [] });
      buckets.get(bKey).tasks.push(t);
    }

    const parallel_lanes = [];
    const taskLaneMap = new WeakMap();
    for (const bucket of [...buckets.values()].sort(
      (a, b) => (a.chKey === b.chKey ? a.layer - b.layer : a.chKey === "_root" ? -1 : b.chKey === "_root" ? 1 : a.chKey.localeCompare(b.chKey)),
    )) {
      const owners = new Map();
      const overlaps = [];
      const lanes = [];
      for (const t of bucket.tasks) {
        const writePaths = Array.from(
          new Set(t.files.map((p) => String(p || "").split("::")[0].trim().replace(/^\.\//, "")).filter(Boolean)),
        );
        for (const p of writePaths) {
          const prev = owners.get(p);
          if (prev && prev !== t.id && !overlaps.includes(p)) overlaps.push(p);
          else owners.set(p, t.id);
        }
        let laneIdx = lanes.findIndex((ln) => writePaths.every((p) => !ln.used.has(p)));
        if (laneIdx === -1) {
          laneIdx = lanes.length;
          lanes.push({ used: new Set(), taskIds: [] });
        }
        for (const p of writePaths) lanes[laneIdx].used.add(p);
        lanes[laneIdx].taskIds.push(t.id);
        taskLaneMap.set(t, laneIdx);
      }
      parallel_lanes.push({
        layer: bucket.layer,
        chapter_id: bucket.chKey === "_root" ? null : bucket.chKey,
        disjoint_write_sets: overlaps.length === 0,
        overlapping_paths: overlaps,
        groups: lanes.map((ln, idx) => ({ lane: idx, task_ids: ln.taskIds, files: Array.from(ln.used) })),
      });
    }

    const commentMatchesTask = (c, t) =>
      Boolean(c.taskId && (!c.chapterId || !t.chapter_id || c.chapterId === t.chapter_id) && (c.taskId === t.id || c.taskId === t.short_id || c.taskId === t.stem));

    const edges = [];
    for (const c of spec.chapters) {
      for (const dep of c.depends_on_chapters) {
        edges.push({ id: `ch:${dep}->${c.chapter_id}`, kind: "chapter", source: dep, target: c.chapter_id, unsatisfied: !closedCh.has(dep) });
      }
    }
    for (const t of allTasks) {
      for (const src of resolvedEdges.get(t.id) || []) {
        edges.push({ id: `task:${src.id}->${t.id}`, kind: "task", source: src.id, target: t.id, chapter_id: t.chapter_id, unsatisfied: !isClosedState(src.state) });
      }
    }

    return {
      ok: true,
      flow_id: spec.flow_id,
      title: spec.title,
      state: spec.state,
      has_chapters: spec.has_chapters,
      plan_revision: spec.plan_revision ?? 1,
      current_chapter: spec.current_chapter,
      current_task: spec.current_task,
      chapters: spec.chapters.map((c) => ({
        id: c.chapter_id,
        chapter_id: c.chapter_id,
        title: c.title,
        state: c.state,
        planning_status: c.planning_status,
        replan_trigger: c.replan_trigger || null,
        depends_on_chapters: [...c.depends_on_chapters],
        layer: chLayers.get(c.chapter_id) ?? 0,
        rel_path: c.rel_path,
        open_comment_count: openComments.filter((cm) => cm.chapterId === c.chapter_id || c.tasks.some((t) => commentMatchesTask(cm, t))).length,
        task_counts: c.task_counts,
        task_ids: c.tasks.map((t) => t.id),
      })),
      tasks: allTasks.map((t) => ({
        id: t.id,
        short_id: t.short_id,
        stem: t.stem,
        chapter_id: t.chapter_id,
        title: t.title,
        state: t.state,
        claimed_by: t.claimed_by,
        depends_on: [...t.depends_on],
        files: [...t.files],
        tests: [...t.tests],
        estimated_loc: t.estimated_loc ?? null,
        rel_path: t.rel_path,
        layer: taskLayers.get(t.id) ?? 0,
        parallel_lane: taskLaneMap.get(t) ?? 0,
        open_comment_count: openComments.filter((cm) => commentMatchesTask(cm, t)).length,
      })),
      edges,
      parallel_lanes,
    };
  }

  /**
   * Run runtime dispatch readiness checks with cross-chapter scoped id matching,
   * upstream `depends_on` creation closure for `read_set`, and `DANGLING_TASK_DEP` detection.
   *
   * @param {string} flowId
   * @param {{ chapterId?: string | null }} [options]
   */
  preflight(flowId, { chapterId = null } = {}) {
    const { spec } = this.status(flowId);
    const findings = [];
    const add = (code, severity, relPath, message) => findings.push({ code, severity, path: relPath, message });

    const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
    let targetChapter = null;
    let tasks = spec.tasks;
    let ownerPlanRevision = spec.plan_revision;
    let scopeRel = spec.rel_path;

    if (spec.has_chapters) {
      const requestedId = chapterId || spec.current_chapter || spec.chapters.find((c) => !isClosedState(c.state))?.chapter_id;
      if (!requestedId) {
        add("NO_OPEN_CHAPTER", "error", spec.rel_path, `Spec '${spec.flow_id}' has no open chapter to run.`);
      } else {
        targetChapter = spec.chapters.find((c) => c.chapter_id === requestedId) || null;
        if (!targetChapter) add("CHAPTER_MISSING", "error", spec.rel_path, `Chapter '${requestedId}' does not exist on disk.`);
      }
      if (targetChapter) {
        scopeRel = targetChapter.rel_path;
        ownerPlanRevision = targetChapter.plan_revision ?? spec.plan_revision;
        tasks = targetChapter.tasks;
        const closedCh = new Set(spec.chapters.filter((c) => isClosedState(c.state)).map((c) => c.chapter_id));
        for (const depCh of targetChapter.depends_on_chapters) {
          if (!closedCh.has(depCh)) {
            add("CHAPTER_DEPENDENCY_OPEN", "error", scopeRel, `Chapter '${targetChapter.chapter_id}' depends on open chapter '${depCh}'.`);
          }
        }
        if (targetChapter.planning_status === "empirical_dependent") {
          add("EMPIRICAL_REPLAN_REQUIRED", "error", scopeRel, `Chapter '${targetChapter.chapter_id}' requires empirical replan (${targetChapter.replan_trigger || "upstream baseline"}).`);
        }
      }
    }

    const upstreamCreatedPaths = (startTask) => {
      const created = new Set();
      const seen = new Set();
      const queue = [...startTask.depends_on];
      while (queue.length > 0) {
        const rawDep = queue.shift();
        const depTask = resolveTaskDependency(startTask, rawDep, allTasks, spec.flow_id);
        if (!depTask || seen.has(depTask.id)) continue;
        seen.add(depTask.id);
        for (const f of depTask.files) {
          created.add(String(f).split("::")[0].trim().replace(/^\.\//, ""));
        }
        for (const nextDep of depTask.depends_on) queue.push(nextDep);
      }
      return created;
    };

    const readyTasks = [];
    for (const task of tasks.filter((t) => !isClosedState(t.state))) {
      if (!["compact", "full", "quick"].includes(task.worksheet_format)) {
        add("WORKSHEET_FORMAT", "error", task.rel_path, `Invalid worksheet_format '${task.worksheet_format}'.`);
      } else if (task.worksheet_format === "compact" || task.worksheet_format === "full") {
        const expected = task.worksheet_format === "compact" ? COMPACT_TASK_HEADINGS : FULL_TASK_HEADINGS;
        if (!hasOrderedRequiredHeadings(task.headings, expected)) {
          add("WORKSHEET_INCOMPLETE", "error", task.rel_path, `Worksheet headings do not match '${task.worksheet_format}' contract.`);
        }
      }
      if (!task.verification_strategy || !task.has_verification_body) {
        add("VERIFICATION_MISSING", "error", task.rel_path, "Task must declare verification_strategy and non-empty ## Verification.");
      }
      if (ownerPlanRevision !== null && task.plan_revision !== null && task.plan_revision !== ownerPlanRevision) {
        add("PLAN_REVISION_DRIFT", "error", task.rel_path, `Task plan_revision (${task.plan_revision}) != spec plan_revision (${ownerPlanRevision}).`);
      }

      const selfCreated = new Set(task.files.map((f) => String(f).split("::")[0].trim().replace(/^\.\//, "")));
      const depCreated = upstreamCreatedPaths(task);
      for (const ref of [...task.read_set, ...task.symbol_refs]) {
        const [rawPath, rawSym] = String(ref).split("::");
        const cleanPath = rawPath.split("#")[0].trim().replace(/^\.\//, "");
        if (!cleanPath || /^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(cleanPath)) continue;
        let absRef = null;
        for (const base of [this.workspace, this.effectiveRoot]) {
          try {
            const candidate = resolveConfinedPath(base, cleanPath);
            if (fs.existsSync(candidate)) {
              absRef = candidate;
              break;
            }
          } catch {
            // Outside workspace root.
          }
        }
        if (!absRef) {
          if (!selfCreated.has(cleanPath) && !depCreated.has(cleanPath)) {
            add("TARGET_PATH_MISSING", "error", task.rel_path, `Referenced path '${cleanPath}' does not exist and is not created by this task or upstream dependencies.`);
          }
          continue;
        }
        if (rawSym && rawSym.trim() && fs.statSync(absRef).isFile()) {
          const sym = rawSym.trim().split(".")[0];
          const text = readTextSafe(absRef) || "";
          if (sym && !text.includes(sym)) {
            add("TARGET_SYMBOL_MISSING", "warning", task.rel_path, `Symbol '${sym}' was not found verbatim in '${cleanPath}'.`);
          }
        }
      }

      let allDepsResolvedAndClosed = true;
      for (const rawDep of task.depends_on) {
        const depTask = resolveTaskDependency(task, rawDep, allTasks, spec.flow_id);
        if (!depTask) {
          add("DANGLING_TASK_DEP", "error", task.rel_path, `Task dependency '${rawDep}' does not match any task in '${spec.flow_id}'.`);
          allDepsResolvedAndClosed = false;
        } else if (!isClosedState(depTask.state)) {
          allDepsResolvedAndClosed = false;
        }
      }
      if (allDepsResolvedAndClosed && task.state !== "blocked") readyTasks.push(task);
    }

    const sourceOwners = new Map();
    const overlappingPaths = [];
    const testOwners = new Map();
    const sharedTestFiles = [];
    for (const t of readyTasks) {
      for (const rawFile of t.files) {
        const clean = String(rawFile).split("::")[0].trim().replace(/^\.\//, "");
        if (!clean) continue;
        const prev = sourceOwners.get(clean);
        if (prev && prev !== t.id && !overlappingPaths.includes(clean)) overlappingPaths.push(clean);
        else sourceOwners.set(clean, t.id);
      }
      for (const rawTest of t.tests) {
        const clean = String(rawTest).split("::")[0].trim().replace(/^\.\//, "");
        if (!clean) continue;
        const prev = testOwners.get(clean);
        if (prev && prev !== t.id && !sharedTestFiles.includes(clean)) sharedTestFiles.push(clean);
        else testOwners.set(clean, t.id);
      }
    }

    return {
      ok: !findings.some((f) => f.severity === "error"),
      flow_id: spec.flow_id,
      chapter_id: targetChapter?.chapter_id || null,
      ready_tasks: readyTasks.map((t) => ({ id: t.id, title: t.title, rel_path: t.rel_path })),
      disjoint_write_sets: overlappingPaths.length === 0,
      overlapping_paths: overlappingPaths,
      shared_test_files: sharedTestFiles,
      findings,
    };
  }

  /**
   * Synchronize checklist markers, SHAs, and `current_task` / `current_chapter` / `state` in code (`0` LLM tokens).
   *
   * @param {{ flowId: string, chapterId?: string | null, dryRun?: boolean }} params
   */
  syncChecklists({ flowId, chapterId = null, dryRun = false }) {
    const { spec } = this.status(flowId);
    const updatedFiles = [];

    if (spec.has_chapters) {
      for (const ch of spec.chapters) {
        if (chapterId && ch.chapter_id !== chapterId) continue;
        const chSpecPath = path.join(spec.spec_dir, "chapters", ch.chapter_id, "spec.md");
        const { changed } = this.#syncOwnerSpecTasks(chSpecPath, ch.tasks, { dryRun });
        if (changed) updatedFiles.push(toPosixRelative(this.effectiveRoot, chSpecPath));
      }
      const rootChanged = this.#syncMultiChapterRoot(
        spec.spec_path,
        path.join(spec.spec_dir, "chapters", "index.md"),
        spec.chapters,
        { dryRun },
      );
      if (rootChanged) updatedFiles.push(spec.rel_path);
    } else {
      const { changed } = this.#syncOwnerSpecTasks(spec.spec_path, spec.tasks, { dryRun });
      if (changed) updatedFiles.push(spec.rel_path);
    }

    sharedParseMemo.invalidate(this.effectiveRoot);
    return { ok: true, flow_id: spec.flow_id, dry_run: dryRun, updated_files: updatedFiles };
  }

  /**
   * Release an active claim on a task worksheet and sync checklists.
   *
   * @param {{ flowId: string, taskId: string, chapterId?: string | null }} params
   */
  releaseClaim({ flowId, taskId, chapterId = null }) {
    const { spec } = this.status(flowId);
    const pool = spec.has_chapters
      ? spec.chapters.filter((c) => !chapterId || c.chapter_id === chapterId).flatMap((c) => c.tasks)
      : spec.tasks;
    const match = pool.find((t) => t.id === taskId || t.short_id === taskId || t.stem === taskId);
    if (!match) throw new Error(`Task '${taskId}' not found in spec '${flowId}'.`);
    const raw = readTextSafe(match.abs_path) || "";
    const updates = {
      claimed_by: null,
      claimed_at: null,
      ...(match.state === "in_progress" && !match.commit ? { state: "pending" } : {}),
    };
    writeTextAtomic(match.abs_path, FrontmatterCodec.updateKeys(raw, updates));
    this.syncChecklists({ flowId: spec.flow_id, chapterId: match.chapter_id || null });
    return { released: true, flow_id: spec.flow_id, task_id: match.id, path: match.rel_path };
  }

  /**
   * Stamp completion metadata with `{ by, at }` provenance and evaluate closeout readiness.
   *
   * @param {{ flowId: string, apply?: boolean, verifiedBy?: string | null }} params
   */
  closeout({ flowId, apply = false, verifiedBy = null } = {}) {
    const { spec } = this.status(flowId);
    const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
    const openTasks = allTasks.filter((t) => !isClosedState(t.state));
    const headSha = this.#headSha() || spec.last_reviewed_commit || "0000000";
    const identity = resolveAuthorIdentity(this.workspace);
    const by = verifiedBy || `human:${identity.email}`;
    const at = new Date().toISOString();

    if (openTasks.length > 0) {
      return {
        ok: false,
        flow_id: spec.flow_id,
        open_tasks: openTasks.map((t) => t.id),
        message: `${openTasks.length} task(s) remain open before closeout.`,
      };
    }

    const updated = [];
    if (apply) {
      const rawSpec = readTextSafe(spec.spec_path) || "";
      const next = FrontmatterCodec.updateKeys(rawSpec, {
        state: "completed",
        status: "stable",
        last_reviewed_commit: headSha,
        verified_by: by,
        verified_at: at,
      });
      if (next !== rawSpec) {
        writeTextAtomic(spec.spec_path, next);
        updated.push(spec.rel_path);
      }
      this.syncChecklists({ flowId: spec.flow_id });
    }
    return {
      ok: true,
      flow_id: spec.flow_id,
      verified: { by, at },
      last_reviewed_commit: headSha,
      updated_files: updated,
      spec_sha256: sha256Hex(readTextSafe(spec.spec_path) || ""),
    };
  }

  /**
   * Combine spec review metadata, comments, and DAG for UI & CLI inspection.
   *
   * @param {string} flowId
   */
  getSpecReview(flowId) {
    const { spec } = this.status(flowId);
    const specMarkdown = readTextSafe(spec.spec_path) || "";
    const dag = this.buildDag(spec.flow_id);
    const meta = this.feedback.readMeta(spec.flow_id);
    const viewer = resolveAuthorIdentity(this.workspace).email;
    const comments = this.feedback.listForFlow(spec.flow_id, { viewerEmail: viewer });
    const { openCommentCount, addressedCommentCount, approvalCount } = SpecComment.summarize(comments);
    const hasOpenChangeRequest = comments.some((c) => c.state === "open" && c.commentKind === "change_request");

    let derived = "draft";
    if (hasOpenChangeRequest) derived = "changes_requested";
    else if (approvalCount > 0 && openCommentCount === 0) derived = "approved";
    else if (openCommentCount > 0) derived = "in_review";
    else if (addressedCommentCount > 0) derived = "addressed";

    return {
      ok: true,
      id: meta.id || spec.flow_id,
      flowId: spec.flow_id,
      title: spec.title,
      planRevision: spec.plan_revision ?? 1,
      reviewState: meta.reviewState || derived,
      specMarkdown,
      dag,
      contentSha256: sha256Hex(specMarkdown),
      openCommentCount,
      addressedCommentCount,
      approvalCount,
      comments,
      revisePromptMarkdown: this.feedback.buildRevisePrompt(spec.flow_id, spec.flow_id, comments),
    };
  }

  #readSpecDir(specDir) {
    const rootSpecPath = path.join(specDir, "spec.md");
    if (!fs.existsSync(rootSpecPath)) return null;
    const doc = parseFileMemoized(rootSpecPath);
    if (!doc) return null;
    const flowId = doc.text("flow_id") || path.basename(specDir);
    const relPath = toPosixRelative(this.effectiveRoot, rootSpecPath);
    const state = (doc.text("state") || doc.text("status") || "draft").toLowerCase();
    const chaptersDir = path.join(specDir, "chapters");
    const hasChapters = Boolean(doc.bool("has_chapters") || isExistingDir(chaptersDir));

    const chapters = [];
    if (hasChapters && isExistingDir(chaptersDir)) {
      for (const chEnt of fs.readdirSync(chaptersDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        if (!chEnt.isDirectory() || !chEnt.name.startsWith("ch")) continue;
        const chapterId = chEnt.name;
        const chSpecPath = path.join(chaptersDir, chapterId, "spec.md");
        const chDoc = fs.existsSync(chSpecPath) ? parseFileMemoized(chSpecPath) : null;
        const chRel = fs.existsSync(chSpecPath) ? toPosixRelative(this.effectiveRoot, chSpecPath) : relPath;
        const chTasksDir = path.join(chaptersDir, chapterId, "tasks");
        const rawTasks = isExistingDir(chTasksDir)
          ? walkMarkdownFiles(chTasksDir)
              .filter((f) => path.basename(f) !== "index.md")
              .map((f) => readTaskWorksheet(f, this.effectiveRoot, { flowId, chapterId }))
          : [];
        const tasks = reconcileChecklistWithTasks(chDoc?.body || "", rawTasks, {
          flowId,
          chapterId,
          specRelPath: chRel,
          specAbsPath: chSpecPath,
        });
        const completed = tasks.filter((t) => isClosedState(t.state)).length;
        const chState = (
          chDoc?.text("state") ||
          chDoc?.text("status") ||
          (tasks.length > 0 && completed === tasks.length ? "completed" : completed > 0 ? "active" : "pending")
        ).toLowerCase();
        chapters.push({
          chapter_id: chapterId,
          title: chDoc?.text("title") || chDoc?.body.match(/^#\s+(.+?)\s*$/m)?.[1] || chapterId,
          state: chState,
          planning_status: chDoc?.text("planning_status") || "complete",
          planning_quality: (chDoc?.text("planning_quality") || "standard").toLowerCase(),
          planning_degraded_reason: chDoc?.text("planning_degraded_reason") || null,
          depends_on_chapters: chDoc ? chDoc.textList("depends_on_chapters") : [],
          replan_trigger: chDoc?.text("replan_trigger") || null,
          plan_revision: chDoc?.integer("plan_revision") ?? doc.integer("plan_revision"),
          last_reviewed_commit: chDoc?.text("last_reviewed_commit") || null,
          rel_path: chRel,
          tasks,
          task_counts: SpecEngine.#summarizeTasks(tasks),
        });
      }
    }

    const directTasksDir = path.join(specDir, "tasks");
    const rawDirect = isExistingDir(directTasksDir)
      ? walkMarkdownFiles(directTasksDir)
          .filter((f) => path.basename(f) !== "index.md")
          .map((f) => readTaskWorksheet(f, this.effectiveRoot, { flowId }))
      : [];
    const directTasks = reconcileChecklistWithTasks(doc.body, rawDirect, {
      flowId,
      chapterId: null,
      specRelPath: relPath,
      specAbsPath: rootSpecPath,
    });

    const degradedChapter = chapters.find((c) => c.planning_quality === "degraded");
    const planningQuality =
      (doc.text("planning_quality") || "").toLowerCase() === "degraded" || degradedChapter
        ? "degraded"
        : "standard";
    const planningDegradedReason =
      doc.text("planning_degraded_reason") || degradedChapter?.planning_degraded_reason || null;

    return {
      flow_id: flowId,
      title: doc.text("title") || doc.body.match(/^#\s+(.+?)\s*$/m)?.[1] || flowId,
      type: doc.text("type") || "Spec",
      description: doc.text("description") || "",
      status: doc.text("status") || "draft",
      state,
      planning_quality: planningQuality,
      planning_degraded_reason: planningDegradedReason,
      planned_with_model: doc.text("planned_with_model") || null,
      parent_prd: doc.text("parent_prd") || null,
      has_chapters: hasChapters,
      plan_revision: doc.integer("plan_revision"),
      current_chapter: doc.text("current_chapter") || chapters.find((c) => !isClosedState(c.state))?.chapter_id || null,
      current_task: doc.text("current_task") || null,
      last_reviewed_commit: doc.text("last_reviewed_commit") || null,
      spec_dir: specDir,
      spec_path: rootSpecPath,
      rel_path: relPath,
      chapters,
      tasks: directTasks,
      task_counts: SpecEngine.#summarizeTasks(chapters.length > 0 ? chapters.flatMap((c) => c.tasks) : directTasks),
    };
  }

  static #summarizeTasks(tasks) {
    const counts = { total: tasks.length, completed: 0, in_progress: 0, pending: 0, blocked: 0, deferred: 0 };
    for (const t of tasks) {
      if (t.state === "completed" || t.state === "closed") counts.completed += 1;
      else if (t.state === "in_progress" || t.state === "active") counts.in_progress += 1;
      else if (t.state === "blocked") counts.blocked += 1;
      else if (t.state === "deferred" || t.state === "skipped") counts.deferred += 1;
      else counts.pending += 1;
    }
    return counts;
  }

  #computeNextForSpec(spec) {
    if (spec.has_chapters) {
      const closedCh = new Set(spec.chapters.filter((c) => isClosedState(c.state)).map((c) => c.chapter_id));
      for (const ch of spec.chapters) {
        if (isClosedState(ch.state)) continue;
        if (!ch.depends_on_chapters.every((d) => closedCh.has(d))) continue;
        const ready = ch.tasks.filter(
          (t) =>
            !isClosedState(t.state) &&
            t.state !== "blocked" &&
            t.depends_on.every((d) => {
              const dep = resolveTaskDependency(t, d, ch.tasks, spec.flow_id);
              return dep && isClosedState(dep.state);
            }),
        );
        return {
          flow_id: spec.flow_id,
          chapter_id: ch.chapter_id,
          planning_status: ch.planning_status,
          ready_tasks: ready.map((t) => ({ id: t.id, title: t.title, rel_path: t.rel_path })),
        };
      }
      return null;
    }
    const ready = spec.tasks.filter(
      (t) =>
        !isClosedState(t.state) &&
        t.state !== "blocked" &&
        t.depends_on.every((d) => {
          const dep = resolveTaskDependency(t, d, spec.tasks, spec.flow_id);
          return dep && isClosedState(dep.state);
        }),
    );
    if (ready.length === 0) return null;
    return {
      flow_id: spec.flow_id,
      chapter_id: null,
      planning_status: "complete",
      ready_tasks: ready.map((t) => ({ id: t.id, title: t.title, rel_path: t.rel_path })),
    };
  }

  #syncOwnerSpecTasks(specPath, tasks, { dryRun = false } = {}) {
    if (!fs.existsSync(specPath)) return { changed: false };
    const original = readTextSafe(specPath) || "";
    const doc = FrontmatterDocument.parse(original);
    const lines = original.split("\n");
    let inFm = false;
    let fmClosed = false;
    let inFence = false;
    const matched = new Set();

    const rewritten = lines.map((line, idx) => {
      if (idx === 0 && line.trim() === "---") {
        inFm = true;
        return line;
      }
      if (inFm) {
        if (line.trim() === "---") {
          inFm = false;
          fmClosed = true;
        }
        return line;
      }
      if (!fmClosed && doc.hasFrontmatter) return line;
      if (/^\s*(```|~~~)/.test(line)) {
        inFence = !inFence;
        return line;
      }
      if (inFence) return line;
      const m = line.match(CHECKLIST_LINE_RE);
      if (!m) return line;
      const [, prefix, , spacing, , rest] = m;
      const task = tasks.find(
        (t) =>
          (t.filename && (rest.includes(`tasks/${t.filename}`) || rest.includes(`(${t.filename})`))) ||
          rest.startsWith(`${t.id} `) ||
          rest.startsWith(`${t.id}:`) ||
          rest.startsWith(`${t.short_id} `) ||
          rest.startsWith(`${t.short_id}:`) ||
          rest.startsWith(`${t.stem} `) ||
          rest.startsWith(`${t.stem}:`),
      );
      if (!task) return line;
      matched.add(task.filename || task.id);
      const mark = expectedMarkerForState(task.state);
      const sha = mark === "x" && task.commit && HEX_SHA_RE.test(task.commit) ? `[${task.commit.slice(0, 7)}] ` : "";
      return `${prefix}[${mark}]${spacing}${sha}${rest}`;
    });

    const missing = tasks.filter((t) => t.filename && !matched.has(t.filename));
    if (missing.length > 0) {
      const planIdx = rewritten.findIndex((l) => l.trim() === "## 5. Implementation Plan");
      const insertLines = missing.map((t) => {
        const mark = expectedMarkerForState(t.state);
        const sha = mark === "x" && t.commit && HEX_SHA_RE.test(t.commit) ? `[${t.commit.slice(0, 7)}] ` : "";
        return `- [${mark}] ${sha}${t.short_id} — ${t.title} (tasks/${t.filename})`;
      });
      if (planIdx >= 0) rewritten.splice(planIdx + 2, 0, ...insertLines);
      else rewritten.push("", "## 5. Implementation Plan", "", ...insertLines);
    }

    const openTask = tasks.find((t) => t.state === "in_progress") || tasks.find((t) => !isClosedState(t.state)) || null;
    const anyStarted = tasks.some((t) => t.state === "in_progress" || isClosedState(t.state));
    const curState = (doc.text("state") || "planned").toLowerCase();
    const nextState = curState === "planned" && anyStarted ? "active" : curState;

    const updated = FrontmatterCodec.updateKeys(rewritten.join("\n"), {
      current_task: openTask ? openTask.id : null,
      state: nextState,
    });
    const changed = updated !== original;
    if (changed && !dryRun) writeTextAtomic(specPath, updated);
    return { changed };
  }

  #syncMultiChapterRoot(rootSpecPath, chIndexPath, chStatuses, { dryRun = false } = {}) {
    if (!fs.existsSync(rootSpecPath)) return false;
    const original = readTextSafe(rootSpecPath) || "";
    const doc = FrontmatterDocument.parse(original);
    let inFm = false;
    let inFence = false;
    const rewritten = original.split("\n").map((line, idx) => {
      if (idx === 0 && line.trim() === "---") {
        inFm = true;
        return line;
      }
      if (inFm) {
        if (line.trim() === "---") inFm = false;
        return line;
      }
      if (/^\s*(```|~~~)/.test(line)) {
        inFence = !inFence;
        return line;
      }
      if (inFence) return line;
      const m = line.match(CHECKLIST_LINE_RE);
      if (!m) return line;
      const [, prefix, , spacing, , rest] = m;
      const ch = chStatuses.find((c) => rest.includes(c.chapter_id));
      if (!ch) return line;
      const mark = expectedMarkerForState(ch.state);
      const sha = mark === "x" && ch.last_reviewed_commit && HEX_SHA_RE.test(ch.last_reviewed_commit) ? `[${ch.last_reviewed_commit.slice(0, 7)}] ` : "";
      return `${prefix}[${mark}]${spacing}${sha}${rest}`;
    });
    const openCh = chStatuses.find((c) => !isClosedState(c.state)) || null;
    const anyActive = chStatuses.some((c) => c.state === "active" || isClosedState(c.state));
    const curState = (doc.text("state") || "planned").toLowerCase();
    const nextState = curState === "planned" && anyActive ? "active" : curState;
    const updated = FrontmatterCodec.updateKeys(rewritten.join("\n"), {
      current_chapter: openCh ? openCh.chapter_id : null,
      state: nextState,
    });
    const changed = updated !== original;
    if (changed && !dryRun) writeTextAtomic(rootSpecPath, updated);

    if (fs.existsSync(chIndexPath)) {
      const idxOrig = readTextSafe(chIndexPath) || "";
      const idxNext = idxOrig
        .split("\n")
        .map((line) => {
          if (!line.trim().startsWith("|")) return line;
          const ch = chStatuses.find((c) => line.includes(c.chapter_id));
          if (!ch) return line;
          const cells = line.split("|");
          if (cells.length >= 6) {
            cells[4] = ` ${ch.state} `;
            return cells.join("|");
          }
          return line;
        })
        .join("\n");
      if (idxNext !== idxOrig && !dryRun) writeTextAtomic(chIndexPath, idxNext);
    }
    return changed;
  }

  #headSha() {
    try {
      return execFileSync("git", ["-C", this.workspace, "rev-parse", "--short=7", "HEAD"], {
        encoding: "utf8",
        timeout: 1500,
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
    } catch {
      return null;
    }
  }
}
