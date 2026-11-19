/**
 * @fileoverview Multi-branch OKF/Flow spec scanner, automatic `.agents/` <-> branch sync and
 * conflict healing, index-free GitHub PR spec publisher and review comment bridge, `flow-specs`
 * orphan collaboration branch sync, and remote `gh api` zero-clone spec client.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { StudioCacheStore } from "../core/cache-store.mjs";
import { extractH1, FrontmatterCodec, FrontmatterDocument } from "../core/frontmatter.mjs";
import { isClosedState, sha256Hex, walkFiles, writeTextAtomic } from "../core/fs-io.mjs";
import { GitRunner, IndexFreeBranchWriter, RepoLocator, resolveGitIdentity } from "../core/git.mjs";
import { PRBodyValidator } from "../core/git-tools.mjs";
import {
  DEFAULT_SPEC_BRANCH,
  discoverSpecRoots,
  FRONTMATTER_FREE_NAMES,
  readSetupConfig,
} from "../core/worktree.mjs";
import { parseFeedbackJsonText, SpecComment, SpecFeedbackStore } from "./feedback.mjs";
import { SpecEngine } from "./spec-engine.mjs";

const HEX_SHA_RE = /^[0-9a-fA-F]{7,40}$/;
const CONFLICT_START_RE = /^<{7}(?: .*)?$/m;
const CONFLICT_SEP_RE = /^={7}$/m;
const CONFLICT_END_RE = /^>{7}(?: .*)?$/m;

const STATE_RANK = Object.freeze({
  draft: 0,
  pending: 1,
  planned: 1,
  review: 2,
  in_review: 2,
  approved: 3,
  in_progress: 4,
  active: 4,
  completed: 5,
  closed: 6,
  archived: 7,
});

const MARKER_RANK = Object.freeze({
  " ": 0,
  "-": 1,
  ">": 1,
  "!": 2,
  "~": 3,
  x: 4,
  X: 4,
});

function ensureSingleTrailingNewline(text) {
  const normalized = String(text ?? "").replace(/\r\n/g, "\n").replace(/\n+$/, "");
  return `${normalized}\n`;
}

function slugifyToken(raw, fallback = "item") {
  const slug = String(raw || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64)
    .replace(/-+$/g, "");
  return slug || fallback;
}

function normalizeSpecState(rawState, tasks) {
  const cleaned = String(rawState || "").trim().toLowerCase();
  if (cleaned === "complete" || cleaned === "done") return "completed";
  if (cleaned === "in-progress" || cleaned === "working") return "active";
  if (cleaned && cleaned !== "null") return cleaned;
  if (Array.isArray(tasks) && tasks.length > 0) {
    if (tasks.some((t) => t.state === "in_progress")) return "active";
    if (tasks.every((t) => isClosedState(t.state))) return "completed";
    if (tasks.some((t) => isClosedState(t.state))) return "active";
  }
  return "planned";
}

function summarizeTasks(tasks = []) {
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

function parseChecklistLine(line) {
  const m = String(line || "").match(/^(\s*-\s*)\[([ xX~!>-])\](\s*)(.+)$/);
  if (!m) return null;
  const [, prefix, marker, spacing, rawTail] = m;
  let rest = rawTail.trim();
  let sha = null;
  let shaPosition = "trailing";
  const leadMatch = rest.match(/^\[([0-9a-fA-F]{7,40})\]\s+(.+)$/);
  if (leadMatch) {
    sha = leadMatch[1];
    rest = leadMatch[2].trim();
    shaPosition = "leading";
  } else {
    const trailMatch = rest.match(/^(.+?)\s+\[([0-9a-fA-F]{7,40})\]$/);
    if (trailMatch) {
      rest = trailMatch[1].trim();
      sha = trailMatch[2];
      shaPosition = "trailing";
    }
  }
  return { prefix, marker, spacing: spacing || " ", sha, shaPosition, rest };
}

function checklistItemKey(restText) {
  const clean = String(restText || "").trim();
  const pathMatch = clean.match(/\(((?:chapters\/[^)]+\/spec\.md|tasks\/[^)]+\.md|[^()/]+\/spec\.md))\)/i);
  if (pathMatch) return pathMatch[1].toLowerCase();
  const idMatch = clean.match(/^`?([A-Za-z0-9_.:-]+)`?\s*(?:—|--|-|:)/);
  if (idMatch) return idMatch[1].toLowerCase();
  return clean.toLowerCase();
}

/**
 * Automatic three-way `.agents/` <-> branch sync and conflict-marker healer when `.agents/` is tracked.
 */
export class AgentsBranchSync {
  static AGENT_ROOT_CANDIDATES = Object.freeze([".agents", "_agents", ".flow"]);
  static MERGEABLE_LIST_KEYS = Object.freeze([
    "files",
    "tests",
    "read_set",
    "depends_on",
    "depends_on_chapters",
    "chapters",
    "tags",
  ]);

  static isAgentsTracked(workspacePath, { env = process.env } = {}) {
    if (!workspacePath || !fs.existsSync(workspacePath)) {
      return { tracked: false, reason: "missing_workspace", effectiveRoot: "", agentRoots: [] };
    }
    const setup = readSetupConfig(workspacePath);
    const effectiveRoot = setup.effective_root || path.resolve(workspacePath);
    const git = GitRunner.forWorkspace(effectiveRoot, { timeoutMs: 3000, env });
    if (!git.isGitRepo()) {
      return { tracked: false, reason: "not_git_repository", effectiveRoot, agentRoots: [] };
    }
    if (fs.existsSync(path.join(effectiveRoot, "plugin.json"))) {
      return { tracked: false, reason: "plugin_repository", effectiveRoot, agentRoots: [] };
    }
    if (setup.ignore_policy === "local-only") {
      return { tracked: false, reason: "local_only_policy", effectiveRoot, agentRoots: [] };
    }
    const primaryRoot = setup.root_directory || ".agents";
    const candidates = [...new Set([primaryRoot, ...AgentsBranchSync.AGENT_ROOT_CANDIDATES])];
    const trackedRoots = [];
    for (const rootRel of candidates) {
      const checkRes = git.readGit(["check-ignore", "-q", rootRel]);
      if (checkRes.status === 0) continue;
      if (rootRel === primaryRoot || fs.existsSync(path.join(effectiveRoot, rootRel))) {
        trackedRoots.push(rootRel);
      }
    }
    if (trackedRoots.length === 0) {
      return { tracked: false, reason: "gitignored", effectiveRoot, agentRoots: [] };
    }
    return { tracked: true, reason: "tracked", effectiveRoot, agentRoots: trackedRoots, specBranch: setup.spec_branch };
  }

  static hasConflictMarkers(text) {
    const raw = String(text || "");
    return CONFLICT_START_RE.test(raw) && CONFLICT_SEP_RE.test(raw) && CONFLICT_END_RE.test(raw);
  }

  static splitConflictMarkers(text) {
    const oursLines = [];
    const baseLines = [];
    const theirsLines = [];
    let hasBase = false;
    let mode = "common";
    for (const line of String(text || "").replace(/\r\n/g, "\n").split("\n")) {
      if (line.startsWith("<<<<<<<")) {
        mode = "ours";
        continue;
      }
      if (mode === "ours" && line.startsWith("|||||||")) {
        mode = "base";
        hasBase = true;
        continue;
      }
      if ((mode === "ours" || mode === "base") && line === "=======") {
        mode = "theirs";
        continue;
      }
      if (mode === "theirs" && line.startsWith(">>>>>>>")) {
        mode = "common";
        continue;
      }
      if (mode === "common") {
        oursLines.push(line);
        baseLines.push(line);
        theirsLines.push(line);
      } else if (mode === "ours") {
        oursLines.push(line);
      } else if (mode === "base") {
        baseLines.push(line);
      } else if (mode === "theirs") {
        theirsLines.push(line);
      }
    }
    return {
      ours: oursLines.join("\n"),
      base: hasBase ? baseLines.join("\n") : null,
      theirs: theirsLines.join("\n"),
    };
  }

  static mergeActivityLog(localText, remoteText) {
    const unwrapConflicts = (raw) => {
      if (!AgentsBranchSync.hasConflictMarkers(raw)) return String(raw || "");
      const split = AgentsBranchSync.splitConflictMarkers(raw);
      return `${split.ours}\n${split.theirs}`;
    };
    const combinedRaw = `${unwrapConflicts(localText)}\n${unwrapConflicts(remoteText)}`.replace(/\r\n/g, "\n");
    const titleMatch = combinedRaw.match(/^#\s+.+$/m);
    const heading = titleMatch ? titleMatch[0].trim() : "# Activity Log";

    if (/^##\s+/m.test(combinedRaw)) {
      const sectionByHeader = new Map();
      let currentHeader = null;
      let currentLines = [];
      const flush = () => {
        if (!currentHeader) return;
        const body = currentLines.join("\n").trim();
        if (!sectionByHeader.has(currentHeader)) {
          sectionByHeader.set(currentHeader, body);
        }
      };
      for (const line of combinedRaw.split("\n")) {
        if (line.startsWith("# ")) continue;
        if (line.startsWith("## ")) {
          flush();
          currentHeader = line.trim();
          currentLines = [];
        } else if (currentHeader) {
          currentLines.push(line);
        }
      }
      flush();
      const sortedHeaders = [...sectionByHeader.keys()].sort((a, b) => {
        const ta = a.match(/\[([^\]]+)\]/)?.[1] || "";
        const tb = b.match(/\[([^\]]+)\]/)?.[1] || "";
        if (ta && tb && ta !== tb) return tb.localeCompare(ta);
        return 0;
      });
      const blocks = sortedHeaders.map((hdr) => {
        const secBody = sectionByHeader.get(hdr);
        return secBody ? `${hdr}\n\n${secBody}` : hdr;
      });
      return ensureSingleTrailingNewline(blocks.length > 0 ? `${heading}\n\n${blocks.join("\n\n")}` : heading);
    }

