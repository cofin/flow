/**
 * @fileoverview Workspace sync for `flow sync`, `flow status`, Studio Sync button,
 * and the `flow_sync` MCP tool.
 */

import fs from "node:fs";
import path from "node:path";

import { FrontmatterCodec } from "../core/frontmatter.mjs";
import { isClosedState, readTextSafe, writeTextAtomic } from "../core/fs-io.mjs";
import { GitRunner } from "../core/git.mjs";
import { DEFAULT_SPEC_BRANCH } from "../core/worktree.mjs";
import { AgentsBranchSync, OrphanSpecBranchSync } from "./git-spec-branch.mjs";
import { SpecActivity } from "./spec-activity.mjs";
import { SpecEngine } from "./spec-engine.mjs";

const HEX_SHA_RE = /^[0-9a-fA-F]{7,40}$/;
const MAX_COMMITS = 200;
const FRESH_CLAIM_MS = 15 * 60 * 1000;
const MAX_ATTENTION_PROBLEMS = 5;

/**
 * Syncs one workspace's spec files with Git and disk and compiles the status/sync report.
 */
export class WorkspaceSync {
  constructor(workspace, { env = process.env } = {}) {
    this.workspace = path.resolve(workspace);
    this.env = env;
  }

  static studioLink(flowId, title = "") {
    const label = String(title || flowId).replace(/[[\]]/g, "");
    return `[Spec: ${label}](sidecar://flow/studio/?flow=${encodeURIComponent(flowId)})`;
  }

  static finalize(report) {
    const count = (list) => (Array.isArray(list) ? list.length : 0);
    const verb = report.dry_run ? "would" : null;
    const parts = [];
    const addPart = (n, done, pending) => {
      if (n > 0) parts.push(verb ? `${verb} ${pending.replace("%d", String(n))}` : done.replace("%d", String(n)));
    };
    addPart(count(report.closed_tasks), "closed %d task(s)", "close %d task(s)");
    addPart(count(report.stamped_commits), "recorded %d commit(s)", "record %d commit(s)");
    addPart(count(report.released_claims), "freed %d claim(s)", "free %d claim(s)");
    addPart(count(report.updated_files), "updated %d file(s)", "update %d file(s)");
    if (report.branch_sync?.resolved_conflicts?.length) {
      addPart(report.branch_sync.resolved_conflicts.length, "resolved %d conflict(s)", "resolve %d conflict(s)");
    }
    if (report.orphan_sync?.committed || report.orphan_sync?.pushed) {
      const targetBranch = report.orphan_sync.branch || DEFAULT_SPEC_BRANCH;
      parts.push(report.orphan_sync.pushed ? `pushed ${targetBranch}` : `updated ${targetBranch}`);
    }
    const head = parts.length > 0 ? parts.join(", ") : "already in sync";
    report.summary = `Sync: ${head}.`;

    const attention = [];
    const looksDone = report.looks_done || [];
    for (const item of looksDone.slice(0, MAX_ATTENTION_PROBLEMS)) {
      attention.push(`Looks done, not confirmed: ${item.task_id} (commit ${item.commit} touched its files)`);
    }
    if (looksDone.length > MAX_ATTENTION_PROBLEMS) {
      attention.push(`Looks done, not confirmed: ${looksDone.length - MAX_ATTENTION_PROBLEMS} more (see --json)`);
    }
    for (const item of report.missing_commits || []) {
      attention.push(`Commit not in history: ${item.task_id} records ${item.commit}`);
    }
    for (const item of (report.problems || []).slice(0, MAX_ATTENTION_PROBLEMS)) {
      attention.push(`Problem: ${item.path ? `${item.path}: ` : ""}${item.message}`);
    }
    report.attention = attention;

    if (count(report.looks_done) > 0) report.next = "flow sync";
    else if (report.next_runnable_flow) report.next = `/flow:implement ${report.next_runnable_flow}`;
    else if (report.finishable_flow) report.next = `/flow:finish ${report.finishable_flow}`;
    else report.next = null;
    return report;
  }

