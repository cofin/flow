/**
 * Bundle snapshot, spec Markdown reader, inline review comment store, and
 * spec scaffold writer for Flow Studio.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { detectWorkspacePython } from "./python-runner.mjs";

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/;
const TRUTH_RE = /<!--\s*truth:\s*start\s*-->([\s\S]*?)<!--\s*truth:\s*end\s*-->/g;
const CHECKLIST_RE = /^\s*-\s*\[( |~|x|!|-)\]\s*(?:\[([0-9a-f]{6,40})\]\s*)?(.*)$/i;
const HEADING_RE = /^(#{1,4})\s+(.+?)\s*$/;
const VALID_SLUG_RE = /^[a-z0-9][a-z0-9-]{1,62}$/;

/**
 * Parse YAML frontmatter and body from an OKF or Flow Markdown document.
 *
 * @param {string} rawText
 */
export function parseFrontmatter(rawText) {
  const normalized = rawText.replace(/\r\n/g, "\n");
  const match = normalized.match(FRONTMATTER_RE);
  if (!match) {
    return { frontmatter: {}, body: normalized, frontmatterEndLine: 0 };
  }
  const yamlText = match[1];
  const body = match[2];
  const frontmatterEndLine = yamlText.split("\n").length + 2;
  return {
    frontmatter: parseYamlSubset(yamlText),
    body,
    frontmatterEndLine,
  };
}

/**
 * Lightweight YAML subset parser for OKF v0.2 frontmatter.
 *
 * @param {string} yamlText
 * @returns {Record<string, any>}
 */
function parseYamlSubset(yamlText) {
  /** @type {Record<string, any>} */
  const out = {};
  const lines = yamlText.split("\n");
  let idx = 0;

  while (idx < lines.length) {
    const line = lines[idx];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !line.includes(":") || /^\s/.test(line)) {
      idx += 1;
      continue;
    }
    const colon = line.indexOf(":");
    const key = line.slice(0, colon).trim();
    const rest = line.slice(colon + 1).trim();

    if (rest) {
      out[key] = parseScalarOrInlineArray(rest);
      idx += 1;
      continue;
    }

    /** @type {any[]} */
    const arr = [];
    idx += 1;
    while (idx < lines.length) {
      const sub = lines[idx];
      const subTrim = sub.trim();
      if (!subTrim || subTrim.startsWith("#")) {
        idx += 1;
        continue;
      }
      if (!/^\s/.test(sub)) break;
      if (subTrim.startsWith("- ")) {
        const itemBody = subTrim.slice(2).trim();
        if (itemBody.includes(":") && !itemBody.startsWith('"') && !itemBody.startsWith("'")) {
          /** @type {Record<string, any>} */
          const obj = {};
          const cIdx = itemBody.indexOf(":");
          obj[itemBody.slice(0, cIdx).trim()] = parseScalarOrInlineArray(itemBody.slice(cIdx + 1).trim());
          const itemIndent = sub.length - sub.trimStart().length;
          idx += 1;
          while (idx < lines.length) {
            const nested = lines[idx];
            const nestedTrim = nested.trim();
            if (!nestedTrim || nestedTrim.startsWith("#")) {
              idx += 1;
              continue;
            }
            const nestedIndent = nested.length - nested.trimStart().length;
            if (nestedIndent <= itemIndent || nestedTrim.startsWith("- ")) break;
            const nc = nestedTrim.indexOf(":");
            if (nc > 0) {
              obj[nestedTrim.slice(0, nc).trim()] = parseScalarOrInlineArray(nestedTrim.slice(nc + 1).trim());
            }
            idx += 1;
          }
          arr.push(obj);
          continue;
        }
        arr.push(parseScalarOrInlineArray(itemBody));
      }
      idx += 1;
    }
    out[key] = arr;
  }
  return out;
}

/**
 * @param {string} val
 */