    const seen = new Set();
    const mergedEntries = [];
    for (const line of combinedRaw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("- ") || seen.has(trimmed)) continue;
      seen.add(trimmed);
      mergedEntries.push(trimmed);
    }
    mergedEntries.sort((a, b) => {
      const da = a.match(/^-\s*(\d{4}-\d{2}-\d{2})/)?.[1] || "";
      const db = b.match(/^-\s*(\d{4}-\d{2}-\d{2})/)?.[1] || "";
      if (da && db && da !== db) return db.localeCompare(da);
      return 0;
    });
    const body = mergedEntries.length > 0 ? `\n${mergedEntries.join("\n")}\n` : "\n";
    return ensureSingleTrailingNewline(`${heading}\n${body}`);
  }

  static rebuildSpecsIndex(specsDir, { dryRun = false } = {}) {
    if (!specsDir || !fs.existsSync(specsDir) || !fs.statSync(specsDir).isDirectory()) return false;
    const indexPath = path.join(specsDir, "index.md");
    const entries = fs
      .readdirSync(specsDir, { withFileTypes: true })
      .filter((d) => d.isDirectory() && fs.existsSync(path.join(specsDir, d.name, "spec.md")))
      .sort((a, b) => a.name.localeCompare(b.name));
    const rows = [];
    for (const dir of entries) {
      const specPath = path.join(specsDir, dir.name, "spec.md");
      const doc = FrontmatterDocument.parse(fs.readFileSync(specPath, "utf8"));
      const title = doc.text("title") || extractH1(doc.body) || dir.name;
      const state = normalizeSpecState(doc.text("state") || doc.text("status"), []);
      rows.push(`- [${title}](${dir.name}/spec.md) (\`${state}\`)`);
    }
    const nextText = ensureSingleTrailingNewline(
      rows.length > 0 ? `# Specifications\n\n${rows.join("\n")}` : "# Specifications",
    );
    const prevText = fs.existsSync(indexPath) ? fs.readFileSync(indexPath, "utf8") : "";
    if (nextText !== prevText) {
      if (!dryRun) writeTextAtomic(indexPath, nextText);
      return true;
    }
    return false;
  }

  static mergeAgentMarkdown(baseText, localText, remoteText, { relPath = "" } = {}) {
    const normPath = String(relPath || "").replace(/\\/g, "/");
    if (normPath.endsWith("/log.md") || normPath === "log.md") {
      return {
        resolved: true,
        unresolvedConflict: false,
        content: AgentsBranchSync.mergeActivityLog(localText, remoteText),
      };
    }

    const cleanLocal = ensureSingleTrailingNewline(localText || "");
    const cleanRemote = ensureSingleTrailingNewline(remoteText || "");
    if (cleanLocal === cleanRemote) {
      return { resolved: true, unresolvedConflict: false, content: cleanLocal };
    }
    const cleanBase = baseText !== null && baseText !== undefined ? ensureSingleTrailingNewline(baseText) : null;
    if (cleanBase !== null) {
      if (cleanLocal === cleanBase) return { resolved: true, unresolvedConflict: false, content: cleanRemote };
      if (cleanRemote === cleanBase) return { resolved: true, unresolvedConflict: false, content: cleanLocal };
    }

    const baseDoc = cleanBase !== null ? FrontmatterDocument.parse(cleanBase) : null;
    const localDoc = FrontmatterDocument.parse(cleanLocal);
    const remoteDoc = FrontmatterDocument.parse(cleanRemote);

    const stripChecklistState = (body) =>
      String(body || "")
        .replace(/\r\n/g, "\n")
        .split("\n")
        .map((line) => {
          const parsed = parseChecklistLine(line);
          return parsed ? `${parsed.prefix}[ ] ${parsed.rest}` : line;
        })
        .join("\n")
        .trim();

    const extractChecklists = (body) => {
      const map = new Map();
      for (const line of String(body || "").replace(/\r\n/g, "\n").split("\n")) {
        const parsed = parseChecklistLine(line);
        if (!parsed) continue;
        map.set(checklistItemKey(parsed.rest), {
          marker: parsed.marker,
          sha: parsed.sha || null,
          shaPosition: parsed.sha ? parsed.shaPosition : null,
          rest: parsed.rest,
        });
      }
      return map;
    };

    const applyMergedChecklists = (body, mergedMap) =>
      String(body || "")
        .replace(/\r\n/g, "\n")
        .split("\n")
        .map((line) => {
          const parsed = parseChecklistLine(line);
          if (!parsed) return line;
          const winner = mergedMap.get(checklistItemKey(parsed.rest));
          if (!winner) return line;
          const mark = winner.marker === "X" ? "x" : winner.marker;
          const cleanSha = mark === "x" && winner.sha && HEX_SHA_RE.test(winner.sha) ? winner.sha.slice(0, 7) : null;
          if (cleanSha && winner.shaPosition === "leading") {
            return `${parsed.prefix}[${mark}]${parsed.spacing}[${cleanSha}] ${parsed.rest}`;
          }
          if (cleanSha) {
            return `${parsed.prefix}[${mark}]${parsed.spacing}${parsed.rest} [${cleanSha}]`;
          }
          return `${parsed.prefix}[${mark}]${parsed.spacing}${parsed.rest}`;
        })
        .join("\n");

    const localChecks = extractChecklists(localDoc.body);
    const remoteChecks = extractChecklists(remoteDoc.body);
    const mergedChecks = new Map();
    for (const key of new Set([...localChecks.keys(), ...remoteChecks.keys()])) {
      const lc = localChecks.get(key);
      const rc = remoteChecks.get(key);
      if (lc && !rc) {
        mergedChecks.set(key, lc);
        continue;
      }
      if (rc && !lc) {
        mergedChecks.set(key, rc);
        continue;
      }
      const lr = MARKER_RANK[lc.marker] ?? 0;
      const rr = MARKER_RANK[rc.marker] ?? 0;
      const chosenMarker = rr > lr ? rc.marker : lc.marker;
      const chosenSha = lc.sha && HEX_SHA_RE.test(lc.sha) ? lc.sha : rc.sha && HEX_SHA_RE.test(rc.sha) ? rc.sha : null;
      const chosenPos = lc.shaPosition || rc.shaPosition || "trailing";
      mergedChecks.set(key, {
        marker: chosenMarker,
        sha: chosenSha,
        shaPosition: chosenPos,
        rest: rc.rest || lc.rest,
      });
    }

    const baseNormBody = baseDoc ? stripChecklistState(baseDoc.body) : null;
    const localNormBody = stripChecklistState(localDoc.body);
    const remoteNormBody = stripChecklistState(remoteDoc.body);

    let chosenTemplateText = null;
    let threeWayBody = null;
    if (localNormBody === remoteNormBody) {
      chosenTemplateText = cleanLocal;
    } else if (baseNormBody !== null && localNormBody === baseNormBody) {
      chosenTemplateText = cleanRemote;
    } else if (baseNormBody !== null && remoteNormBody === baseNormBody) {
      chosenTemplateText = cleanLocal;
    } else if (baseNormBody !== null) {
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-md-merge-"));
      try {
        const basePath = path.join(tmpDir, "base.md");
        const oursPath = path.join(tmpDir, "ours.md");
        const theirsPath = path.join(tmpDir, "theirs.md");
        const normalizeChecklistsOnly = (rawBody) =>
          String(rawBody || "")
            .replace(/\r\n/g, "\n")
            .split("\n")
            .map((line) => {
              const parsed = parseChecklistLine(line);
              return parsed ? `${parsed.prefix}[ ] ${parsed.rest}` : line;
            })
            .join("\n");
        fs.writeFileSync(basePath, ensureSingleTrailingNewline(normalizeChecklistsOnly(baseDoc.body)), "utf8");
        fs.writeFileSync(oursPath, ensureSingleTrailingNewline(normalizeChecklistsOnly(localDoc.body)), "utf8");
        fs.writeFileSync(theirsPath, ensureSingleTrailingNewline(normalizeChecklistsOnly(remoteDoc.body)), "utf8");
        const mergeRes = spawnSync(
          "git",
          ["merge-file", "--stdout", "-L", "local", "-L", "base", "-L", "remote", oursPath, basePath, theirsPath],
          { encoding: "utf8", timeout: 4000 },
        );
        if (mergeRes.status === 0 && typeof mergeRes.stdout === "string") {
          chosenTemplateText = cleanLocal;
          threeWayBody = mergeRes.stdout;
        }
      } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    } else {
      const localRev = localDoc.integer("plan_revision") ?? 0;
      const remoteRev = remoteDoc.integer("plan_revision") ?? 0;
      if (remoteRev > localRev) chosenTemplateText = cleanRemote;
      else if (localRev > remoteRev) chosenTemplateText = cleanLocal;
    }

    if (chosenTemplateText === null) {
      return { resolved: false, unresolvedConflict: true, content: cleanLocal };
    }

    const chosenDoc = FrontmatterDocument.parse(chosenTemplateText);
    const mergedBody = applyMergedChecklists(threeWayBody !== null ? threeWayBody : chosenDoc.body, mergedChecks);
    if (!localDoc.hasFrontmatter && !remoteDoc.hasFrontmatter) {
      return { resolved: true, unresolvedConflict: false, content: ensureSingleTrailingNewline(mergedBody) };
    }

    const fmUpdates = {};
    const localRev = localDoc.integer("plan_revision");
    const remoteRev = remoteDoc.integer("plan_revision");
    if (localRev !== null || remoteRev !== null) {
      fmUpdates.plan_revision = Math.max(localRev ?? 1, remoteRev ?? 1);
    }
    const localStateRev = localDoc.integer("state_revision");
    const remoteStateRev = remoteDoc.integer("state_revision");
    if (localStateRev !== null || remoteStateRev !== null) {
      fmUpdates.state_revision = Math.max(localStateRev ?? 1, remoteStateRev ?? 1);
    }

    const lState = (localDoc.text("state") || "").toLowerCase();
    const rState = (remoteDoc.text("state") || "").toLowerCase();
    if (lState || rState) {
      const lRank = STATE_RANK[lState] ?? -1;
      const rRank = STATE_RANK[rState] ?? -1;
      if (rState === "blocked" && (remoteRev ?? 0) >= (localRev ?? 0)) fmUpdates.state = "blocked";
      else if (lState === "blocked" && (localRev ?? 0) >= (remoteRev ?? 0)) fmUpdates.state = "blocked";
      else fmUpdates.state = rRank > lRank ? rState : lState || rState;
    }

    const lCommit = localDoc.text("commit");
    const rCommit = remoteDoc.text("commit");
    const validLocalSha = lCommit && lCommit !== "null" && HEX_SHA_RE.test(lCommit) ? lCommit : null;
    const validRemoteSha = rCommit && rCommit !== "null" && HEX_SHA_RE.test(rCommit) ? rCommit : null;
    if (validLocalSha || validRemoteSha) {
      fmUpdates.commit = validRemoteSha || validLocalSha;
      if (isClosedState(fmUpdates.state || lState || rState)) {
        fmUpdates.claimed_by = null;
        fmUpdates.claimed_at = null;
      }
    }

    const baseLrc = baseDoc?.text("last_reviewed_commit") || null;
    const lLrc = localDoc.text("last_reviewed_commit");
    const rLrc = remoteDoc.text("last_reviewed_commit");
    if (rLrc && rLrc !== "null" && rLrc !== baseLrc) fmUpdates.last_reviewed_commit = rLrc;
    else if (lLrc && lLrc !== "null") fmUpdates.last_reviewed_commit = lLrc;

    for (const listKey of AgentsBranchSync.MERGEABLE_LIST_KEYS) {
      const hasLocalKey = Object.prototype.hasOwnProperty.call(localDoc.data || {}, listKey);
      const hasRemoteKey = Object.prototype.hasOwnProperty.call(remoteDoc.data || {}, listKey);
      if (!hasLocalKey && !hasRemoteKey) continue;
      const lItems = localDoc.textList(listKey);
      const rItems = remoteDoc.textList(listKey);
      const bItems = baseDoc ? new Set(baseDoc.textList(listKey)) : null;
      if (bItems) {
        const kept = [];
        for (const item of [...lItems, ...rItems]) {
          if (kept.includes(item)) continue;
          const removedInLocal = bItems.has(item) && !lItems.includes(item);
          const removedInRemote = bItems.has(item) && !rItems.includes(item);
          if (removedInLocal || removedInRemote) continue;
          kept.push(item);
        }
        fmUpdates[listKey] = kept;
      } else {
        fmUpdates[listKey] = [...new Set([...lItems, ...rItems])];
      }
    }

    const rawLines = chosenTemplateText.split("\n");
    const fmEndLine = Math.max(1, (chosenDoc.bodyLine || 1) - 1);
    const fmHeader = rawLines.slice(0, fmEndLine).join("\n");
    const combined = `${fmHeader}\n${mergedBody}`;
    const updated = FrontmatterCodec.updateKeys(combined, fmUpdates);
    return { resolved: true, unresolvedConflict: false, content: ensureSingleTrailingNewline(updated) };
  }

  constructor(workspacePath, { env = process.env } = {}) {
    this.workspace = path.resolve(workspacePath);
    this.env = env;
  }

  syncWithBranch({ flowId = null, local = false, dryRun = false } = {}) {
    const status = AgentsBranchSync.isAgentsTracked(this.workspace, { env: this.env });
    const specBranch = status.specBranch || DEFAULT_SPEC_BRANCH;
    const receipt = {
      ran: false,
      tracked: status.tracked,
      reason: status.reason,
      branch: null,
      upstream_ref: null,
      fetched: false,
      fast_forwarded: [],
      merged_files: [],
      removed_files: [],
      resolved_conflicts: [],
      unresolved_conflicts: [],
      pr_comments_imported: 0,
      errors: [],
    };
    if (!status.tracked) {
      return receipt;
    }

    receipt.ran = true;
    const effectiveRoot = status.effectiveRoot;
    const git = GitRunner.forWorkspace(effectiveRoot, { timeoutMs: 10000, env: this.env });
    const branchRes = git.revParseVerify("HEAD", { abbrevRef: true });
    const currentBranch = branchRes.ok && branchRes.value && branchRes.value !== "HEAD" ? branchRes.value : null;
    receipt.branch = currentBranch;

    this.#healLocalTreeConflicts(effectiveRoot, status.agentRoots, receipt, { flowId, dryRun });

    if (local || !currentBranch) {
      if (local) receipt.reason = "local_only_flag";
      return receipt;
    }

    const hasOrigin = git.remoteUrl("origin").ok;
    if (hasOrigin && !dryRun) {
      const fetchBranch = git.readGit(
        ["fetch", "--no-tags", "origin", `refs/heads/${currentBranch}:refs/remotes/origin/${currentBranch}`],
        { timeoutMs: 12000 },
      );
      git.readGit(
        ["fetch", "--no-tags", "origin", `refs/heads/${specBranch}:refs/remotes/origin/${specBranch}`],
        { timeoutMs: 12000 },
      );
      receipt.fetched = fetchBranch.ok;
    }

    const upstreamCandidate = `refs/remotes/origin/${currentBranch}`;
    if (git.revParseVerify(upstreamCandidate).ok) {
      receipt.upstream_ref = upstreamCandidate;
      this.#syncTreeAgainstRef(git, effectiveRoot, status.agentRoots, upstreamCandidate, receipt, { flowId, dryRun });
    }

    const orphanRef = git.revParseVerify(`refs/remotes/origin/${specBranch}`).ok
      ? `refs/remotes/origin/${specBranch}`
      : git.revParseVerify(`refs/heads/${specBranch}`).ok
        ? `refs/heads/${specBranch}`
        : null;
    if (orphanRef && !dryRun) {
      this.#pullFeedbackFromOrphanRef(git, effectiveRoot, orphanRef, { flowId });
    }

    if (hasOrigin && !dryRun) {
      try {
        const prSync = new SpecPrPublisher(effectiveRoot, { env: this.env }).syncPullRequestComments(flowId, {
          branch: currentBranch,
        });
        receipt.pr_comments_imported = prSync.imported_count || 0;
      } catch {
        // Offline or unauthenticated gh CLI does not block workspace sync.
      }
    }

    const setup = readSetupConfig(effectiveRoot);
    const specsDir = path.join(effectiveRoot, setup.bundle_root, "specs");
    if (fs.existsSync(specsDir)) {
      AgentsBranchSync.rebuildSpecsIndex(specsDir, { dryRun });
    }
    return receipt;
  }

  #healLocalTreeConflicts(effectiveRoot, agentRoots, receipt, { flowId = null, dryRun = false } = {}) {
    for (const rootRel of agentRoots) {
      const rootAbs = path.join(effectiveRoot, rootRel);
      if (!fs.existsSync(rootAbs)) continue;
      for (const absPath of walkFiles(rootAbs, { extensions: [".md", ".json"], maxDepth: 7 })) {
        const relPath = path.relative(effectiveRoot, absPath).split(path.sep).join("/");
        if (flowId && relPath.includes("/specs/") && !relPath.includes(`/specs/${flowId}/`) && !relPath.endsWith("/specs/index.md")) {
          continue;
        }
        let raw = "";
        try {
          raw = fs.readFileSync(absPath, "utf8");
        } catch {
          continue;
        }
        if (!AgentsBranchSync.hasConflictMarkers(raw)) continue;

        if (relPath.endsWith("/specs/index.md")) {
          if (AgentsBranchSync.rebuildSpecsIndex(path.dirname(absPath), { dryRun })) {
            receipt.resolved_conflicts.push(relPath);
          }
          continue;
        }
        if (absPath.endsWith(".json")) {
          const mergedComments = parseFeedbackJsonText(raw);
          const slug = path.basename(absPath, ".json");
          if (!dryRun) {
            writeTextAtomic(
              absPath,
              `${JSON.stringify(
                { authorSlug: slug, updatedAt: new Date().toISOString(), comments: mergedComments.map((c) => SpecComment.stripDerived(c)) },
                null,
                2,
              )}\n`,
            );
          }
          receipt.resolved_conflicts.push(relPath);
          continue;
        }

        const split = AgentsBranchSync.splitConflictMarkers(raw);
        const merged = AgentsBranchSync.mergeAgentMarkdown(split.base, split.ours, split.theirs, { relPath });
        if (merged.resolved) {
          if (!dryRun) writeTextAtomic(absPath, merged.content);
          receipt.resolved_conflicts.push(relPath);
        } else {
          receipt.unresolved_conflicts.push(relPath);
        }
      }
    }
  }

  #listTreeBlobs(git, ref, agentRoots) {
    const map = new Map();
    if (!ref) return map;
    const res = git.readGit(["ls-tree", "-r", "--full-tree", ref, "--", ...agentRoots]);
    if (!res.ok) return map;
    for (const line of res.stdout.split(/\r?\n/)) {
      if (!line.trim()) continue;
      const tabIdx = line.indexOf("\t");
      if (tabIdx < 0) continue;
      const meta = line.slice(0, tabIdx).trim().split(/\s+/);
      const relPath = line.slice(tabIdx + 1).trim();
      if (meta[1] === "blob" && meta[2] && relPath) map.set(relPath, meta[2]);
    }
    return map;
  }

  #readBlobText(git, blobSha) {
    const res = git.readGit(["cat-file", "-p", blobSha]);
    return res.ok ? res.stdout : null;
  }

  #syncTreeAgainstRef(git, effectiveRoot, agentRoots, upstreamRef, receipt, { flowId = null, dryRun = false } = {}) {
    const mbRes = git.readGit(["merge-base", "HEAD", upstreamRef]);
    const mergeBase = mbRes.ok && mbRes.stdout.trim() ? mbRes.stdout.trim() : null;
    const baseBlobs = mergeBase ? this.#listTreeBlobs(git, mergeBase, agentRoots) : new Map();
    const remoteBlobs = this.#listTreeBlobs(git, upstreamRef, agentRoots);

    const localFiles = new Set();
    for (const rootRel of agentRoots) {
      const rootAbs = path.join(effectiveRoot, rootRel);
      if (!fs.existsSync(rootAbs)) continue;
      for (const absPath of walkFiles(rootAbs, { maxDepth: 7 })) {
        localFiles.add(path.relative(effectiveRoot, absPath).split(path.sep).join("/"));
      }
    }

    const allPaths = [...new Set([...baseBlobs.keys(), ...remoteBlobs.keys(), ...localFiles])].sort();
    for (const relPath of allPaths) {
      if (flowId && relPath.includes("/specs/") && !relPath.includes(`/specs/${flowId}/`) && !relPath.endsWith("/specs/index.md")) {
        continue;
      }
      if (relPath.endsWith("/specs/index.md")) continue;

      const baseSha = baseBlobs.get(relPath) || null;
      const remoteSha = remoteBlobs.get(relPath) || null;
      const absPath = path.join(effectiveRoot, relPath);
      const hasLocal = fs.existsSync(absPath);

      if (remoteSha === baseSha) continue;

      if (!remoteSha && baseSha) {
        if (!hasLocal) continue;
        const baseText = this.#readBlobText(git, baseSha);
        const localText = fs.readFileSync(absPath, "utf8");
        if (baseText !== null && ensureSingleTrailingNewline(localText) === ensureSingleTrailingNewline(baseText)) {
          if (!dryRun) {
            try {
              fs.unlinkSync(absPath);
            } catch {
              // Ignore concurrent removal.
            }
          }
          receipt.removed_files.push(relPath);
        }
        continue;
      }

      const remoteText = this.#readBlobText(git, remoteSha);
      if (remoteText === null) continue;

      if (!hasLocal) {
        if (!dryRun) {
          writeTextAtomic(absPath, relPath.endsWith(".md") ? ensureSingleTrailingNewline(remoteText) : remoteText);
        }
        receipt.fast_forwarded.push(relPath);
        continue;
      }

      const localText = fs.readFileSync(absPath, "utf8");
      const baseText = baseSha ? this.#readBlobText(git, baseSha) : null;
      if (baseText !== null && ensureSingleTrailingNewline(localText) === ensureSingleTrailingNewline(baseText)) {
        const nextOut = relPath.endsWith(".md") ? ensureSingleTrailingNewline(remoteText) : remoteText;
        if (nextOut !== localText) {
          if (!dryRun) writeTextAtomic(absPath, nextOut);
          receipt.fast_forwarded.push(relPath);
        }
        continue;
      }

      if (relPath.endsWith(".json") && relPath.includes("/feedback/")) {
        const mergedList = SpecComment.merge(parseFeedbackJsonText(localText), parseFeedbackJsonText(remoteText)).map((c) =>
          SpecComment.stripDerived(c),
        );
        const slug = path.basename(relPath, ".json");
        const nextJson = `${JSON.stringify({ authorSlug: slug, updatedAt: new Date().toISOString(), comments: mergedList }, null, 2)}\n`;
        if (nextJson !== localText) {
          if (!dryRun) writeTextAtomic(absPath, nextJson);
          receipt.merged_files.push(relPath);
        }
        continue;
      }

      if (relPath.endsWith(".md")) {
        const merged = AgentsBranchSync.mergeAgentMarkdown(baseText, localText, remoteText, { relPath });
        if (merged.resolved) {
          if (merged.content !== localText) {
            if (!dryRun) writeTextAtomic(absPath, merged.content);
            receipt.merged_files.push(relPath);
          }
        } else {
          receipt.unresolved_conflicts.push(relPath);
        }
      }
    }
  }

  #pullFeedbackFromOrphanRef(git, effectiveRoot, orphanRef, { flowId = null } = {}) {
    const ls = git.readGit(["ls-tree", "-r", "--full-tree", orphanRef, "--", "specs"]);
    if (!ls.ok) return;
    const store = new SpecFeedbackStore(effectiveRoot, { env: this.env });
    for (const line of ls.stdout.split(/\r?\n/)) {
      const tabIdx = line.indexOf("\t");
      if (tabIdx < 0) continue;
      const meta = line.slice(0, tabIdx).trim().split(/\s+/);
      const relPath = line.slice(tabIdx + 1).trim();
      const m = relPath.match(/^specs\/([^/]+)\/feedback\/([^/]+)\.json$/);
      if (!m || m[2].startsWith("_")) continue;
      const [, fid, slug] = m;
      if (flowId && fid !== flowId) continue;
      const raw = this.#readBlobText(git, meta[2]);
      if (!raw) continue;
      const comments = parseFeedbackJsonText(raw);
      if (comments.length === 0) continue;
      store.writeMergedAuthorBatch({
        flowId: fid,
        authorEmail: comments[0].authorEmail,
        authorName: comments[0].authorName,
        authorSlug: slug,
        comments,
      });
    }
  }
}

