/**
 * Live agent, subagent lease, transcript tail, worktree, and Attention Drawer monitor
 * across Antigravity, Codex CLI threads, Claude Code sessions, and Flow workflows.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  isClosedState,
  parseClaimIdentity,
  readJsonSafe,
  readStudioLiveState,
  runtimeBaseDir,
  workspaceRuntimeId,
} from "./core/fs-io.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";

const LEASE_TTL_SECONDS = 900;

/**
 * Locate Antigravity appData root (`<appData>/brain/`).
 *
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string}
 */
export function locateAntigravityAppData(env = process.env) {
  for (const key of ["ANTIGRAVITY_APP_DATA_DIR", "FLOW_APP_DATA_DIR"]) {
    const raw = String(env[key] || "").trim();
    if (raw) return path.resolve(raw);
  }
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const geminiDir = path.join(home, ".gemini");
  try {
    for (const ent of fs.readdirSync(geminiDir, { withFileTypes: true })) {
      if (ent.isDirectory() && fs.existsSync(path.join(geminiDir, ent.name, "brain"))) {
        return path.join(geminiDir, ent.name);
      }
    }
  } catch {
    // Fallback below.
  }
  return path.join(geminiDir, "agy");
}

/**
 * Monitor live worker leases, active turns, open review requests, blocked specs,
 * and cross-harness sessions to surface the Studio Attention Drawer (`"X needs you"`).
 */
export class ActivityMonitor {
  /**
   * @param {{ env?: NodeJS.ProcessEnv, antigravityBridge?: any, codexBridge?: any, cliRunner?: any }} [options]
   */
  constructor({ env = process.env, antigravityBridge = null, codexBridge = null, cliRunner = null } = {}) {
    this.env = env;
    this.antigravityBridge = antigravityBridge;
    this.codexBridge = codexBridge;
    this.cliRunner = cliRunner;
  }

  /**
   * Gather live sessions, subagent leases, git worktrees, and actionable attention items for `workspaceRoot`.
   *
   * @param {string} workspaceRoot
   */
  async snapshot(workspaceRoot) {
    const root = path.resolve(workspaceRoot);
    const engine = new SpecEngine({ workspacePath: root, env: this.env });
    const liveState = readStudioLiveState(engine.effectiveRoot, {
      agentsDir: path.join(engine.effectiveRoot, ".agents"),
      env: this.env,
    });
    const leases = this.#readActiveLeases(engine.effectiveRoot);
    const worktrees = this.#listGitWorktrees(root);
    const specs = engine.listSpecs({ includeArchived: false });

    const attention = [];
    for (const spec of specs) {
      if (spec.planning_quality === "degraded") {
        attention.push({
          id: `degraded:${spec.flow_id}`,
          kind: "degraded_plan",
          severity: "warning",
          flowId: spec.flow_id,
          title: `${spec.title} planned on fallback model`,
          actionLabel: "Re-plan on strongest model",
          command: `/flow:revise ${spec.flow_id}`,
        });
      }
      const comments = engine.feedback.listForFlow(spec.flow_id);
      const openChanges = comments.filter((c) => c.state === "open" && c.commentKind === "change_request");
      const openNotes = comments.filter((c) => c.state === "open" && c.commentKind !== "approval");
      if (openChanges.length > 0 || openNotes.length > 0) {
        attention.push({
          id: `feedback:${spec.flow_id}`,
          kind: openChanges.length > 0 ? "change_request" : "review_feedback",
          severity: openChanges.length > 0 ? "warning" : "info",
          flowId: spec.flow_id,
          count: openNotes.length,
          title: `${openNotes.length} open review note(s) on ${spec.flow_id}`,
          actionLabel: "Open Revise Prompt",
          command: `/flow:revise ${spec.flow_id}`,
        });
      }

      const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
      for (const task of allTasks) {
        if (task.state === "blocked") {
          attention.push({
            id: `blocked:${task.id}`,
            kind: "blocked_task",
            severity: "error",
            flowId: spec.flow_id,
            taskId: task.id,
            title: `Blocked task: ${task.id} — ${task.title}`,
            actionLabel: "Revise Blocked Task",
            command: `/flow:revise ${spec.flow_id}`,
          });
        }
        if (task.claimed_by && !isClosedState(task.state)) {
          const idInfo = parseClaimIdentity(task.claimed_by);
          attention.push({
            id: `claim:${task.id}`,
            kind: "claimed_task",
            severity: "info",
            flowId: spec.flow_id,
            taskId: task.id,
            claimedBy: task.claimed_by,
            harness: idInfo?.harness || "unknown",
            title: `Active claim ${task.id} (${task.claimed_by})`,
            actionLabel: "Inspect Spec",
            command: `/flow:status ${spec.flow_id}`,
          });
        }
      }
    }

    const runs = this.cliRunner ? this.cliRunner.listRuns() : [];
    const codexThreads = this.codexBridge ? this.codexBridge.listThreads() : [];
    let trajectories = [];
    if (this.antigravityBridge?.available) {
      const tr = await this.antigravityBridge.listTrajectories(root);
      trajectories = tr?.trajectories || [];
    }

    return {
      generatedAt: new Date().toISOString(),
      workspaceRoot: root,
      liveState,
      leases,
      worktrees,
      runs,
      codexThreads,
      trajectories,
      attention,
      needsAttentionCount: attention.filter((a) => a.severity === "error" || a.severity === "warning").length,
    };
  }

  #readActiveLeases(effectiveRoot) {
    const leaseDir = path.join(runtimeBaseDir(this.env), workspaceRuntimeId(effectiveRoot), "subagents");
    if (!fs.existsSync(leaseDir)) return [];
    const nowSec = Math.floor(Date.now() / 1000);
    const active = [];
    for (const name of fs.readdirSync(leaseDir).sort()) {
      if (!name.endsWith(".lease")) continue;
      try {
        const lines = fs.readFileSync(path.join(leaseDir, name), "utf8").split(/\r?\n/);
        const epoch = Number(lines[0]);
        if (!Number.isFinite(epoch) || nowSec - epoch > LEASE_TTL_SECONDS) continue;
        const meta = lines[1] ? JSON.parse(lines[1]) : {};
        active.push({ ...meta, epoch, ageSeconds: nowSec - epoch });
      } catch {
        // Ignore malformed lease files.
      }
    }
    return active;
  }

  #listGitWorktrees(root) {
    try {
      const raw = execFileSync("git", ["-C", root, "worktree", "list", "--porcelain"], {
        encoding: "utf8",
        timeout: 2000,
        stdio: ["ignore", "pipe", "ignore"],
      });
      const out = [];
      let current = {};
      for (const line of raw.split(/\r?\n/)) {
        if (!line.trim()) {
          if (current.worktree) out.push(current);
          current = {};
          continue;
        }
        const [k, ...rest] = line.split(" ");
        current[k] = rest.join(" ");
      }
      if (current.worktree) out.push(current);
      return out;
    } catch {
      return [];
    }
  }
}