function parseScalarOrInlineArray(val) {
  if (val.startsWith("[") && val.endsWith("]")) {
    const inner = val.slice(1, -1).trim();
    if (!inner) return [];
    return inner
      .split(",")
      .map((s) => s.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
  }
  const unquoted = val.replace(/^["']|["']$/g, "");
  if (unquoted === "true") return true;
  if (unquoted === "false") return false;
  if (unquoted === "null" || unquoted === "~") return null;
  return unquoted;
}

/**
 * Extract `<!-- truth: start -->` blocks from Markdown body text.
 *
 * @param {string} body
 * @returns {string | null}
 */
export function extractTruthBlock(body) {
  const blocks = [];
  let match;
  TRUTH_RE.lastIndex = 0;
  while ((match = TRUTH_RE.exec(body)) !== null) {
    const cleaned = match[1].trim();
    if (cleaned) blocks.push(cleaned);
  }
  return blocks.length > 0 ? blocks.join("\n") : null;
}

/**
 * Map checklist marker character to canonical task state string.
 *
 * @param {string} marker
 */
function markerToState(marker) {
  const m = marker.toLowerCase();
  if (m === "x") return "completed";
  if (m === "~") return "in_progress";
  if (m === "!") return "blocked";
  if (m === "-") return "skipped";
  return "pending";
}

/**
 * Walk `.md` files recursively inside `dir`.
 *
 * @param {string} dir
 * @returns {string[]}
 */
function walkMarkdownFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  /** @type {string[]} */
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkMarkdownFiles(full));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      results.push(full);
    }
  }
  return results;
}

/**
 * Read a task worksheet file into a structured task item.
 *
 * @param {string} taskFile
 * @param {string} workspaceRoot
 */