/**
 * Scans specs across HEAD, linked worktrees, local/remote branches, and `flow-specs` / `*-specs` hubs.
 */
export class GitBranchSpecScanner {
  static SPEC_ROOT_CANDIDATES = Object.freeze([
    ".agents/bundles/specs",
    "_agents/bundles/specs",
    ".agents/specs",
    "_agents/specs",
    ".agents/tracks",
    "_agents/tracks",
    ".flow/specs",
    "specs",
  ]);

  constructor(workspacePath, { env = process.env } = {}) {
    this.workspace = path.resolve(workspacePath);
    const setup = readSetupConfig(this.workspace);
    this.effectiveRoot = setup.effective_root || this.workspace;
    this.setup = setup;
    this.specBranch = setup.spec_branch || DEFAULT_SPEC_BRANCH;
    this.env = env;
    this.git = GitRunner.forWorkspace(this.effectiveRoot, { timeoutMs: 5000, env });
    this.cache = StudioCacheStore.shared({ env });
    this.feedback = new SpecFeedbackStore(this.effectiveRoot, { env });
  }

  #isOrphanHubBranch(shortBranch) {
    return shortBranch === this.specBranch || shortBranch.endsWith("-specs");
  }

  listOpenPullRequests({ refresh = false } = {}) {
    const commonRes = this.git.isGitRepo() ? this.git.gitCommonDir() : { ok: false, value: "" };
    const commonDir = commonRes.ok && commonRes.value ? commonRes.value : this.effectiveRoot;
    const nowBucket = refresh ? String(Date.now()) : String(Math.floor(Date.now() / 20_000));
    return this.cache.getOrComputeWorkspace(commonDir, "open_prs_v1", nowBucket, () => {
      if (!this.git.remoteUrl("origin").ok) return [];
      try {
        const items = this.git.runHubJson(
          ["pr", "list", "--state", "open", "--limit", "100", "--json", "number,title,url,headRefName,headRefOid,isDraft,author"],
          { allowFailure: true, timeoutMs: 6000 },
        );
        if (!Array.isArray(items)) return [];
        return items
          .filter((pr) => pr && typeof pr === "object" && pr.headRefName)
          .map((pr) => ({
            number: Number(pr.number) || null,
            title: String(pr.title || ""),
            url: String(pr.url || ""),
            branch: String(pr.headRefName || ""),
            head_oid: String(pr.headRefOid || ""),
            is_draft: Boolean(pr.isDraft),
            author: String(pr.author?.login || pr.author?.name || ""),
          }));
      } catch {
        return [];
      }
    });
  }

  listActiveRefs({ includeRemote = true, includeOrphan = true } = {}) {
    if (!this.git.isGitRepo()) return [];
    const headBranchRes = this.git.revParseVerify("HEAD", { abbrevRef: true });
    const currentBranch = headBranchRes.ok && headBranchRes.value !== "HEAD" ? headBranchRes.value : null;
    const headShaRes = this.git.revParseVerify("HEAD");
    const headSha = headShaRes.ok ? headShaRes.value : null;

    const wtMap = new Map();
    const wtRes = this.git.worktreeList();
    if (wtRes.ok) {
      for (const wt of wtRes.worktrees) {
        if (wt.branch && wt.path) wtMap.set(wt.branch, path.resolve(wt.path));
      }
    }

    const openPrs = this.listOpenPullRequests();
    const prByBranch = new Map(openPrs.map((pr) => [pr.branch, pr]));
    const defaultRef = this.git.revParseVerify("refs/remotes/origin/main").ok
      ? "refs/remotes/origin/main"
      : this.git.revParseVerify("refs/heads/main").ok
        ? "refs/heads/main"
        : null;
    const defaultSha = defaultRef ? this.git.revParseVerify(defaultRef).value : null;

    const refPatterns = ["refs/heads"];
    if (includeRemote) refPatterns.push("refs/remotes/origin");
    const forEach = this.git.readGit([
      "for-each-ref",
      "--sort=-committerdate",
      "--format=%(refname)\t%(objectname)\t%(committerdate:unix)",
      ...refPatterns,
    ]);
    if (!forEach.ok) return [];

    const byBranch = new Map();
    for (const line of forEach.stdout.split(/\r?\n/)) {
      if (!line.trim()) continue;
      const [fullRef = "", sha = "", tsRaw = "0"] = line.split("\t");
      if (!fullRef || !sha || fullRef === "refs/remotes/origin/HEAD") continue;
      const isRemote = fullRef.startsWith("refs/remotes/origin/");
      const shortBranch = isRemote ? fullRef.slice("refs/remotes/origin/".length) : fullRef.slice("refs/heads/".length);
      if (!shortBranch) continue;
      const isOrphan = this.#isOrphanHubBranch(shortBranch);
      if (isOrphan && !includeOrphan) continue;

      const ts = Number.parseInt(tsRaw, 10) || 0;
      const existing = byBranch.get(shortBranch);
      if (existing && !existing.is_remote) {
        if (ts > existing.committer_ts) {
          existing.remote_ref = fullRef;
          existing.remote_sha = sha;
        }
        continue;
      }

      const isHead = shortBranch === currentBranch;
      const worktreePath = wtMap.get(shortBranch) || (isHead ? this.effectiveRoot : null);
      const pr = prByBranch.get(shortBranch) || null;
      if (
        !isHead &&
        !worktreePath &&
        !isOrphan &&
        shortBranch !== "main" &&
        shortBranch !== "master" &&
        !pr &&
        defaultSha &&
        sha !== defaultSha
      ) {
        if (this.git.readGit(["merge-base", "--is-ancestor", sha, defaultRef]).ok) continue;
      }

      byBranch.set(shortBranch, {
        branch: shortBranch,
        git_ref: fullRef,
        commit_sha: sha,
        committer_ts: ts,
        is_remote: isRemote,
        is_current: isHead,
        is_orphan_hub: isOrphan,
        worktree_path: worktreePath,
        pr,
      });
    }

    if (currentBranch && !byBranch.has(currentBranch) && headSha) {
      byBranch.set(currentBranch, {
        branch: currentBranch,
        git_ref: `refs/heads/${currentBranch}`,
        commit_sha: headSha,
        committer_ts: Math.floor(Date.now() / 1000),
        is_remote: false,
        is_current: true,
        is_orphan_hub: this.#isOrphanHubBranch(currentBranch),
        worktree_path: this.effectiveRoot,
        pr: prByBranch.get(currentBranch) || null,
      });
    }
    return [...byBranch.values()];
  }

  scanRefSpecs(refInfo, { includeArchived = false } = {}) {
    if (!refInfo?.commit_sha || !refInfo?.git_ref) return [];
    const commonRes = this.git.gitCommonDir();
    const commonDir = commonRes.ok && commonRes.value ? commonRes.value : this.effectiveRoot;
    const rawSpecs = this.cache.getOrComputeWorkspace(
      commonDir,
      `branch_specs_v1_${refInfo.branch.replace(/[^a-zA-Z0-9._-]/g, "_")}`,
      refInfo.commit_sha,
      () => this.#parseSpecsFromCommit(refInfo),
    );
    return rawSpecs
      .filter((s) => includeArchived || (s.state !== "archived" && s.state !== "closed"))
      .map((spec) => {
        const mergedComments = this.feedback.listForFlow(spec.flow_id, { extraComments: spec._branch_comments || [] });
        const counts = SpecComment.summarize(mergedComments);
        const { _branch_comments: _omit, ...cleanSpec } = spec;
        return {
          ...cleanSpec,
          source_branch: refInfo.branch,
          git_ref: refInfo.git_ref,
          commit_sha: refInfo.commit_sha.slice(0, 7),
          on_current_branch: Boolean(refInfo.is_current),
          worktree_path: refInfo.worktree_path || null,
          pr_number: refInfo.pr?.number || null,
          pr_url: refInfo.pr?.url || null,
          pr_title: refInfo.pr?.title || null,
          pr_author: refInfo.pr?.author || null,
          pr_is_draft: Boolean(refInfo.pr?.is_draft),
          open_comment_count: counts.openCommentCount,
          addressed_comment_count: counts.addressedCommentCount,
          approval_count: counts.approvalCount,
        };
      });
  }

  listAllBranchSpecs({ localSpecs = [], includeArchived = false } = {}) {
    const refs = this.listActiveRefs({ includeRemote: true, includeOrphan: true });
    const currentRef = refs.find((r) => r.is_current) || null;
    const byFlow = new Map();

    const record = (spec, branchName) => {
      const prev = byFlow.get(spec.flow_id);
      if (!prev) {
        byFlow.set(spec.flow_id, { ...spec, available_branches: branchName ? [branchName] : [] });
        return;
      }
      const branches = [...new Set([...(prev.available_branches || []), ...(branchName ? [branchName] : [])])];
      const preferIncoming =
        (!prev.on_current_branch && spec.on_current_branch) ||
        (!prev.worktree_path && spec.worktree_path && !prev.on_current_branch) ||
        (this.#isOrphanHubBranch(prev.source_branch || "") && !this.#isOrphanHubBranch(spec.source_branch || "")) ||
        (!prev.on_current_branch &&
          !spec.on_current_branch &&
          !this.#isOrphanHubBranch(spec.source_branch || "") &&
          (spec.plan_revision ?? 0) > (prev.plan_revision ?? 0));

      const winner = preferIncoming ? spec : prev;
      const prSource = winner.pr_number ? winner : spec.pr_number ? spec : prev;
      byFlow.set(spec.flow_id, {
        ...winner,
        git_ref: winner.on_current_branch ? "HEAD" : winner.git_ref,
        available_branches: branches,
        pr_number: prSource.pr_number || null,
        pr_url: prSource.pr_url || null,
        pr_title: prSource.pr_title || null,
        pr_author: prSource.pr_author || null,
        pr_is_draft: Boolean(prSource.pr_is_draft),
        open_comment_count: Math.max(prev.open_comment_count || 0, spec.open_comment_count || 0),
        addressed_comment_count: Math.max(prev.addressed_comment_count || 0, spec.addressed_comment_count || 0),
        approval_count: Math.max(prev.approval_count || 0, spec.approval_count || 0),
      });
    };

    for (const localSpec of localSpecs || []) {
      const branchName = currentRef?.branch || "HEAD";
      record(
        {
          ...localSpec,
          source_branch: branchName,
          git_ref: "HEAD",
          on_current_branch: true,
          worktree_path: this.effectiveRoot,
          pr_number: currentRef?.pr?.number || null,
          pr_url: currentRef?.pr?.url || null,
          pr_title: currentRef?.pr?.title || null,
          pr_author: currentRef?.pr?.author || null,
          pr_is_draft: Boolean(currentRef?.pr?.is_draft),
        },
        branchName,
      );
    }

    for (const refInfo of refs) {
      if (refInfo.is_current && Array.isArray(localSpecs) && localSpecs.length > 0) continue;
      if (refInfo.branch === "main" || refInfo.branch === "master") continue;
      for (const spec of this.scanRefSpecs(refInfo, { includeArchived })) {
        record(spec, refInfo.branch);
      }
    }
    return [...byFlow.values()];
  }

  readDocumentFromRef(relPath, gitRef) {
    let cleanRel = String(relPath || "").trim().replace(/\\/g, "/").replace(/^\/+/, "").replace(/\/+$/, "");
    const cleanRef = String(gitRef || "").trim();
    if (cleanRel && !cleanRel.includes("\0") && !cleanRel.toLowerCase().endsWith(".md")) {
      cleanRel = `${cleanRel}/spec.md`;
    }
    if (!cleanRel || cleanRel.includes("\0") || !cleanRel.toLowerCase().endsWith(".md")) {
      throw new Error("relPath must point to a .md file.");
    }
    if (!cleanRef || cleanRef.startsWith("-")) throw new Error("Valid gitRef is required.");

    let resolvedRel = cleanRel;
    let showRes = this.git.readGit(["show", `${cleanRef}:${resolvedRel}`]);
    if (!showRes.ok) {
      const movedMatch = this.#matchSpecPath(cleanRel);
      if (movedMatch) {
        for (const candRoot of this.#candidateRoots()) {
          if (candRoot === movedMatch.specRoot) continue;
          const altRel = `${candRoot}/${movedMatch.flowId}/${movedMatch.subPath}`;
          const altShow = this.git.readGit(["show", `${cleanRef}:${altRel}`]);
          if (altShow.ok) {
            resolvedRel = altRel;
            showRes = altShow;
            break;
          }
        }
      }
    }
    if (!showRes.ok) {
      throw new Error(`Markdown document "${cleanRel}" was not found on ref "${cleanRef}".`);
    }
    const raw = showRes.stdout;
    const doc = FrontmatterDocument.parse(raw);
    const rootMatch = this.#matchSpecPath(resolvedRel);
    const flowId = doc.text("flow_id") || rootMatch?.flowId || null;
    const chMatch = resolvedRel.match(/\/chapters\/([^/]+)\//);
    const chapterId = doc.text("chapter_id") || (chMatch ? chMatch[1] : null);
    const taskMatch = resolvedRel.match(/\/tasks\/([^/]+)\.md$/);
    const taskId = doc.text("id") || (taskMatch ? taskMatch[1].split("-")[0] : null);
    const title = doc.text("title") || extractH1(doc.body) || path.posix.basename(resolvedRel);
    const comments = flowId ? this.feedback.list(resolvedRel) : [];

    return {
      ok: true,
      workspace: this.workspace,
      effective_root: this.effectiveRoot,
      git_ref: cleanRef,
      relPath: resolvedRel,
      rel_path: resolvedRel,
      title,
      flowId,
      flow_id: flowId,
      chapter_id: chapterId,
      task_id: taskId,
      frontmatter: doc.data,
      markdown: doc.body,
      raw,
      lines: raw.split(/\r?\n/).map((text, idx) => ({ lineNumber: idx + 1, text })),
      body_start_line: doc.bodyLine,
      comments,
    };
  }

  buildDagFromRef(flowId, gitRef) {
    const cleanRef = String(gitRef || "").trim();
    const shaRes = this.git.revParseVerify(cleanRef);
    if (!shaRes.ok) throw new Error(`Unknown Git ref '${cleanRef}'.`);
    const refSpecs = this.scanRefSpecs(
      {
        branch: cleanRef.replace(/^refs\/(?:heads|remotes\/origin)\//, ""),
        git_ref: cleanRef,
        commit_sha: shaRes.value,
        is_current: false,
      },
      { includeArchived: true },
    );
    const spec = refSpecs.find((s) => s.flow_id === flowId);
    if (!spec) throw new Error(`Spec '${flowId}' not found on ref '${cleanRef}'.`);
    const openComments = this.feedback.listForFlow(flowId).filter((c) => c.state === "open" && c.commentKind !== "approval");
    return { spec, dag: SpecEngine.buildDagFromSpec(spec, openComments) };
  }

  ensureWorktreeForBranch(branchName, { targetDir = null } = {}) {
    const cleanBranch = String(branchName || "").trim().replace(/^refs\/(?:heads|remotes\/origin)\//, "");
    if (!cleanBranch || cleanBranch.startsWith("-")) throw new Error("Valid branchName is required.");
    const wtRes = this.git.worktreeList();
    if (wtRes.ok) {
      const existing = wtRes.worktrees.find((wt) => wt.branch === cleanBranch && wt.path && fs.existsSync(wt.path));
      if (existing) {
        return { ok: true, created: false, branch: cleanBranch, worktree_path: path.resolve(existing.path) };
      }
    }
    const repoName = path.basename(this.effectiveRoot);
    const wtPath = targetDir
      ? path.resolve(targetDir)
      : path.resolve(path.dirname(this.effectiveRoot), `${repoName}-wt-${slugifyToken(cleanBranch, "branch")}`);
    const hasLocalBranch = this.git.revParseVerify(`refs/heads/${cleanBranch}`).ok;
    const hasRemoteBranch = this.git.revParseVerify(`refs/remotes/origin/${cleanBranch}`).ok;
    if (!hasLocalBranch && !hasRemoteBranch) {
      throw new Error(`Branch '${cleanBranch}' does not exist locally or on origin.`);
    }
    const args = hasLocalBranch
      ? ["worktree", "add", wtPath, cleanBranch]
      : ["worktree", "add", "-b", cleanBranch, wtPath, `origin/${cleanBranch}`];
    this.git.runGit(args, { cwd: this.effectiveRoot });
    return { ok: true, created: true, branch: cleanBranch, worktree_path: wtPath };
  }

  #candidateRoots() {
    const configuredSpecs = path.posix.join(this.setup.bundle_root.replace(/\\/g, "/"), "specs");
    return [...new Set([configuredSpecs, ...GitBranchSpecScanner.SPEC_ROOT_CANDIDATES])];
  }

  #matchSpecPath(relPath) {
    for (const root of this.#candidateRoots()) {
      const prefix = `${root}/`;
      if (relPath.startsWith(prefix)) {
        const rest = relPath.slice(prefix.length);
        const slashIdx = rest.indexOf("/");
        if (slashIdx > 0) {
          return { specRoot: root, flowId: rest.slice(0, slashIdx), subPath: rest.slice(slashIdx + 1) };
        }
      }
    }
    return null;
  }

  #parseSpecsFromCommit(refInfo) {
    const roots = this.#candidateRoots();
    const ls = this.git.readGit(["ls-tree", "-r", "--full-tree", refInfo.commit_sha, "--", ...roots]);
    if (!ls.ok) return [];

    const blobsBySpec = new Map();
    for (const line of ls.stdout.split(/\r?\n/)) {
      const tabIdx = line.indexOf("\t");
      if (tabIdx < 0) continue;
      const meta = line.slice(0, tabIdx).trim().split(/\s+/);
      const relPath = line.slice(tabIdx + 1).trim();
      if (meta[1] !== "blob" || !meta[2]) continue;
      const match = this.#matchSpecPath(relPath);
      if (!match) continue;
      const key = `${match.specRoot}::${match.flowId}`;
      if (!blobsBySpec.has(key)) {
        blobsBySpec.set(key, { specRoot: match.specRoot, flowId: match.flowId, files: new Map() });
      }
      blobsBySpec.get(key).files.set(match.subPath, { relPath, sha: meta[2] });
    }

    const readBlob = (sha) => {
      const res = this.git.readGit(["cat-file", "-p", sha]);
      return res.ok ? res.stdout : "";
    };

    const parseTasksMap = (entries, flowId, chapterId) => {
      const out = [];
      for (const [subPath, info] of [...entries].sort((a, b) => a[0].localeCompare(b[0]))) {
        const filename = path.posix.basename(subPath);
        if (!filename.endsWith(".md") || FRONTMATTER_FREE_NAMES.has(filename)) continue;
        const doc = FrontmatterDocument.parse(readBlob(info.sha));
        const stem = filename.replace(/\.md$/, "").split("-")[0];
        const id = doc.text("id") || (chapterId ? `${flowId}:${chapterId.split("-")[0]}:${stem}` : `${flowId}:${stem}`);
        const shortId = id.includes(":") ? id.split(":").pop() : id;
        const claimedBy = doc.text("claimed_by");
        out.push({
          id,
          short_id: shortId,
          stem,
          filename,
          chapter_id: chapterId || doc.text("chapter_id") || null,
          title: doc.text("title") || filename.replace(/\.md$/, ""),
          state: (doc.text("state") || "pending").toLowerCase(),
          worksheet_format: (doc.text("worksheet_format") || "compact").toLowerCase(),
          depends_on: doc.textList("depends_on"),
          read_set: doc.textList("read_set"),
          files: doc.textList("files"),
          tests: doc.textList("tests"),
          lock_scopes: doc.textList("lock_scopes"),
          estimated_loc: doc.integer("estimated_loc"),
          plan_revision: doc.integer("plan_revision"),
          commit: doc.text("commit") || null,
          claimed_by: claimedBy && claimedBy !== "null" ? claimedBy : null,
          claimed_at: doc.text("claimed_at") || null,
          abs_path: null,
          rel_path: info.relPath,
        });
      }
      return out;
    };

    const specs = [];
    for (const bucket of blobsBySpec.values()) {
      const rootSpecEntry = bucket.files.get("spec.md");
      if (!rootSpecEntry) continue;
      const specRaw = readBlob(rootSpecEntry.sha);
      const doc = FrontmatterDocument.parse(specRaw);
      const flowId = doc.text("flow_id") || bucket.flowId;
      const chapterNames = [
        ...new Set([...bucket.files.keys()].map((p) => p.match(/^chapters\/([^/]+)\//)?.[1]).filter(Boolean)),
      ].sort();
      const hasChapters = doc.bool("has_chapters") || chapterNames.length > 0;
      const chapters = [];
      let allTasks = [];

      if (hasChapters) {
        for (const chName of chapterNames) {
          const chSpecEntry = bucket.files.get(`chapters/${chName}/spec.md`);
          const chDoc = chSpecEntry ? FrontmatterDocument.parse(readBlob(chSpecEntry.sha)) : null;
          const chTaskEntries = [...bucket.files.entries()].filter(([k]) => k.startsWith(`chapters/${chName}/tasks/`));
          const chTasks = parseTasksMap(chTaskEntries, flowId, chName);
          allTasks.push(...chTasks);
          chapters.push({
            chapter_id: chName,
            title: chDoc?.text("title") || extractH1(chDoc?.body) || chName,
            description: chDoc?.text("description") || "",
            state: normalizeSpecState(chDoc?.text("state") || chDoc?.text("status"), chTasks),
            planning_status: chDoc?.text("planning_status") || "complete",
            planning_quality: chDoc?.text("planning_quality") || doc.text("planning_quality") || "standard",
            depends_on_chapters: chDoc ? chDoc.textList("depends_on_chapters") : [],
            replan_trigger: chDoc?.text("replan_trigger") || null,
            plan_revision: chDoc?.integer("plan_revision") ?? doc.integer("plan_revision"),
            current_task: chDoc?.text("current_task") || null,
            last_reviewed_commit: chDoc?.text("last_reviewed_commit") || null,
            rel_path: chSpecEntry ? chSpecEntry.relPath : `${bucket.specRoot}/${bucket.flowId}/chapters/${chName}/spec.md`,
            task_counts: summarizeTasks(chTasks),
            tasks: chTasks,
          });
        }
      } else {
        const taskEntries = [...bucket.files.entries()].filter(([k]) => k.startsWith("tasks/"));
        allTasks = parseTasksMap(taskEntries, flowId, null);
      }

      let branchComments = [];
      for (const [subPath, info] of bucket.files.entries()) {
        if (!subPath.startsWith("feedback/") || !subPath.endsWith(".json")) continue;
        const fname = path.posix.basename(subPath);
        if (fname.startsWith("_") || fname.startsWith(".")) continue;
        branchComments = SpecComment.merge(branchComments, parseFeedbackJsonText(readBlob(info.sha)));
      }

      specs.push({
        flow_id: flowId,
        title: doc.text("title") || extractH1(doc.body) || flowId,
        type: doc.text("type") || "Spec",
        description: doc.text("description") || "",
        state: normalizeSpecState(doc.text("state") || doc.text("status"), allTasks),
        status: doc.text("status") || "draft",
        has_chapters: hasChapters,
        has_frontmatter: doc.hasFrontmatter,
        source_root: bucket.specRoot,
        source_kind: refInfo.is_orphan_hub ? "orphan_branch" : "git_branch",
        planning_quality: doc.text("planning_quality") || "standard",
        planning_degraded_reason: doc.text("planning_degraded_reason") || null,
        planned_with_model: doc.text("planned_with_model") || null,
        parent_prd: doc.text("parent_prd") || null,
        plan_revision: doc.integer("plan_revision"),
        plan_commit: doc.text("plan_commit") || null,
        last_reviewed_commit: doc.text("last_reviewed_commit") || null,
        current_chapter: doc.text("current_chapter") || null,
        current_task: doc.text("current_task") || null,
        spec_dir: null,
        spec_path: null,
        rel_path: rootSpecEntry.relPath,
        task_counts: summarizeTasks(allTasks),
        chapters,
        tasks: hasChapters ? [] : allTasks,
        _branch_comments: branchComments,
      });
    }
    return specs;
  }
}

/**
 * Pull or merge a spec directory and its feedback from another Git branch or `flow-specs` into the working tree.
 */
export class SpecBranchPuller {
  constructor(workspacePath, { env = process.env } = {}) {
    this.workspace = path.resolve(workspacePath);
    const engine = new SpecEngine({ workspacePath: this.workspace, env });
    this.setup = readSetupConfig(this.workspace);
    this.effectiveRoot = engine.effectiveRoot;
    this.bundleRoot = engine.bundleRel;
    this.specBranch = this.setup.spec_branch || DEFAULT_SPEC_BRANCH;
    this.env = env;
    this.git = GitRunner.forWorkspace(this.effectiveRoot, { timeoutMs: 8000, env });
    this.scanner = new GitBranchSpecScanner(this.effectiveRoot, { env });
    this.feedback = new SpecFeedbackStore(this.effectiveRoot, { env });
  }

  pullSpec(flowId, { fromRef = null, force = false, dryRun = false } = {}) {
    const cleanFlow = String(flowId || "").trim();
    if (!cleanFlow || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(cleanFlow)) {
      throw new Error("Valid flowId is required.");
    }

    let resolvedRef = fromRef ? String(fromRef).trim() : "";
    let sourceSpecPrefix = null;
    if (!resolvedRef) {
      const candidates = this.scanner.listAllBranchSpecs({ localSpecs: [], includeArchived: true });
      const match = candidates.find((s) => s.flow_id === cleanFlow && !s.on_current_branch) || candidates.find((s) => s.flow_id === cleanFlow);
      if (!match) {
        throw new Error(`Spec '${cleanFlow}' was not found on any active branch or ${this.specBranch}.`);
      }
      resolvedRef = match.git_ref;
      sourceSpecPrefix = `${match.source_root}/${cleanFlow}`;
    } else {
      if (!this.git.revParseVerify(resolvedRef).ok && this.git.revParseVerify(`origin/${resolvedRef}`).ok) {
        resolvedRef = `origin/${resolvedRef}`;
      }
      if (!this.git.revParseVerify(resolvedRef).ok) {
        throw new Error(`Git ref '${fromRef}' was not found.`);
      }
      for (const rootCand of [
        path.posix.join(this.bundleRoot.replace(/\\/g, "/"), "specs"),
        ...GitBranchSpecScanner.SPEC_ROOT_CANDIDATES,
      ]) {
        const probe = this.git.readGit(["ls-tree", "-r", "--name-only", resolvedRef, "--", `${rootCand}/${cleanFlow}`]);
        if (probe.ok && probe.stdout.trim()) {
          sourceSpecPrefix = `${rootCand}/${cleanFlow}`;
          break;
        }
      }
      if (!sourceSpecPrefix) {
        throw new Error(`Spec '${cleanFlow}' was not found under ref '${resolvedRef}'.`);
      }
    }

    const ls = this.git.readGit(["ls-tree", "-r", "--full-tree", resolvedRef, "--", sourceSpecPrefix]);
    if (!ls.ok || !ls.stdout.trim()) {
      throw new Error(`Unable to read spec tree '${sourceSpecPrefix}' from '${resolvedRef}'.`);
    }

    const targetSpecRootRel =
      sourceSpecPrefix.startsWith(".agents/specs/") || sourceSpecPrefix.startsWith(".flow/specs/")
        ? sourceSpecPrefix.slice(0, sourceSpecPrefix.lastIndexOf("/"))
        : path.posix.join(this.bundleRoot.replace(/\\/g, "/"), "specs");
    const targetSpecDir = path.join(this.effectiveRoot, targetSpecRootRel, cleanFlow);
    const statusRes = this.git.statusPorcelain({ untrackedFiles: "all", nul: true });
    const dirtySet = new Set(statusRes.ok ? statusRes.paths : []);

    const writtenFiles = [];
    const mergedFiles = [];
    let importedComments = 0;

    for (const line of ls.stdout.split(/\r?\n/)) {
      const tabIdx = line.indexOf("\t");
      if (tabIdx < 0) continue;
      const meta = line.slice(0, tabIdx).trim().split(/\s+/);
      const srcRel = line.slice(tabIdx + 1).trim();
      if (meta[1] !== "blob" || !meta[2]) continue;
      const subPath = srcRel.slice(sourceSpecPrefix.length + 1);
      if (!subPath || subPath === "DISCUSSION.md") continue;

      const blobRes = this.git.readGit(["cat-file", "-p", meta[2]]);
      if (!blobRes.ok) continue;
      const remoteText = blobRes.stdout;

      if (subPath.startsWith("feedback/") && subPath.endsWith(".json") && !path.posix.basename(subPath).startsWith("_")) {
        const slug = path.posix.basename(subPath, ".json");
        const list = parseFeedbackJsonText(remoteText);
        if (list.length > 0 && !dryRun) {
          const first = list[0];
          this.feedback.writeMergedAuthorBatch({
            flowId: cleanFlow,
            authorEmail: first.authorEmail,
            authorName: first.authorName,
            authorSlug: slug,
            comments: list,
          });
          importedComments += list.length;
        }
        continue;
      }

      const destAbs = path.join(targetSpecDir, subPath);
      const destRel = path.relative(this.effectiveRoot, destAbs).split(path.sep).join("/");
      if (!fs.existsSync(destAbs)) {
        if (!dryRun) {
          writeTextAtomic(destAbs, destRel.endsWith(".md") ? ensureSingleTrailingNewline(remoteText) : remoteText);
        }
        writtenFiles.push(destRel);
        continue;
      }

      const localText = fs.readFileSync(destAbs, "utf8");
      if (force) {
        const nextOut = destRel.endsWith(".md") ? ensureSingleTrailingNewline(remoteText) : remoteText;
        if (nextOut !== localText) {
          if (!dryRun) writeTextAtomic(destAbs, nextOut);
          writtenFiles.push(destRel);
        }
        continue;
      }

      if (destRel.endsWith(".md")) {
        const merged = AgentsBranchSync.mergeAgentMarkdown(null, localText, remoteText, { relPath: destRel });
        if (!merged.resolved || dirtySet.has(destRel)) {
          const normRemote = ensureSingleTrailingNewline(remoteText);
          const normLocal = ensureSingleTrailingNewline(localText);
          if (normRemote !== normLocal && dirtySet.has(destRel) && !merged.resolved) {
            throw new Error(`Local uncommitted changes in '${destRel}' conflict with '${resolvedRef}'; commit or pass --force.`);
          }
          if (!merged.resolved) {
            throw new Error(`Divergent prose in '${destRel}' between local checkout and '${resolvedRef}'; pass --force to overwrite.`);
          }
        }
        if (merged.content !== localText) {
          if (!dryRun) writeTextAtomic(destAbs, merged.content);
          mergedFiles.push(destRel);
        }
      }
    }

    const specsRootAbs = path.join(this.effectiveRoot, targetSpecRootRel);
    if (targetSpecRootRel.endsWith("bundles/specs") && fs.existsSync(specsRootAbs)) {
      if (AgentsBranchSync.rebuildSpecsIndex(specsRootAbs, { dryRun })) {
        writtenFiles.push(`${targetSpecRootRel}/index.md`);
      }
    }

    StudioCacheStore.shared({ env: this.env }).invalidateWorkspace(this.effectiveRoot);
    return {
      ok: true,
      flow_id: cleanFlow,
      from_ref: resolvedRef,
      spec_dir: `${targetSpecRootRel}/${cleanFlow}`,
      written_files: writtenFiles,
      merged_files: mergedFiles,
      imported_comments: importedComments,
      dry_run: Boolean(dryRun),
    };
  }
}

/**
 * Publishes specs to GitHub feature/spec PRs and syncs line-anchored PR review comments.
 */
export class SpecPrPublisher {
  constructor(workspacePath, { env = process.env, hubBinary = null } = {}) {
    this.workspace = path.resolve(workspacePath);
    const setup = readSetupConfig(this.workspace);
    this.setup = setup;
    this.effectiveRoot = setup.effective_root || this.workspace;
    this.env = env;
    this.git = GitRunner.forWorkspace(this.effectiveRoot, { timeoutMs: 15000, env, hubBinary });
    this.feedback = new SpecFeedbackStore(this.effectiveRoot, { env });
  }

  static buildPrTitleAndBody(spec, { branch = "", customTitle = null } = {}) {
    const rawTitle = customTitle ? String(customTitle).trim() : `docs(spec): publish ${spec.flow_id} specification`;
    const cleanTitle = rawTitle.replace(/!/g, "");
    const cleanSummary = String(spec.description || `${spec.title} specification.`)
      .replace(/!/g, ".")
      .trim();
    const changeBullets = [`- \`${spec.rel_path}\`: Add \`${spec.flow_id}\` specification (${spec.title.replace(/!/g, "")}).`];
    if (spec.has_chapters && Array.isArray(spec.chapters) && spec.chapters.length > 0) {
      changeBullets.push(`- Chapters (${spec.chapters.length}): ${spec.chapters.map((c) => `\`${c.chapter_id}\``).join(", ")}.`);
    } else if ((spec.task_counts?.total || 0) > 0) {
      changeBullets.push(`- Task worksheets: ${spec.task_counts.total} planned task(s) on \`${branch || "spec branch"}\`.`);
    }
    const body = ["## Summary", "", cleanSummary, "", "## Key Changes", "", ...changeBullets, ""].join("\n");
    const findings = new PRBodyValidator().validate(cleanTitle, body);
    const errors = findings.filter((f) => f.severity === "error");
    if (errors.length > 0) {
      throw new Error(`Generated PR body failed validation: ${errors[0].message}`);
    }
    return { title: cleanTitle, body };
  }

  publishSpecToPr(flowId, { branch = null, base = null, draft = false, title = null, push = false } = {}) {
    const cleanFlow = String(flowId || "").trim();
    if (!cleanFlow) throw new Error("flowId is required.");
    if (fs.existsSync(path.join(this.effectiveRoot, "plugin.json")) || this.setup.ignore_policy === "local-only") {
      throw new Error(
        `Cannot commit .agents specs onto code branches when ignore_policy is local-only or in a plugin repository; use 'flow spec share ${cleanFlow} --branch' instead.`,
      );
    }
    if (this.git.readGit(["check-ignore", "-q", this.setup.root_directory || ".agents"]).status === 0) {
      throw new Error(
        `Directory '${this.setup.root_directory || ".agents"}' is gitignored; update ignore_policy to 'shared' or use 'flow spec share ${cleanFlow} --branch'.`,
      );
    }

    const specRootAbs = this.#locateLocalSpecDir(cleanFlow);
    if (!specRootAbs) throw new Error(`Spec '${cleanFlow}' was not found on disk in workspace.`);
    const specFilesAbs = walkFiles(specRootAbs, { extensions: [".md"], maxDepth: 6 });
    if (specFilesAbs.length === 0) throw new Error(`Spec '${cleanFlow}' contains no Markdown files.`);

    const specsParentAbs = path.dirname(specRootAbs);
    if (specsParentAbs.endsWith(`${path.sep}bundles${path.sep}specs`)) {
      AgentsBranchSync.rebuildSpecsIndex(specsParentAbs, { dryRun: false });
      const idxAbs = path.join(specsParentAbs, "index.md");
      if (fs.existsSync(idxAbs)) specFilesAbs.push(idxAbs);
    }

    const relPaths = [];
    for (const absPath of specFilesAbs) {
      const normalized = ensureSingleTrailingNewline(fs.readFileSync(absPath, "utf8"));
      writeTextAtomic(absPath, normalized);
      relPaths.push(path.relative(this.effectiveRoot, absPath).split(path.sep).join("/"));
    }

    const headBranchRes = this.git.revParseVerify("HEAD", { abbrevRef: true });
    const currentBranch = headBranchRes.ok && headBranchRes.value !== "HEAD" ? headBranchRes.value : null;
    const defaultBase =
      base ||
      (this.git.revParseVerify("refs/remotes/origin/main").ok || this.git.revParseVerify("refs/heads/main").ok
        ? "main"
        : "master");
    const targetBranch = String(
      branch ||
        (currentBranch && currentBranch !== "main" && currentBranch !== "master"
          ? currentBranch
          : `feat/${slugifyToken(cleanFlow, "spec")}`),
    ).trim();

    const specSummary = this.#readMinimalLocalSpecSummary(specRootAbs, cleanFlow);
    const commitMsg = `docs(spec): publish ${cleanFlow} specification`;
    const prevHead = this.git.revParseVerify(`refs/heads/${targetBranch}`).value || this.git.revParseVerify("HEAD").value;
    const commitSha = IndexFreeBranchWriter.commitWorkspacePaths({
      git: this.git,
      effectiveRoot: this.effectiveRoot,
      targetBranch,
      baseBranch: defaultBase,
      relPaths,
      message: commitMsg,
      env: this.env,
    });
    const committed = Boolean(commitSha && commitSha !== prevHead);

    let pushed = false;
    if (push && this.git.remoteUrl("origin").ok) {
      this.git.runGit(["push", "origin", `refs/heads/${targetBranch}:refs/heads/${targetBranch}`], {
        cwd: this.effectiveRoot,
      });
      pushed = true;
    }

    const { title: prTitle, body: prBody } = SpecPrPublisher.buildPrTitleAndBody(specSummary, {
      branch: targetBranch,
      customTitle: title,
    });

    let prInfo = null;
    if (pushed) {
      const existingPrs = this.git.runHubJson(
        ["pr", "list", "--head", targetBranch, "--state", "open", "--json", "number,title,url,author,isDraft"],
        { allowFailure: true },
      );
      if (Array.isArray(existingPrs) && existingPrs.length > 0) {
        const existing = existingPrs[0];
        prInfo = {
          created: false,
          number: Number(existing.number) || null,
          url: String(existing.url || ""),
          title: String(existing.title || prTitle),
          is_draft: Boolean(existing.isDraft),
        };
      } else {
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-spec-pr-"));
        try {
          const bodyPath = path.join(tmpDir, "pr-body.md");
          fs.writeFileSync(bodyPath, prBody, "utf8");
          const createArgs = [
            "pr",
            "create",
            "--base",
            defaultBase,
            "--head",
            targetBranch,
            "--title",
            prTitle,
            "--body-file",
            bodyPath,
            "--assignee",
            "@me",
          ];
          if (draft) createArgs.push("--draft");
          const createdRes = this.git.runHub(createArgs);
          const urlMatch = createdRes.stdout.trim().match(/https?:\/\/\S+\/pull\/(\d+)/);
          prInfo = {
            created: true,
            number: urlMatch ? Number.parseInt(urlMatch[1], 10) : null,
            url: urlMatch ? urlMatch[0] : createdRes.stdout.trim(),
            title: prTitle,
            is_draft: Boolean(draft),
          };
        } finally {
          fs.rmSync(tmpDir, { recursive: true, force: true });
        }
      }
    }

    StudioCacheStore.shared({ env: this.env }).invalidateWorkspace(this.effectiveRoot);
    return {
      ok: true,
      flow_id: cleanFlow,
      branch: targetBranch,
      base: defaultBase,
      commit_sha: commitSha.slice(0, 7),
      committed,
      pushed,
      title: prTitle,
      body: prBody,
      staged_paths: relPaths,
      pr: prInfo,
    };
  }

  syncPullRequestComments(flowId = null, { prNumber = null, branch = null } = {}) {
    const meta = this.git.getRemoteMeta();
    if (!meta) return { ok: false, imported_count: 0, error: "No origin GitHub remote configured." };

    let resolvedPr = prNumber ? { number: Number(prNumber), branch: branch || null } : null;
    if (!resolvedPr) {
      const b = this.git.revParseVerify("HEAD", { abbrevRef: true });
      const targetBranch = branch || (b.ok && b.value !== "HEAD" ? b.value : null);
      if (!targetBranch) return { ok: true, imported_count: 0, pr_number: null };
      const list = this.git.runHubJson(
        ["pr", "list", "--head", targetBranch, "--state", "open", "--json", "number,headRefName,url,author"],
        { allowFailure: true },
      );
      if (!Array.isArray(list) || list.length === 0) return { ok: true, imported_count: 0, pr_number: null };
      resolvedPr = {
        number: Number(list[0].number),
        branch: String(list[0].headRefName || targetBranch),
        url: String(list[0].url || ""),
      };
    }

    const rawComments = this.git.runApiJson(
      `repos/${meta.owner}/${meta.repo}/pulls/${resolvedPr.number}/comments?per_page=100`,
      { allowFailure: true },
    );
    if (!Array.isArray(rawComments)) return { ok: true, imported_count: 0, pr_number: resolvedPr.number };

    const byAuthorAndFlow = new Map();
    let importedCount = 0;
    for (const rc of rawComments) {
      const pathStr = String(rc?.path || "").replace(/\\/g, "/");
      if (!pathStr.endsWith(".md")) continue;
      const specMatch = pathStr.match(/(?:specs|tracks)\/([^/]+)\/(.+)$/);
      if (!specMatch) continue;
      const itemFlowId = specMatch[1];
      if (flowId && itemFlowId !== flowId) continue;

      const chMatch = pathStr.match(/\/chapters\/([^/]+)\//);
      const taskMatch = pathStr.match(/\/tasks\/([^/]+)\.md$/);
      const lineEnd = Number(rc.line ?? rc.original_line) || null;
      const lineStart = Number(rc.start_line ?? rc.original_start_line ?? lineEnd) || null;
      const login = String(rc.user?.login || "reviewer");
      const authorEmail = String(rc.user?.email || `${login}@github`);
      const authorSlug = slugifyToken(login, "reviewer");

      const comment = SpecComment.normalize({
        id: `gh-pr-${rc.id}`,
        ghPrCommentId: String(rc.id),
        parentCommentId: rc.in_reply_to_id ? `gh-pr-${rc.in_reply_to_id}` : null,
        authorEmail,
        authorName: String(rc.user?.name || login),
        relPath: pathStr,
        gitBranch: resolvedPr.branch || null,
        commitSha: rc.commit_id ? String(rc.commit_id).slice(0, 7) : null,
        chapterId: chMatch ? chMatch[1] : null,
        taskId: taskMatch ? taskMatch[1].split("-")[0] : null,
        lineStart,
        lineEnd,
        quotedText: rc.diff_hunk ? String(rc.diff_hunk).split("\n").slice(-2).join("\n").slice(0, 240) : null,
        commentKind: "feedback",
        state: "open",
        body: String(rc.body || "").trim(),
        createdAt: rc.created_at || new Date().toISOString(),
        updatedAt: rc.updated_at || rc.created_at || new Date().toISOString(),
      });

      const key = `${itemFlowId}::${authorSlug}`;
      if (!byAuthorAndFlow.has(key)) {
        byAuthorAndFlow.set(key, {
          flowId: itemFlowId,
          authorSlug,
          authorEmail,
          authorName: comment.authorName,
          comments: [],
        });
      }
      byAuthorAndFlow.get(key).comments.push(comment);
      importedCount += 1;
    }

    for (const group of byAuthorAndFlow.values()) {
      this.feedback.writeMergedAuthorBatch({
        flowId: group.flowId,
        authorEmail: group.authorEmail,
        authorName: group.authorName,
        authorSlug: group.authorSlug,
        comments: group.comments,
      });
    }
    StudioCacheStore.shared({ env: this.env }).invalidateWorkspace(this.effectiveRoot);
    return { ok: true, imported_count: importedCount, pr_number: resolvedPr.number };
  }

  publishPullRequestReview(
    flowId,
    { prNumber = null, branch = null, event = "COMMENT", commentIds = null, confirmForeignPr = false } = {},
  ) {
    const cleanFlow = String(flowId || "").trim();
    if (!cleanFlow) throw new Error("flowId is required.");
    const meta = this.git.getRemoteMeta();
    if (!meta) throw new Error("No origin GitHub remote configured.");

    const b = this.git.revParseVerify("HEAD", { abbrevRef: true });
    const targetBranch = branch || (b.ok && b.value !== "HEAD" ? b.value : null);

    let pr = null;
    if (prNumber) {
      pr = this.git.runHubJson(
        ["pr", "view", String(prNumber), "--json", "number,url,author,headRefOid,headRefName"],
        { allowFailure: true },
      );
    } else if (targetBranch) {
      const list = this.git.runHubJson(
        ["pr", "list", "--head", targetBranch, "--state", "open", "--json", "number,url,author,headRefOid,headRefName"],
        { allowFailure: true },
      );
      if (Array.isArray(list) && list.length > 0) pr = list[0];
    }
    if (!pr || !pr.number) throw new Error(`No open Pull Request found for '${cleanFlow}'.`);

    const viewer = this.git.runApiJson("user", { allowFailure: true });
    const viewerLogin = String(viewer?.login || "").trim().toLowerCase();
    const prAuthor = String(pr.author?.login || "").trim();
    if (prAuthor && viewerLogin && prAuthor.toLowerCase() !== viewerLogin && confirmForeignPr !== true) {
      return {
        ok: false,
        requires_confirmation: true,
        pr_number: Number(pr.number),
        pr_url: String(pr.url || ""),
        pr_author: prAuthor,
        error: `Confirmation required before posting a review on PR #${pr.number} authored by ${prAuthor}.`,
      };
    }

    const specDir = this.#locateLocalSpecDir(cleanFlow);
    const defaultRel = specDir
      ? path.relative(this.effectiveRoot, path.join(specDir, "spec.md")).split(path.sep).join("/")
      : `${this.setup.bundle_root}/specs/${cleanFlow}/spec.md`;
    const allComments = this.feedback.listForFlow(cleanFlow);
    const allowIds = Array.isArray(commentIds) && commentIds.length > 0 ? new Set(commentIds) : null;
    const candidates = allComments.filter(
      (c) =>
        c.state === "open" &&
        c.commentKind !== "approval" &&
        !c.ghPrCommentId &&
        (!allowIds || allowIds.has(c.id)),
    );

    const reviewComments = candidates.map((c) => {
      const relPath = c.relPath || defaultRel;
      const line =
        Number.isInteger(c.lineEnd) && c.lineEnd >= 1
          ? c.lineEnd
          : Number.isInteger(c.lineStart) && c.lineStart >= 1
            ? c.lineStart
            : 1;
      const item = { path: relPath, line, side: "RIGHT", body: String(c.body || "").replace(/!/g, ".").trim() };
      if (Number.isInteger(c.lineStart) && c.lineStart >= 1 && c.lineStart < line) {
        item.start_line = c.lineStart;
        item.start_side = "RIGHT";
      }
      return item;
    });

    const normalizedEvent = ["COMMENT", "APPROVE", "REQUEST_CHANGES"].includes(String(event).toUpperCase())
      ? String(event).toUpperCase()
      : "COMMENT";
    const payload = {
      ...(pr.headRefOid ? { commit_id: String(pr.headRefOid) } : {}),
      event: normalizedEvent,
      body: `Specification review feedback for \`${cleanFlow}\`.`,
      comments: reviewComments,
    };

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-pr-review-"));
    try {
      const jsonPath = path.join(tmpDir, "review.json");
      fs.writeFileSync(jsonPath, JSON.stringify(payload), "utf8");
      const posted = this.git.runHubJson([
        "api",
        `repos/${meta.owner}/${meta.repo}/pulls/${pr.number}/reviews`,
        "--method",
        "POST",
        "--input",
        jsonPath,
      ]);
      const stampedReviewId = Number.isInteger(Number(posted?.id)) && Number(posted?.id) > 0 ? Number(posted.id) : 1;
      for (let i = 0; i < candidates.length; i += 1) {
        const c = candidates[i];
        this.feedback.writeMergedAuthorBatch({
          flowId: cleanFlow,
          authorEmail: c.authorEmail,
          authorName: c.authorName,
          authorSlug: slugifyToken(c.authorEmail || c.authorName, "reviewer"),
          comments: [{ ...c, ghPrCommentId: String(stampedReviewId + i), updatedAt: new Date().toISOString() }],
        });
      }
      return {
        ok: true,
        pr_number: Number(pr.number),
        pr_url: String(pr.url || ""),
        posted_comments: reviewComments.length,
        exported_count: reviewComments.length,
        review_id: posted?.id || null,
      };
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  }

  #locateLocalSpecDir(flowId) {
    for (const root of discoverSpecRoots(this.effectiveRoot)) {
      const cand = path.join(root.root, flowId);
      if (fs.existsSync(path.join(cand, "spec.md"))) return cand;
    }
    return null;
  }

  #readMinimalLocalSpecSummary(specDir, flowId) {
    const specPath = path.join(specDir, "spec.md");
    const doc = FrontmatterDocument.parse(fs.readFileSync(specPath, "utf8"));
    const chDir = path.join(specDir, "chapters");
    const chapters =
      fs.existsSync(chDir) && fs.statSync(chDir).isDirectory()
        ? fs
            .readdirSync(chDir, { withFileTypes: true })
            .filter((d) => d.isDirectory())
            .map((d) => ({ chapter_id: d.name }))
        : [];
    const tasksDir = path.join(specDir, "tasks");
    const taskCount =
      fs.existsSync(tasksDir) && fs.statSync(tasksDir).isDirectory()
        ? fs.readdirSync(tasksDir).filter((n) => n.endsWith(".md") && !FRONTMATTER_FREE_NAMES.has(n)).length
        : 0;
    return {
      flow_id: flowId,
      title: doc.text("title") || extractH1(doc.body) || flowId,
      description: doc.text("description") || "",
      has_chapters: chapters.length > 0,
      chapters,
      task_counts: { total: taskCount },
      rel_path: path.relative(this.effectiveRoot, specPath).split(path.sep).join("/"),
    };
  }
}

/**
 * Publishes specs, `DISCUSSION.md`, `feedback/*.json`, and root `README.md` onto the `flow-specs` orphan hub branch.
 */
export class OrphanSpecBranchSync {
  static renderDiscussionMarkdown({ flowId, title, branch = null, prUrl = null, prNumber = null, comments = [] } = {}) {
    const cleanTitle = String(title || flowId).trim();
    const counts = SpecComment.summarize(comments);
    const metaParts = [`Flow: \`${flowId}\``];
    if (branch) metaParts.push(`Branch: \`${branch}\``);
    if (prNumber && prUrl) metaParts.push(`PR: [#${prNumber}](${prUrl})`);
    metaParts.push(`Open: ${counts.openCommentCount} | Addressed: ${counts.addressedCommentCount} | Approvals: ${counts.approvalCount}`);

    const lines = [`# Discussion: ${cleanTitle}`, "", metaParts.join(" · "), ""];
    if (!Array.isArray(comments) || comments.length === 0) {
      lines.push("No review comments recorded yet.");
      return ensureSingleTrailingNewline(lines.join("\n"));
    }

    const byParent = new Map();
    const roots = [];
    const byId = new Set(comments.map((c) => c.id));
    for (const c of comments) {
      if (c.parentCommentId && byId.has(c.parentCommentId)) {
        if (!byParent.has(c.parentCommentId)) byParent.set(c.parentCommentId, []);
        byParent.get(c.parentCommentId).push(c);
      } else {
        roots.push(c);
      }
    }

    const appendThread = (item, depth = 0) => {
      const indent = "  ".repeat(depth);
      const loc = [item.relPath, item.chapterId, item.taskId, item.lineAnchor].filter(Boolean).join(" · ");
      lines.push(
        `${indent}- **[${item.state}/${item.commentKind}]** ${item.authorName} (\`${item.authorEmail}\`)${loc ? ` — \`${loc}\`` : ""}`,
      );
      if (item.quotedText) {
        for (const ql of String(item.quotedText).trim().split(/\r?\n/)) {
          lines.push(`${indent}  > ${ql}`);
        }
      }
      for (const bl of String(item.body || "").trim().split(/\r?\n/)) {
        lines.push(`${indent}  ${bl}`);
      }
      for (const reply of byParent.get(item.id) || []) {
        appendThread(reply, depth + 1);
      }
    };

    for (const root of roots) appendThread(root, 0);
    return ensureSingleTrailingNewline(lines.join("\n"));
  }

  static renderRootReadmeMarkdown(specs = [], branchName = DEFAULT_SPEC_BRANCH) {
    const lines = [
      `# Active Specifications (\`${branchName}\`)`,
      "",
      "Cross-branch specification and review hub. Browse any spec or discussion directly in GitHub or open this repository in Flow Studio.",
      "",
      "| Spec | State | Tasks | Branch | PR | Feedback | Discussion |",
      "| --- | --- | --- | --- | --- | --- | --- |",
    ];
    if (!Array.isArray(specs) || specs.length === 0) {
      lines.push("| _No active specs_ | - | - | - | - | - | - |");
      return ensureSingleTrailingNewline(lines.join("\n"));
    }
    for (const s of [...specs].sort((a, b) => a.flow_id.localeCompare(b.flow_id))) {
      const tasksLabel = `${s.task_counts?.completed || 0}/${s.task_counts?.total || 0}`;
      const branchLabel = s.source_branch ? `\`${s.source_branch}\`` : "-";
      const prLabel = s.pr_number && s.pr_url ? `[#${s.pr_number}](${s.pr_url})` : "-";
      const fbLabel = `${s.open_comment_count || 0} open / ${s.approval_count || 0} approved`;
      lines.push(
        `| [${s.title}](specs/${s.flow_id}/spec.md) | \`${s.state || "planned"}\` | \`${tasksLabel}\` | ${branchLabel} | ${prLabel} | ${fbLabel} | [Thread](specs/${s.flow_id}/DISCUSSION.md) |`,
      );
    }
    return ensureSingleTrailingNewline(lines.join("\n"));
  }

  constructor(workspacePath, { env = process.env, specBranch = null } = {}) {
    this.workspace = path.resolve(workspacePath);
    const setup = readSetupConfig(this.workspace);
    this.setup = setup;
    this.specBranch = specBranch || setup.spec_branch || DEFAULT_SPEC_BRANCH;
    this.effectiveRoot = setup.effective_root || this.workspace;
    this.env = env;
    this.git = GitRunner.forWorkspace(this.effectiveRoot, { timeoutMs: 12000, env });
    this.scanner = new GitBranchSpecScanner(this.effectiveRoot, { env });
    this.feedback = new SpecFeedbackStore(this.effectiveRoot, { env });
  }

  sync({ flowId = null, push = false, localOnly = false } = {}) {
    if (!this.git.isGitRepo()) throw new Error("Workspace is not a Git repository.");
    const hasOrigin = !localOnly && this.git.remoteUrl("origin").ok;
    return this.#syncAttempt({ flowId, push: Boolean(push && hasOrigin), hasOrigin, retry: true });
  }

  #syncAttempt({ flowId, push, hasOrigin, retry }) {
    if (hasOrigin) {
      this.git.readGit(
        ["fetch", "--no-tags", "origin", `refs/heads/${this.specBranch}:refs/remotes/origin/${this.specBranch}`],
        { timeoutMs: 12000 },
      );
    }

    const remoteOrphanRef = `refs/remotes/origin/${this.specBranch}`;
    const localOrphanRef = `refs/heads/${this.specBranch}`;
    const hasRemoteOrphan = this.git.revParseVerify(remoteOrphanRef).ok;
    const hasLocalOrphan = this.git.revParseVerify(localOrphanRef).ok;
    const baseOrphanRef = hasRemoteOrphan ? remoteOrphanRef : hasLocalOrphan ? localOrphanRef : null;
    const baseOrphanSha = baseOrphanRef ? this.git.revParseVerify(baseOrphanRef).value : null;

    if (baseOrphanRef) {
      const lsFb = this.git.readGit(["ls-tree", "-r", "--full-tree", baseOrphanRef, "--", "specs"]);
      if (lsFb.ok) {
        for (const line of lsFb.stdout.split(/\r?\n/)) {
          const tabIdx = line.indexOf("\t");
          if (tabIdx < 0) continue;
          const meta = line.slice(0, tabIdx).trim().split(/\s+/);
          const rel = line.slice(tabIdx + 1).trim();
          const m = rel.match(/^specs\/([^/]+)\/feedback\/([^/]+)\.json$/);
          if (!m || m[2].startsWith("_")) continue;
          const [, fid, slug] = m;
          const raw = this.git.readGit(["cat-file", "-p", meta[2]]).stdout;
          const list = parseFeedbackJsonText(raw);
          if (list.length > 0) {
            this.feedback.writeMergedAuthorBatch({
              flowId: fid,
              authorEmail: list[0].authorEmail,
              authorName: list[0].authorName,
              authorSlug: slug,
              comments: list,
            });
          }
        }
      }
    }

    const localDiskSpecs = this.#collectLocalDiskSpecs();
    const allSpecs = this.scanner.listAllBranchSpecs({ localSpecs: localDiskSpecs, includeArchived: false });
    const targetSpecs = flowId ? allSpecs.filter((s) => s.flow_id === flowId) : allSpecs;

    const desiredEntries = new Map();
    for (const spec of targetSpecs) {
      const filesMap = this.#collectSpecBlobsForOrphan(spec);
      for (const [subRel, content] of filesMap.entries()) {
        desiredEntries.set(`specs/${spec.flow_id}/${subRel}`, ensureSingleTrailingNewline(content));
      }

      const comments = this.feedback.listForFlow(spec.flow_id);
      const bySlug = new Map();
      for (const c of comments) {
        const slug = slugifyToken(c.authorEmail || c.authorName, "author");
        if (!bySlug.has(slug)) bySlug.set(slug, { authorEmail: c.authorEmail, authorName: c.authorName, comments: [] });
        bySlug.get(slug).comments.push(SpecComment.stripDerived(c));
      }
      for (const [slug, group] of bySlug.entries()) {
        desiredEntries.set(
          `specs/${spec.flow_id}/feedback/${slug}.json`,
          `${JSON.stringify(
            { authorEmail: group.authorEmail, authorName: group.authorName, authorSlug: slug, updatedAt: new Date().toISOString(), comments: group.comments },
            null,
            2,
          )}\n`,
        );
      }
      desiredEntries.set(
        `specs/${spec.flow_id}/DISCUSSION.md`,
        OrphanSpecBranchSync.renderDiscussionMarkdown({
          flowId: spec.flow_id,
          title: spec.title,
          branch: spec.source_branch,
          prUrl: spec.pr_url,
          prNumber: spec.pr_number,
          comments,
        }),
      );
    }

    const readmeSpecs = flowId ? allSpecs : targetSpecs;
    desiredEntries.set("README.md", OrphanSpecBranchSync.renderRootReadmeMarkdown(readmeSpecs, this.specBranch));

    const identity = resolveGitIdentity(this.effectiveRoot, { env: this.env });
    const commitEnv = {
      ...process.env,
      ...(this.env || {}),
      GIT_AUTHOR_NAME: identity.name,
      GIT_AUTHOR_EMAIL: identity.email,
      GIT_COMMITTER_NAME: identity.name,
      GIT_COMMITTER_EMAIL: identity.email,
    };
    const signArgs = this.git.shouldSignCommits() ? ["-S"] : [];
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-orphan-idx-"));
    const tempIndex = path.join(tmpDir, "index");
    const idxEnv = { ...commitEnv, GIT_INDEX_FILE: tempIndex };
    let commitSha = baseOrphanSha;
    let committed = false;

    try {
      if (baseOrphanSha) {
        this.git.runGit(["read-tree", baseOrphanSha], { cwd: this.effectiveRoot, env: idxEnv });
        if (!flowId) {
          const existingLs = this.git.readGit(["ls-files"], { env: idxEnv });
          const activePrefixes = new Set(targetSpecs.map((s) => `specs/${s.flow_id}/`));
          for (const existingPath of (existingLs.stdout || "").split(/\r?\n/).filter(Boolean)) {
            if (existingPath === "README.md") continue;
            if (existingPath.startsWith("specs/") && ![...activePrefixes].some((p) => existingPath.startsWith(p))) {
              this.git.runGit(["update-index", "--force-remove", "--", existingPath], { cwd: this.effectiveRoot, env: idxEnv });
            }
          }
        }
      }

      for (const [relPath, text] of desiredEntries.entries()) {
        const blobSha = this.git
          .runGit(["hash-object", "-w", "--stdin"], { cwd: this.effectiveRoot, env: idxEnv, input: text })
          .stdout.trim();
        this.git.runGit(["update-index", "--add", "--cacheinfo", `100644,${blobSha},${relPath}`], {
          cwd: this.effectiveRoot,
          env: idxEnv,
        });
      }

      const treeSha = this.git.runGit(["write-tree"], { cwd: this.effectiveRoot, env: idxEnv }).stdout.trim();
      const prevTreeSha = baseOrphanSha ? this.git.revParseVerify(`${baseOrphanSha}^{tree}`).value : null;
      if (treeSha !== prevTreeSha) {
        const parentArgs = [];
        if (baseOrphanSha) parentArgs.push("-p", baseOrphanSha);
        if (hasLocalOrphan && hasRemoteOrphan) {
          const localSha = this.git.revParseVerify(localOrphanRef).value;
          if (localSha && localSha !== baseOrphanSha && !this.git.readGit(["merge-base", "--is-ancestor", localSha, baseOrphanSha]).ok) {
            parentArgs.push("-p", localSha);
          }
        }
        const msg = flowId ? `chore(specs): sync ${flowId} on ${this.specBranch}` : `chore(specs): sync active specifications`;
        commitSha = this.git
          .runGit(["commit-tree", treeSha, ...parentArgs, ...signArgs, "-m", msg], { cwd: this.effectiveRoot, env: commitEnv })
          .stdout.trim();
        committed = true;
      }
      if (commitSha) {
        this.git.runGit(["update-ref", localOrphanRef, commitSha], { cwd: this.effectiveRoot, env: commitEnv });
      }
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }

    let pushed = false;
    if (push && commitSha) {
      const pushRes = this.git.runGit(["push", "origin", `${localOrphanRef}:refs/heads/${this.specBranch}`], {
        cwd: this.effectiveRoot,
        allowFailure: true,
        env: commitEnv,
      });
      if (pushRes.status === 0) pushed = true;
      else if (retry) return this.#syncAttempt({ flowId, push, hasOrigin, retry: false });
      else throw new Error(`Failed to push ${this.specBranch} to origin: ${(pushRes.stderr || pushRes.stdout).trim()}`);
    }

    StudioCacheStore.shared({ env: this.env }).invalidateWorkspace(this.effectiveRoot);
    return {
      ok: true,
      branch: this.specBranch,
      commit_sha: commitSha ? commitSha.slice(0, 7) : null,
      committed,
      pushed,
      synced_specs: targetSpecs.map((s) => s.flow_id),
    };
  }

  #collectLocalDiskSpecs() {
    const out = [];
    const seenFlows = new Set();
    for (const root of discoverSpecRoots(this.effectiveRoot)) {
      if (!fs.existsSync(root.root)) continue;
      for (const entry of fs.readdirSync(root.root, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const specDir = path.join(root.root, entry.name);
        const specFile = path.join(specDir, "spec.md");
        if (!fs.existsSync(specFile)) continue;
        const doc = FrontmatterDocument.parse(fs.readFileSync(specFile, "utf8"));
        const flowId = doc.text("flow_id") || entry.name;
        if (seenFlows.has(flowId)) continue;
        seenFlows.add(flowId);
        const allMd = walkFiles(specDir, { extensions: [".md"], maxDepth: 5 });
        const taskFiles = allMd.filter(
          (p) => p.includes(`${path.sep}tasks${path.sep}`) && !FRONTMATTER_FREE_NAMES.has(path.basename(p)),
        );
        const tasks = taskFiles.map((tf) => ({ state: (FrontmatterDocument.parse(fs.readFileSync(tf, "utf8")).text("state") || "pending").toLowerCase() }));
        const counts = summarizeTasks(tasks);
        const fbCounts = SpecComment.summarize(this.feedback.listForFlow(flowId));
        out.push({
          flow_id: flowId,
          title: doc.text("title") || extractH1(doc.body) || flowId,
          description: doc.text("description") || "",
          state: normalizeSpecState(doc.text("state") || doc.text("status"), tasks),
          plan_revision: doc.integer("plan_revision") ?? 1,
          spec_dir: specDir,
          rel_path: path.relative(this.effectiveRoot, specFile).split(path.sep).join("/"),
          task_counts: counts,
          open_comment_count: fbCounts.openCommentCount,
          addressed_comment_count: fbCounts.addressedCommentCount,
          approval_count: fbCounts.approvalCount,
        });
      }
    }
    return out;
  }

  #collectSpecBlobsForOrphan(spec) {
    const files = new Map();
    if (spec.spec_dir && fs.existsSync(spec.spec_dir)) {
      for (const absPath of walkFiles(spec.spec_dir, { extensions: [".md"], maxDepth: 6 })) {
        const subRel = path.relative(spec.spec_dir, absPath).split(path.sep).join("/");
        if (subRel === "DISCUSSION.md") continue;
        files.set(subRel, fs.readFileSync(absPath, "utf8"));
      }
      return files;
    }
    if (spec.git_ref && spec.source_root) {
      const prefix = `${spec.source_root}/${spec.flow_id}`;
      const ls = this.git.readGit(["ls-tree", "-r", "--full-tree", spec.git_ref, "--", prefix]);
      if (ls.ok) {
        for (const line of ls.stdout.split(/\r?\n/)) {
          const tabIdx = line.indexOf("\t");
          if (tabIdx < 0) continue;
          const meta = line.slice(0, tabIdx).trim().split(/\s+/);
          const relPath = line.slice(tabIdx + 1).trim();
          if (meta[1] !== "blob" || !relPath.endsWith(".md")) continue;
          const subRel = relPath.slice(prefix.length + 1);
          if (!subRel || subRel === "DISCUSSION.md") continue;
          const blob = this.git.readGit(["cat-file", "-p", meta[2]]);
          if (blob.ok) files.set(subRel, blob.stdout);
        }
      }
    }
    return files;
  }
}