  static renderText(report) {
    const lines = [report.summary];
    for (const item of report.closed_tasks || []) lines.push(`  closed ${item.task_id} (${item.commit})`);
    for (const item of report.stamped_commits || []) lines.push(`  recorded ${item.commit} on ${item.task_id}`);
    for (const item of report.released_claims || []) lines.push(`  freed claim on ${item.task_id}`);
    if (Array.isArray(report.live) && report.live.length > 0) {
      lines.push("Now:");
      for (const item of report.live) {
        if (item.phase && item.phase !== "idle") {
          lines.push(`  ${item.flow_id}: phase=${item.phase}${item.phase_detail ? ` (${item.phase_detail})` : ""}`);
        }
        for (const task of item.active_tasks || []) {
          const who = task.claimed_by || task.conversation_id || "active";
          const fileNote = task.last_path ? ` · ${task.last_path}` : "";
          const tag = task.certain === false ? " (possibly working)" : "";
          lines.push(`  ${task.task_id}${tag} — ${who}${fileNote}`);
        }
      }
    }
    for (const line of report.attention || []) lines.push(line);
    if (report.next) lines.push(`Next: ${report.next}`);
    for (const link of report.links || []) lines.push(link);
    return `${lines.join("\n")}\n`;
  }

  run({
    flowId = null,
    chapterId = null,
    dryRun = false,
    useGit = true,
    local = false,
    syncBranch = false,
    pushBranch = false,
    releaseStale = true,
    stampHead = false,
    acknowledge = true,
  } = {}) {
    const branchSync = useGit
      ? new AgentsBranchSync(this.workspace, { env: this.env }).syncWithBranch({ flowId, local, dryRun })
      : null;

    const engine = new SpecEngine({ workspacePath: this.workspace, env: this.env });
    const targets = flowId ? [engine.status(flowId).spec] : engine.listSpecs({ includeArchived: false });
    const report = {
      ok: true,
      workspace: this.workspace,
      dry_run: Boolean(dryRun),
      specs_synced: targets.map((s) => s.flow_id),
      closed_tasks: [],
      stamped_commits: [],
      released_claims: [],
      looks_done: [],
      missing_commits: [],
      updated_files: [],
      bundle: {
        linked_worktree: engine.worktree.isLinkedWorktree,
        bundle_in: engine.worktree.effectiveAgentsRoot === engine.workspace ? "worktree" : "main",
        root: engine.bundleDir,
      },
      ...(branchSync ? { branch_sync: branchSync } : {}),
      problems: [],
      links: [],
    };

    if (useGit) {
      this.#syncGitIntoTasks(targets, report, { chapterId, dryRun, releaseStale, stampHead });
    }

    const fresh = new SpecEngine({ workspacePath: this.workspace, env: this.env });
    const updatedSet = new Set([
      ...(branchSync?.fast_forwarded || []),
      ...(branchSync?.merged_files || []),
      ...(branchSync?.resolved_conflicts || []),
    ]);
    for (const s of targets) {
      const synced = fresh.syncChecklists({ flowId: s.flow_id, chapterId, dryRun, releaseStaleClaims: false });
      for (const f of synced.updated_files || []) updatedSet.add(f);
    }
    report.updated_files = [...updatedSet];

    for (const conflictPath of branchSync?.unresolved_conflicts || []) {
      report.problems.push({
        code: "MERGE_CONFLICT_UNRESOLVED",
        path: conflictPath,
        message: "Conflicting prose edits between local .agents and remote branch require review.",
      });
    }

    if (syncBranch && useGit && !dryRun) {
      try {
        report.orphan_sync = new OrphanSpecBranchSync(this.workspace, { env: this.env }).sync({
          flowId,
          push: Boolean(pushBranch && !local),
          localOnly: local,
        });
      } catch (err) {
        report.problems.push({
          code: "ORPHAN_SYNC_FAILED",
          path: null,
          message: err instanceof Error ? err.message : "Unable to sync orphan spec branch.",
        });
      }
    }

    const changed =
      report.closed_tasks.length + report.stamped_commits.length + report.released_claims.length + report.updated_files.length;
    if (!dryRun && useGit && changed > 0 && fresh.bundleDir) {
      this.#appendLog(fresh.bundleDir, report);
      AgentsBranchSync.rebuildSpecsIndex(path.join(fresh.bundleDir, "specs"), { dryRun: false });
    }

    if (!dryRun && targets.length > 0 && acknowledge) {
      const ackSources = [...report.closed_tasks, ...report.stamped_commits, ...report.released_claims];
      const changedByFlow = new Map();
      for (const item of ackSources) {
        const fid = String(item?.task_id || "").split(":")[0];
        if (!fid) continue;
        if (!changedByFlow.has(fid)) changedByFlow.set(fid, []);
        changedByFlow.get(fid).push(item.task_id);
      }
      for (const [fid, taskIds] of changedByFlow.entries()) {
        SpecActivity.acknowledgeTasks(this.workspace, fid, taskIds, { env: this.env });
      }
    }

    const after = new SpecEngine({ workspacePath: this.workspace, env: this.env });
    const afterSpecs = after.listSpecs({ includeArchived: false });
    const nextRun = after.status(null).next_runnable;
    report.next_runnable_flow = nextRun?.flow_id || null;
    const finishable = afterSpecs.find(
      (s) => !isClosedState(s.state) && (s.task_counts?.total || 0) > 0 && s.task_counts.completed === s.task_counts.total,
    );
    report.finishable_flow = finishable?.flow_id || null;
    const shown = flowId ? afterSpecs.filter((s) => s.flow_id === flowId) : afterSpecs.filter((s) => !isClosedState(s.state));
    report.live = this.#buildLiveStatus(shown);
    report.links = shown.slice(0, 3).map((s) => WorkspaceSync.studioLink(s.flow_id, s.title));
    return report;
  }