function readTaskWorksheet(taskFile, workspaceRoot) {
  const raw = fs.readFileSync(taskFile, "utf8");
  const { frontmatter, body } = parseFrontmatter(raw);
  const relPath = path.relative(workspaceRoot, taskFile).split(path.sep).join("/");
  const fileBase = path.basename(taskFile, ".md");
  const id = String(frontmatter.id || frontmatter.task_id || fileBase);
  const shortId = id.includes(":") ? id.split(":").pop() : id.split("-")[0];
  const headingMatch = body.match(/^#\s+(.+?)\s*$/m);
  const title = String(frontmatter.title || headingMatch?.[1] || fileBase);
  const state = String(frontmatter.state || frontmatter.status || "pending").toLowerCase();
  const files = Array.isArray(frontmatter.files) ? frontmatter.files.map(String) : [];
  const readSet = Array.isArray(frontmatter.read_set) ? frontmatter.read_set.map(String) : [];

  return {
    id,
    shortId,
    slug: fileBase,
    title,
    state,
    commitSha: frontmatter.commit_sha || frontmatter.commit || null,
    verificationStrategy: frontmatter.verification_strategy || frontmatter.verification || null,
    files,
    readSet,
    relPath,
  };
}

/**
 * Parse checklist lines from a spec body and reconcile against `tasks/*.md` worksheets.
 *
 * @param {string} body
 * @param {ReturnType<typeof readTaskWorksheet>[]} tasks
 */
function reconcileChecklistWithTasks(body, tasks) {
  const checklistItems = [];
  for (const line of body.split("\n")) {
    const m = line.match(CHECKLIST_RE);
    if (!m) continue;
    const [, marker, sha, label] = m;
    checklistItems.push({
      state: markerToState(marker),
      commitSha: sha || null,
      label: label.trim(),
    });
  }

  if (tasks.length === 0) {
    return checklistItems.map((item, idx) => ({
      id: `t${String(idx + 1).padStart(2, "0")}`,
      shortId: `t${String(idx + 1).padStart(2, "0")}`,
      slug: `item-${idx + 1}`,
      title: item.label,
      state: item.state,
      commitSha: item.commitSha,
      verificationStrategy: null,
      files: [],
      readSet: [],
      relPath: null,
    }));
  }

  for (const task of tasks) {
    const matched = checklistItems.find((item) => {
      if (task.relPath && item.label.includes(path.basename(task.relPath))) return true;
      if (item.label.includes(task.id)) return true;
      if (task.shortId && new RegExp(`\\b${escapeRegExp(task.shortId)}\\b`, "i").test(item.label)) return true;
      return false;
    });
    if (matched) {
      if (task.state === "pending" && matched.state !== "pending") {
        task.state = matched.state;
      }
      if (!task.commitSha && matched.commitSha) {
        task.commitSha = matched.commitSha;
      }
    }
  }
  return tasks;
}

/**
 * @param {string} s
 */
function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Build a complete present-tense bundle snapshot for a workspace root.
 */
export class BundleSnapshotBuilder {
  /**
   * @param {string} workspaceRoot
   */
  static build(workspaceRoot) {
    const root = path.resolve(workspaceRoot);
    const workspaceId = deriveWorkspaceId(root);
    const agentsDir = path.join(root, ".agents");
    const setupStatePath = path.join(agentsDir, "setup-state.json");
    const setupState = readJsonIfExists(setupStatePath) || {};
    const bundleRel = String(setupState.bundle_root || ".agents/bundles");
    const bundleRoot = path.join(root, bundleRel);
    const hasBundle = fs.existsSync(bundleRoot);
    const pythonInfo = detectWorkspacePython(root);
    const liveState = readJsonIfExists(path.join(agentsDir, "studio-live-state.json"));
    const reviewStore = new ReviewCommentsStore(root);
    const commentCounts = reviewStore.countByRelPath();

    /** @type {any[]} */
    const specs = [];
    const specsDir = path.join(bundleRoot, "specs");
    if (fs.existsSync(specsDir)) {
      const specDirs = fs
        .readdirSync(specsDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .sort((a, b) => a.name.localeCompare(b.name));

      for (const dirEntry of specDirs) {
        const flowId = dirEntry.name;
        const specFolder = path.join(specsDir, flowId);
        const rootSpecPath = path.join(specFolder, "spec.md");
        if (!fs.existsSync(rootSpecPath)) continue;

        const rawSpec = fs.readFileSync(rootSpecPath, "utf8");
        const { frontmatter, body } = parseFrontmatter(rawSpec);
        const specRelPath = path.relative(root, rootSpecPath).split(path.sep).join("/");
        const headingMatch = body.match(/^#\s+(.+?)\s*$/m);
        const title = String(frontmatter.title || headingMatch?.[1] || flowId);
        const docKind = String(frontmatter.type || "Spec");
        const state = String(frontmatter.state || frontmatter.status || "draft").toLowerCase();
        const chaptersRoot = path.join(specFolder, "chapters");
        const hasChapters = Boolean(frontmatter.has_chapters || fs.existsSync(chaptersRoot));

        /** @type {any[]} */
        const chapters = [];
        if (hasChapters && fs.existsSync(chaptersRoot)) {
          const chDirs = fs
            .readdirSync(chaptersRoot, { withFileTypes: true })
            .filter((d) => d.isDirectory())
            .sort((a, b) => a.name.localeCompare(b.name));

          for (const chDir of chDirs) {
            const chapterId = chDir.name;
            const chSpecPath = path.join(chaptersRoot, chapterId, "spec.md");
            const chRaw = fs.existsSync(chSpecPath) ? fs.readFileSync(chSpecPath, "utf8") : "";
            const chParsed = chRaw ? parseFrontmatter(chRaw) : { frontmatter: {}, body: "" };
            const chTasksDir = path.join(chaptersRoot, chapterId, "tasks");
            const rawTasks = fs.existsSync(chTasksDir)
              ? walkMarkdownFiles(chTasksDir).map((f) => readTaskWorksheet(f, root))
              : [];
            const tasks = reconcileChecklistWithTasks(chParsed.body, rawTasks);
            const completedCount = tasks.filter((t) => t.state === "completed").length;
            const chState = String(
              chParsed.frontmatter.state ||
                chParsed.frontmatter.status ||
                (tasks.length > 0 && completedCount === tasks.length
                  ? "completed"
                  : completedCount > 0
                    ? "active"
                    : "pending")
            ).toLowerCase();
            const chRelPath = fs.existsSync(chSpecPath)
              ? path.relative(root, chSpecPath).split(path.sep).join("/")
              : null;

            chapters.push({
              chapterId,
              title: String(
                chParsed.frontmatter.title ||
                  chParsed.body.match(/^#\s+(.+?)\s*$/m)?.[1] ||
                  chapterId
              ),
              state: chState,
              planningStatus: String(chParsed.frontmatter.planning_status || "complete"),
              dependsOnChapters: Array.isArray(chParsed.frontmatter.depends_on_chapters)
                ? chParsed.frontmatter.depends_on_chapters.map(String)
                : [],
              lastReviewedCommit: chParsed.frontmatter.last_reviewed_commit || null,
              relPath: chRelPath,
              unresolvedComments: chRelPath ? commentCounts[chRelPath] || 0 : 0,
              tasks,
              completedTasks: completedCount,
              totalTasks: tasks.length,
            });
          }
        }

        const directTasksDir = path.join(specFolder, "tasks");
        const rawDirectTasks = fs.existsSync(directTasksDir)
          ? walkMarkdownFiles(directTasksDir).map((f) => readTaskWorksheet(f, root))
          : [];
        const directTasks = reconcileChecklistWithTasks(body, rawDirectTasks);

        const allTasks = chapters.length > 0 ? chapters.flatMap((c) => c.tasks) : directTasks;
        const completedTasks = allTasks.filter((t) => t.state === "completed").length;
        const nextChapter =
          chapters.find((c) => c.chapterId === frontmatter.current_chapter && c.state !== "completed") ||
          chapters.find((c) => c.state === "active" || c.state === "in_progress") ||
          chapters.find((c) => c.state !== "completed") ||
          null;

        specs.push({
          flowId,
          title,
          type: docKind,
          description: String(frontmatter.description || ""),
          state,
          status: String(frontmatter.status || "draft"),
          parentPrd: frontmatter.parent_prd || null,
          hasChapters,
          currentChapter: frontmatter.current_chapter || nextChapter?.chapterId || null,
          lastReviewedCommit: frontmatter.last_reviewed_commit || null,
          relPath: specRelPath,
          unresolvedComments: commentCounts[specRelPath] || 0,
          chapters,
          tasks: directTasks,
          completedTasks,
          totalTasks: allTasks.length,
          recommendedAction: buildRecommendedAction(flowId, docKind, state, chapters, nextChapter, allTasks),
        });
      }
    }

    /** @type {any[]} */
    const knowledge = [];
    for (const sub of ["knowledge", "decisions", "research"]) {
      const subDir = path.join(bundleRoot, sub);
      for (const mdFile of walkMarkdownFiles(subDir)) {
        if (path.basename(mdFile) === "index.md") continue;
        const raw = fs.readFileSync(mdFile, "utf8");
        const { frontmatter, body } = parseFrontmatter(raw);
        const relPath = path.relative(root, mdFile).split(path.sep).join("/");
        const conceptId = path.relative(bundleRoot, mdFile).replace(/\.md$/i, "").split(path.sep).join("/");
        knowledge.push({
          entryId: `${workspaceId}:${conceptId}`,
          conceptId,
          type: String(frontmatter.type || inferTypeFromSubdir(sub)),
          title: String(frontmatter.title || body.match(/^#\s+(.+?)\s*$/m)?.[1] || path.basename(mdFile, ".md")),
          description: String(frontmatter.description || ""),
          status: String(frontmatter.status || "draft"),
          tags: Array.isArray(frontmatter.tags) ? frontmatter.tags.map(String) : [],
          truthBlock: extractTruthBlock(body),
          sourcesCount: Array.isArray(frontmatter.sources) ? frontmatter.sources.length : 0,
          relPath,
          unresolvedComments: commentCounts[relPath] || 0,
        });
      }
    }

    const activeSpec =
      specs.find((s) => s.state === "active" || s.state === "in_progress") ||
      specs[0] ||
      null;

    return {
      generatedAt: new Date().toISOString(),
      workspaceId,
      repoName: path.basename(root),
      workspaceRoot: root,
      bundleInitialized: hasBundle,
      bundleRoot: bundleRel,
      setupState,
      python: pythonInfo,
      liveState,
      activeFlowId: activeSpec?.flowId || null,
      specs,
      knowledge,
      counts: {
        specs: specs.length,
        activeSpecs: specs.filter((s) => s.state === "active" || s.state === "in_progress").length,
        knowledge: knowledge.length,
        unresolvedComments: Object.values(commentCounts).reduce((acc, v) => acc + v, 0),
      },
    };
  }
}

/**
 * @param {string} sub
 */
function inferTypeFromSubdir(sub) {
  if (sub === "decisions") return "Decision";
  if (sub === "research") return "Research";
  return "Concept";
}

/**
 * Compute the single calm primary CTA for a spec card.
 *
 * @param {string} flowId
 * @param {string} docKind
 * @param {string} state
 * @param {any[]} chapters
 * @param {any} nextChapter
 * @param {any[]} allTasks
 */
function buildRecommendedAction(flowId, docKind, state, chapters, nextChapter, allTasks) {
  if (docKind.toUpperCase() === "PRD") {
    return {
      label: "Plan Next Child Spec",
      command: `/flow:plan --parent ${flowId}`,
    };
  }
  if (allTasks.length === 0 && chapters.length === 0) {
    return {
      label: "Generate Task Plan",
      command: `/flow:plan ${flowId}`,
    };
  }
  const completed = allTasks.filter((t) => t.state === "completed").length;
  if (allTasks.length > 0 && completed === allTasks.length && state !== "completed") {
    return {
      label: "Run Zero-Context Review",
      command: `/flow:review ${flowId}`,
    };
  }
  if (nextChapter) {
    return {
      label: `Implement ${nextChapter.chapterId}`,
      command: `/flow:implement ${flowId} ${nextChapter.chapterId}`,
      chapterId: nextChapter.chapterId,
    };
  }
  if (state === "completed") {
    return {
      label: "Finish & Resynthesize",
      command: `/flow:finish ${flowId}`,
    };
  }
  return {
    label: "Implement Next Slice",
    command: `/flow:implement ${flowId}`,
  };
}

/**
 * Manage persistent list of user workspaces for cross-repo catalog and portfolio views.
 */
export class WorkspaceRegistry {
  /**
   * @param {string} [defaultWorkspace]
   */
  constructor(defaultWorkspace) {
    this.defaultWorkspace = path.resolve(defaultWorkspace || process.cwd());
    /** @type {Set<string>} */
    this.runtimeWorkspaces = new Set([this.defaultWorkspace]);
    const baseConfigDir = process.env.FLOW_CONFIG_DIR
      ? path.resolve(process.env.FLOW_CONFIG_DIR)
      : process.env.XDG_CONFIG_HOME
        ? path.join(path.resolve(process.env.XDG_CONFIG_HOME), "flow")
        : path.join(os.homedir(), ".config", "flow");
    this.configPath = process.env.FLOW_WORKSPACES_CONFIG
      ? path.resolve(process.env.FLOW_WORKSPACES_CONFIG)
      : path.join(baseConfigDir, "workspaces.json");
  }

  /**
   * Return deduplicated list of existing workspace directories.
   *
   * @returns {string[]}
   */
  listWorkspaces() {
    /** @type {Set<string>} */
    const seen = new Set(this.runtimeWorkspaces);
    const saved = readJsonIfExists(this.configPath);
    if (saved && Array.isArray(saved.workspaces)) {
      for (const raw of saved.workspaces) {
        if (typeof raw === "string" && raw.trim()) {
          const resolved = path.resolve(raw);
          if (fs.existsSync(resolved)) seen.add(resolved);
        }
      }
    }
    return Array.from(seen);
  }

  /**
   * Register an additional workspace directory.
   *
   * @param {string} workspacePath
   */
  addWorkspace(workspacePath) {
    const resolved = path.resolve(workspacePath);
    if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
      throw new Error(`Workspace directory does not exist: ${resolved}`);
    }
    this.runtimeWorkspaces.add(resolved);
    const list = this.listWorkspaces();
    try {
      fs.mkdirSync(path.dirname(this.configPath), { recursive: true });
      fs.writeFileSync(this.configPath, `${JSON.stringify({ workspaces: list }, null, 2)}\n`, "utf8");
    } catch {
      // Sandboxed or read-only $HOME environments retain workspaces in memory.
    }
    return list;
  }
}

/**
 * Safely read bundle Markdown documents with line numbers, outline headings, and comments.
 */
export class SpecMarkdownReader {
  /**
   * @param {string} workspaceRoot
   * @param {string} relPath
   */
  static read(workspaceRoot, relPath) {
    const root = path.resolve(workspaceRoot);
    const target = resolveConfinedPath(root, relPath);
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      throw new Error(`Markdown document not found: ${relPath}`);
    }
    const raw = fs.readFileSync(target, "utf8").replace(/\r\n/g, "\n");
    const { frontmatter, body, frontmatterEndLine } = parseFrontmatter(raw);
    const allLines = raw.split("\n");
    const headings = [];
    for (let i = 0; i < allLines.length; i += 1) {
      if (i < frontmatterEndLine) continue;
      const hm = allLines[i].match(HEADING_RE);
      if (hm) {
        headings.push({
          level: hm[1].length,
          text: hm[2],
          line: i + 1,
        });
      }
    }
    const commentsStore = new ReviewCommentsStore(root);
    const normalizedRel = path.relative(root, target).split(path.sep).join("/");
    return {
      relPath: normalizedRel,
      title: String(frontmatter.title || headings[0]?.text || path.basename(target, ".md")),
      frontmatter,
      frontmatterEndLine,
      truthBlock: extractTruthBlock(body),
      headings,
      raw,
      lines: allLines.map((text, idx) => ({ lineNumber: idx + 1, text })),
      comments: commentsStore.list(normalizedRel),
    };
  }
}

/**
 * Persist line-anchored inline review comments under `.agents/studio-reviews/`
 * and format `/flow:revise` agent prompts.
 */
export class ReviewCommentsStore {
  /**
   * @param {string} workspaceRoot
   */
  constructor(workspaceRoot) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.reviewsDir = path.join(this.workspaceRoot, ".agents", "studio-reviews");
  }

  /**
   * @param {string} relPath
   */
  list(relPath) {
    const file = this.#storageFileFor(relPath);
    const payload = readJsonIfExists(file);
    return Array.isArray(payload?.comments) ? payload.comments : [];
  }

  /**
   * @param {{ relPath: string, startLine: number, endLine?: number, quote?: string, body: string, author?: string }} input
   */
  add(input) {
    const normalizedRel = normalizeRelPath(this.workspaceRoot, input.relPath);
    const startLine = Math.max(1, Number(input.startLine) || 1);
    const endLine = Math.max(startLine, Number(input.endLine) || startLine);
    const body = String(input.body || "").trim();
    if (!body) {
      throw new Error("Comment body cannot be empty");
    }
    const existing = this.list(normalizedRel);
    const comment = {
      id: `rc_${crypto.randomBytes(6).toString("hex")}`,
      relPath: normalizedRel,
      startLine,
      endLine,
      quote: String(input.quote || "").trim(),
      body,
      author: String(input.author || "human"),
      resolved: false,
      createdAt: new Date().toISOString(),
    };
    existing.push(comment);
    this.#save(normalizedRel, existing);
    return comment;
  }

  /**
   * @param {string} relPath
   * @param {string} commentId
   * @param {boolean} [resolved]
   */
  setResolved(relPath, commentId, resolved = true) {
    const normalizedRel = normalizeRelPath(this.workspaceRoot, relPath);
    const existing = this.list(normalizedRel);
    const target = existing.find((c) => c.id === commentId);
    if (!target) {
      throw new Error(`Review comment not found: ${commentId}`);
    }
    target.resolved = Boolean(resolved);
    this.#save(normalizedRel, existing);
    return target;
  }

  /**
   * Return map of `{ [relPath]: unresolvedCount }` across all reviewed files.
   *
   * @returns {Record<string, number>}
   */
  countByRelPath() {
    /** @type {Record<string, number>} */
    const counts = {};
    if (!fs.existsSync(this.reviewsDir)) return counts;
    for (const entry of fs.readdirSync(this.reviewsDir)) {
      if (!entry.endsWith(".json")) continue;
      const data = readJsonIfExists(path.join(this.reviewsDir, entry));
      if (data?.relPath && Array.isArray(data.comments)) {
        const openCount = data.comments.filter((c) => !c.resolved).length;
        if (openCount > 0) counts[data.relPath] = openCount;
      }
    }
    return counts;
  }

  /**
   * Build a structured `/flow:revise` prompt from unresolved inline review comments.
   *
   * @param {string} relPath
   * @param {string} [flowId]
   */
  buildRevisePrompt(relPath, flowId) {
    const normalizedRel = normalizeRelPath(this.workspaceRoot, relPath);
    const unresolved = this.list(normalizedRel).filter((c) => !c.resolved);
    const targetId = flowId || inferFlowIdFromRelPath(normalizedRel) || normalizedRel;
    const lines = [
      `/flow:revise ${targetId}`,
      "",
      `Apply the following line-anchored review notes on \`${normalizedRel}\`:`,
      "",
    ];
    for (const c of unresolved) {
      const range = c.startLine === c.endLine ? `L${c.startLine}` : `L${c.startLine}-L${c.endLine}`;
      lines.push(`- **${normalizedRel}:${range}**: ${c.body}`);
      if (c.quote) {
        lines.push(`  > ${c.quote.replace(/\n/g, " ")}`);
      }
    }
    return lines.join("\n");
  }

  /**
   * @param {string} relPath
   */
  #storageFileFor(relPath) {
    const normalizedRel = normalizeRelPath(this.workspaceRoot, relPath);
    const hash = crypto.createHash("sha256").update(normalizedRel).digest("hex").slice(0, 12);
    const safeSlug = normalizedRel.replace(/[^a-zA-Z0-9_-]+/g, "_").slice(-48);
    return path.join(this.reviewsDir, `${safeSlug}-${hash}.json`);
  }

  /**
   * @param {string} relPath
   * @param {any[]} comments
   */
  #save(relPath, comments) {
    fs.mkdirSync(this.reviewsDir, { recursive: true });
    const file = this.#storageFileFor(relPath);
    fs.writeFileSync(file, `${JSON.stringify({ relPath, comments }, null, 2)}\n`, "utf8");
  }
}

/**
 * Scaffold a new Feature Spec or Master PRD inside `.agents/bundles/specs/<flow_id>/`.
 */
export class SpecScaffoldWriter {
  /**
   * @param {string} workspaceRoot
   * @param {{
   *   flowId: string,
   *   title: string,
   *   kind?: "Spec" | "PRD",
   *   problem?: string,
   *   goals?: string,
   *   parentPrd?: string,
   *   hasChapters?: boolean
   * }} payload
   */
  static create(workspaceRoot, payload) {
    const root = path.resolve(workspaceRoot);
    const flowId = String(payload.flowId || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/^-+|-+$/g, "");

    if (!VALID_SLUG_RE.test(flowId)) {
      throw new Error(`Invalid spec slug '${payload.flowId}'. Use lowercase letters, digits, and hyphens.`);
    }
    const title = String(payload.title || "").trim() || flowId;
    const kind = payload.kind === "PRD" ? "PRD" : "Spec";
    const hasChapters = Boolean(payload.hasChapters || kind === "PRD");
    const problem = String(payload.problem || "Define problem context and target user outcomes.").trim();
    const goals = String(payload.goals || "- Establish clear public-seam interfaces and verification gates.").trim();

    const bundleRoot = path.join(root, ".agents", "bundles");
    const indexMd = path.join(bundleRoot, "index.md");
    if (!fs.existsSync(indexMd)) {
      fs.mkdirSync(bundleRoot, { recursive: true });
      fs.writeFileSync(
        indexMd,
        `---\nokf_version: "0.2"\nbundle: ${path.basename(root)}\n---\n\n# ${path.basename(root)} Bundle\n`,
        "utf8"
      );
    }

    const specDir = path.join(bundleRoot, "specs", flowId);
    const specFile = path.join(specDir, "spec.md");
    if (fs.existsSync(specFile)) {
      throw new Error(`Specification '${flowId}' already exists at .agents/bundles/specs/${flowId}/spec.md`);
    }

    fs.mkdirSync(specDir, { recursive: true });
    const fmLines = [
      "---",
      `type: ${kind}`,
      `flow_id: ${flowId}`,
      `title: "${title.replace(/"/g, '\\"')}"`,
      `description: "${problem.split("\n")[0].slice(0, 140).replace(/"/g, '\\"')}"`,
      "status: draft",
      "state: draft",
      `has_chapters: ${hasChapters ? "true" : "false"}`,
    ];
    if (payload.parentPrd) {
      fmLines.push(`parent_prd: ${String(payload.parentPrd).trim()}`);
    }
    if (hasChapters && kind === "Spec") {
      fmLines.push("current_chapter: ch01-foundation");
    }
    fmLines.push("---", "");

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

    fs.writeFileSync(specFile, `${fmLines.join("\n")}${bodyLines.join("\n")}`, "utf8");

    if (hasChapters && kind === "Spec") {
      const chaptersDir = path.join(specDir, "chapters");
      const ch01Dir = path.join(chaptersDir, "ch01-foundation");
      fs.mkdirSync(path.join(ch01Dir, "tasks"), { recursive: true });
      fs.writeFileSync(
        path.join(chaptersDir, "index.md"),
        `# ${title} — Chapter Catalog\n\n- [ ] [ch01-foundation](ch01-foundation/spec.md) — Initial vertical-slice foundation\n`,
        "utf8"
      );
      fs.writeFileSync(
        path.join(ch01Dir, "spec.md"),
        [
          "---",
          "type: Spec",
          "chapter_id: ch01-foundation",
          `title: "${title.replace(/"/g, '\\"')} — Chapter 01"`,
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
        "utf8"
      );
    }

    const relPath = path.relative(root, specFile).split(path.sep).join("/");
    const dispatchCommand =
      kind === "PRD" ? `/flow:prd ${flowId} — ${title}` : `/flow:plan ${flowId} — ${title}`;
    return {
      flowId,
      kind,
      title,
      relPath,
      absPath: specFile,
      dispatchCommand,
    };
  }
}

/**
 * Derive deterministic `<repo_name>-<hash8>` workspace identifier matching Python `CatalogService`.
 *
 * @param {string} workspaceRoot
 */
export function deriveWorkspaceId(workspaceRoot) {
  const resolved = path.resolve(workspaceRoot);
  const hash8 = crypto.createHash("sha256").update(resolved, "utf8").digest("hex").slice(0, 8);
  const safeName =
    path
      .basename(resolved)
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "workspace";
  return `${safeName}-${hash8}`;
}

/**
 * @param {string} filePath
 */
function readJsonIfExists(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

/**
 * Confine relative path inside `workspaceRoot`.
 *
 * @param {string} workspaceRoot
 * @param {string} relPath
 */
function resolveConfinedPath(workspaceRoot, relPath) {
  const root = path.resolve(workspaceRoot);
  const candidate = path.resolve(root, relPath);
  const rel = path.relative(root, candidate);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`Path escapes workspace root: ${relPath}`);
  }
  return candidate;
}

/**
 * @param {string} workspaceRoot
 * @param {string} relPath
 */
function normalizeRelPath(workspaceRoot, relPath) {
  const target = resolveConfinedPath(workspaceRoot, relPath);
  return path.relative(path.resolve(workspaceRoot), target).split(path.sep).join("/");
}

/**
 * @param {string} relPath
 */
function inferFlowIdFromRelPath(relPath) {
  const m = relPath.match(/\.agents\/bundles\/specs\/([^/]+)\//);
  return m ? m[1] : null;
}