/**
 * Zero-clone remote GitHub repository spec reader and feedback writer via `gh api`.
 */
export class RemoteRepoSpecClient {
  constructor(repoLocatorInput, { workspacePath = null, env = process.env, hubBinary = null, specBranch = DEFAULT_SPEC_BRANCH } = {}) {
    const parsed = RepoLocator.parseSlug(repoLocatorInput);
    if (!parsed || !parsed.owner || !parsed.repo) {
      throw new Error(`Invalid repository locator '${repoLocatorInput}'. Expected 'owner/repo' or remote URL.`);
    }
    this.owner = parsed.owner;
    this.repo = parsed.repo;
    this.host = parsed.host || "github.com";
    this.repoSlug = `${this.owner}/${this.repo}`;
    this.specBranch = specBranch || DEFAULT_SPEC_BRANCH;
    this.env = env;
    this.cache = StudioCacheStore.shared({ env });
    this.feedback = new SpecFeedbackStore(null, { env, repoLocator: this.repoSlug });
    const cwd = workspacePath && fs.existsSync(workspacePath) ? path.resolve(workspacePath) : os.tmpdir();
    this.git = GitRunner.forWorkspace(cwd, { hubBinary, timeoutMs: 15000, env });
  }

  listSpecs({ includeOpenPrs = true } = {}) {
    const specsByFlow = new Map();
    const orphanTree = this.#fetchTree(this.specBranch);
    if (orphanTree) {
      for (const item of this.#extractSpecsFromRemoteTree(orphanTree.tree, this.specBranch)) {
        specsByFlow.set(item.flow_id, item);
      }
    }
    if (includeOpenPrs) {
      const prs = this.git.runApiJson(`repos/${this.owner}/${this.repo}/pulls?state=open&per_page=30`, {
        allowFailure: true,
        host: this.host,
      });
      if (Array.isArray(prs)) {
        for (const pr of prs) {
          const headSha = pr?.head?.sha;
          const headRef = pr?.head?.ref;
          if (!headSha || !headRef) continue;
          const prTree = this.#fetchTree(headSha);
          if (!prTree) continue;
          for (const spec of this.#extractSpecsFromRemoteTree(prTree.tree, headRef, { commitSha: headSha })) {
            const existing = specsByFlow.get(spec.flow_id);
            const enriched = {
              ...spec,
              pr_number: Number(pr.number) || null,
              pr_url: String(pr.html_url || ""),
              pr_title: String(pr.title || ""),
              pr_author: String(pr.user?.login || ""),
            };
            if (!existing || existing.source_branch === this.specBranch) {
              specsByFlow.set(spec.flow_id, enriched);
            }
          }
        }
      }
    }
    return [...specsByFlow.values()];
  }