  #buildLiveStatus(specs) {
    const overlay = SpecActivity.overlay(this.workspace, { env: this.env, prune: false });
    const out = [];
    for (const spec of specs || []) {
      const flowLive = overlay.flows?.[spec.flow_id] || null;
      const phase = flowLive?.phase || "idle";
      const allTasks = spec.has_chapters ? (spec.chapters || []).flatMap((c) => c.tasks || []) : spec.tasks || [];
      const activeTasks = [];
      for (const task of allTasks) {
        if (isClosedState(task.state)) continue;
        const rec = flowLive?.tasks?.[task.id] || null;
        if (rec || task.state === "in_progress") {
          activeTasks.push({
            task_id: task.id,
            title: task.title || task.id,
            state: task.state || "pending",
            claimed_by: task.claimed_by || null,
            conversation_id: rec?.conversation_id || null,
            last_path: rec?.last_path || null,
            started_at: task.claimed_at || rec?.started_at || null,
            last_at: rec?.last_at || task.claimed_at || null,
            working_now: Boolean(rec?.working_now),
            certain: rec ? rec.certain !== false : true,
          });
        }
      }
      if (phase !== "idle" || activeTasks.length > 0) {
        out.push({
          flow_id: spec.flow_id,
          phase,
          phase_detail: flowLive?.phase_detail || null,
          phase_since: flowLive?.phase_since || null,
          active_tasks: activeTasks,
        });
      }
    }
    return out;
  }

  #syncGitIntoTasks(targets, report, { chapterId, dryRun, releaseStale, stampHead }) {
    const git = GitRunner.forWorkspace(this.workspace, { timeoutMs: 5000, env: this.env });
    if (!git.isGitRepo()) return;
    const headRes = git.revParseVerify("HEAD", { short: 7 });
    if (!headRes.ok) return;
    const headSha = headRes.value;
    const statusRes = git.statusPorcelain({ untrackedFiles: "all", nul: true });
    const dirtyPaths = new Set(statusRes.ok ? statusRes.paths : []);
    const commitCache = new Map();
    const ancestorCache = new Map();
    const inHistory = (sha) => {
      if (!ancestorCache.has(sha)) ancestorCache.set(sha, git.readGit(["merge-base", "--is-ancestor", sha, "HEAD"]).ok);
      return ancestorCache.get(sha);
    };
    const filesOf = (commit) => {
      if (!commit.files) {
        const res = git.showNameOnly(commit.sha);
        commit.files = new Set(res.ok ? res.files : []);
      }
      return commit.files;
    };
    const updateTask = (task, updates) => {
      if (dryRun || !task.abs_path || !fs.existsSync(task.abs_path)) return;
      writeTextAtomic(task.abs_path, FrontmatterCodec.updateKeys(readTextSafe(task.abs_path) || "", updates));
    };

    const liveOverlay = releaseStale ? SpecActivity.overlay(this.workspace, { env: this.env, prune: false }) : null;
    const freshLeases = releaseStale ? SpecActivity.freshLeaseConversations(this.workspace, { env: this.env }) : null;

    for (const spec of targets) {
      const commits = this.#commitsSincePlan(git, spec, commitCache);
      const flowLive = liveOverlay?.flows?.[spec.flow_id] || null;
      const chapters = spec.has_chapters ? (spec.chapters || []).filter((c) => !chapterId || c.chapter_id === chapterId) : [];
      const tasks = spec.has_chapters ? chapters.flatMap((c) => c.tasks || []) : spec.tasks || [];

      for (const task of tasks) {
        const owned = [...(task.files || []), ...(task.tests || [])]
          .map((p) => String(p).split("::")[0].trim().replace(/^\.\//, ""))
          .filter(Boolean);
        const dirty = owned.some((p) => dirtyPaths.has(p));
        const named = commits.find((c) => WorkspaceSync.#commitNamesTask(c.message, spec, task)) || null;
        const touching = () => (owned.length > 0 ? commits.find((c) => owned.some((p) => filesOf(c).has(p))) || null : null);
        const entry = { task_id: task.id, title: task.title, path: task.rel_path };

        if (!isClosedState(task.state)) {
          if (named && !dirty) {
            updateTask(task, { state: "completed", commit: named.sha, claimed_by: null, claimed_at: null });
            report.closed_tasks.push({ ...entry, commit: named.sha });
            continue;
          }
          const candidate = dirty ? null : touching();
          if (candidate) {
            report.looks_done.push({ ...entry, commit: candidate.sha });
          } else {
            const hasLiveSession =
              Boolean(flowLive?.tasks?.[task.id]?.working_now) || SpecActivity.isClaimLive(task.claimed_by, freshLeases);
            if (
              releaseStale &&
              !dirty &&
              !hasLiveSession &&
              (task.state === "in_progress" || task.claimed_by) &&
              !WorkspaceSync.#claimIsFresh(task.claimed_at)
            ) {
              updateTask(task, {
                ...(task.state === "in_progress" ? { state: "pending" } : {}),
                claimed_by: null,
                claimed_at: null,
              });
              report.released_claims.push(entry);
            }
          }
        } else if (task.commit && HEX_SHA_RE.test(task.commit)) {
          if (!inHistory(task.commit)) report.missing_commits.push({ ...entry, commit: task.commit });
        } else if (task.state === "completed" || task.state === "closed") {
          const hit = named || (!dirty && touching()) || (stampHead && !dirty ? { sha: headSha } : null);
          if (hit) {
            updateTask(task, { commit: hit.sha, claimed_by: null, claimed_at: null });
            report.stamped_commits.push({ ...entry, commit: hit.sha });
          }
        }
      }
    }
  }

  #commitsSincePlan(git, spec, cache) {
    const plan = spec.plan_commit && HEX_SHA_RE.test(spec.plan_commit) ? spec.plan_commit : null;
    const range = plan && git.readGit(["merge-base", "--is-ancestor", plan, "HEAD"]).ok ? `${plan}..HEAD` : null;
    const cacheKey = range || "recent";
    if (cache.has(cacheKey)) return cache.get(cacheKey);
    const args = ["log", "--no-merges", `--max-count=${MAX_COMMITS}`, "--format=%h%x1f%s%x1e"];
    if (range) args.push(range);
    const res = git.readGit(args);
    const list = !res.ok
      ? []
      : res.stdout
          .split("\x1e")
          .map((row) => row.trim())
          .filter(Boolean)
          .map((row) => {
            const [sha, ...rest] = row.split("\x1f");
            return { sha: sha.trim(), message: rest.join("\x1f").trim(), files: null };
          })
          .filter((c) => c.sha);
    cache.set(cacheKey, list);
    return list;
  }

  #appendLog(bundleDir, report) {
    const logPath = path.join(bundleDir, "log.md");
    const dateStr = new Date().toISOString().slice(0, 10);
    const specsLabel = (report.specs_synced || []).join(", ") || "workspace";
    const summaryLine = `- ${dateStr} **sync**: ${specsLabel} (${WorkspaceSync.finalize({ ...report }).summary.replace(/^Sync:\s*/, "")})`;
    const cur = readTextSafe(logPath) || "# Bundle Log\n";
    if (cur.includes(summaryLine)) return;
    const next = cur.endsWith("\n") ? `${cur}${summaryLine}\n` : `${cur}\n${summaryLine}\n`;
    writeTextAtomic(logPath, next);
  }

  static #commitNamesTask(message, spec, task) {
    const escaped = [task.id, task.stem, task.short_id]
      .filter(Boolean)
      .map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    if (escaped.length === 0) return false;
    return new RegExp(`(?:^|[^A-Za-z0-9_:])(?:${escaped.join("|")})(?![A-Za-z0-9_])`).test(message);
  }

  static #claimIsFresh(claimedAt) {
    if (!claimedAt) return false;
    const ms = Date.parse(claimedAt);
    return Number.isFinite(ms) && Date.now() - ms < FRESH_CLAIM_MS;
  }
}