  readDocument(relPath, { gitRef = this.specBranch } = {}) {
    const cleanRel = String(relPath || "").trim().replace(/^\/+/, "");
    const treeObj = this.#fetchTree(gitRef);
    if (!treeObj) throw new Error(`Ref '${gitRef}' was not found in '${this.repoSlug}'.`);
    const entry = treeObj.tree.find((t) => t.type === "blob" && t.path === cleanRel);
    if (!entry) throw new Error(`Document '${cleanRel}' was not found in '${this.repoSlug}@${gitRef}'.`);
    const raw = this.#fetchBlobText(entry.sha);
    const doc = FrontmatterDocument.parse(raw);
    const match = cleanRel.match(/^(?:(?:\.agents|_agents)\/bundles\/specs|(?:\.agents|_agents|\.flow)\/specs|specs)\/([^/]+)\/(.+)$/);
    const flowId = doc.text("flow_id") || (match ? match[1] : null);
    return {
      ok: true,
      repo_locator: this.repoSlug,
      git_ref: gitRef,
      relPath: cleanRel,
      rel_path: cleanRel,
      title: doc.text("title") || extractH1(doc.body) || path.posix.basename(cleanRel),
      flowId,
      flow_id: flowId,
      frontmatter: doc.data,
      markdown: doc.body,
      raw,
      lines: raw.split(/\r?\n/).map((text, idx) => ({ lineNumber: idx + 1, text })),
      body_start_line: doc.bodyLine,
      comments: flowId ? this.feedback.listForFlow(flowId).filter((c) => !c.relPath || c.relPath === cleanRel) : [],
    };
  }

  getSpecReview(flowId, { gitRef = this.specBranch } = {}) {
    const cleanFlow = String(flowId || "").trim();
    const specs = this.listSpecs({ includeOpenPrs: true });
    const spec = specs.find((s) => s.flow_id === cleanFlow);
    if (!spec) throw new Error(`Spec '${cleanFlow}' was not found in '${this.repoSlug}'.`);
    const effectiveRef = spec.git_ref || gitRef;
    const doc = this.readDocument(spec.rel_path, { gitRef: effectiveRef });
    const comments = this.feedback.listForFlow(cleanFlow);
    const counts = SpecComment.summarize(comments);
    return {
      ok: true,
      id: cleanFlow,
      flowId: cleanFlow,
      title: spec.title,
      repoLocator: this.repoSlug,
      gitBranch: spec.source_branch || effectiveRef,
      gitRef: effectiveRef,
      planRevision: spec.plan_revision ?? 1,
      reviewState: counts.openCommentCount > 0 ? "in_review" : counts.approvalCount > 0 ? "approved" : "draft",
      specMarkdown: doc.raw,
      dag: SpecEngine.buildDagFromSpec(spec, comments.filter((c) => c.state === "open" && c.commentKind !== "approval")),
      contentSha256: sha256Hex(doc.raw),
      ...counts,
      comments,
      revisePromptMarkdown: this.feedback.buildRevisePrompt(cleanFlow, cleanFlow, comments),
    };
  }

  #fetchTree(ref) {
    const cleanRef = encodeURIComponent(String(ref || this.specBranch));
    const res = this.git.runApiJson(`repos/${this.owner}/${this.repo}/git/trees/${cleanRef}?recursive=1`, {
      allowFailure: true,
      host: this.host,
    });
    return res && Array.isArray(res.tree) ? res : null;
  }

  #fetchBlobText(blobSha) {
    return this.cache.getOrComputeWorkspace(
      path.join(os.tmpdir(), `flow-remote-${this.owner}-${this.repo}`),
      "blob_v1",
      blobSha,
      () => {
        const blob = this.git.runApiJson(`repos/${this.owner}/${this.repo}/git/blobs/${blobSha}`, { host: this.host });
        if (!blob || typeof blob.content !== "string") {
          throw new Error(`Unable to fetch blob '${blobSha}' from '${this.repoSlug}'.`);
        }
        const enc = blob.encoding === "utf-8" || blob.encoding === "utf8" ? "utf8" : "base64";
        return Buffer.from(blob.content.replace(/\s+/g, ""), enc).toString("utf8");
      },
    );
  }

  #extractSpecsFromRemoteTree(treeItems, branchName, { commitSha = null } = {}) {
    const byFlow = new Map();
    for (const item of treeItems) {
      if (item.type !== "blob") continue;
      const m = item.path.match(/^((?:\.agents|_agents)\/bundles\/specs|(?:\.agents|_agents|\.flow)\/specs|specs)\/([^/]+)\/(.+)$/);
      if (!m) continue;
      const [, specRoot, flowId, subPath] = m;
      const key = `${specRoot}::${flowId}`;
      if (!byFlow.has(key)) byFlow.set(key, { specRoot, flowId, files: new Map() });
      byFlow.get(key).files.set(subPath, item);
    }
    const out = [];
    for (const bucket of byFlow.values()) {
      const rootEntry = bucket.files.get("spec.md");
      if (!rootEntry) continue;
      const raw = this.#fetchBlobText(rootEntry.sha);
      const doc = FrontmatterDocument.parse(raw);
      const flowId = doc.text("flow_id") || bucket.flowId;
      out.push({
        flow_id: flowId,
        title: doc.text("title") || extractH1(doc.body) || flowId,
        description: doc.text("description") || "",
        state: normalizeSpecState(doc.text("state") || doc.text("status"), []),
        source_root: bucket.specRoot,
        source_branch: branchName,
        git_ref: branchName,
        commit_sha: commitSha ? commitSha.slice(0, 7) : null,
        rel_path: rootEntry.path,
        chapters: [],
        tasks: [],
        task_counts: { total: 0, completed: 0, in_progress: 0, pending: 0, blocked: 0, deferred: 0 },
      });
    }
    return out;
  }
}
