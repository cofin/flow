/**
 * Cross-harness CLI runner with user-modifiable Execution Modes:
 *   - `direct-workspace`: Run directly in the active repository root (default for sequential work).
 *   - `worktree-isolated`: Provision an isolated `.agents/worktrees/<harness>-<id>` checkout.
 *   - `read-only`: Enforce read-only tool/sandbox flags for safe concurrent reviews and research.
 */

import { spawn, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";

import { whichSync } from "./python-runner.mjs";

const HARNESS_CATALOG = [
  { id: "claude", label: "Claude Code", binary: "claude" },
  { id: "codex", label: "Codex CLI", binary: "codex" },
  { id: "opencode", label: "OpenCode V2", binary: "opencode" },
  { id: "cursor-agent", label: "Cursor Agent", binary: "cursor-agent" },
  { id: "agy", label: "Google Antigravity", binary: "agy" },
];

export const VALID_EXECUTION_MODES = ["direct-workspace", "worktree-isolated", "read-only"];

export class CrossHarnessRunner {
  /**
   * @param {{ defaultWorkspace?: string, onEvent?: (event: any) => void }} [options]
   */
  constructor(options = {}) {
    this.defaultWorkspace = path.resolve(options.defaultWorkspace || process.cwd());
    this.onEvent = options.onEvent || (() => {});
    /** @type {Map<string, any>} */
    this.runs = new Map();
    /** @type {Map<string, import("node:child_process").ChildProcess>} */
    this.processes = new Map();
  }

  /**
   * Resolve harness binary path considering `FLOW_HARNESS_BIN_DIR` override and `PATH`.
   *
   * @param {string} binaryName
   * @returns {string | null}
   */
  resolveBinary(binaryName) {
    const overrideDir = process.env.FLOW_HARNESS_BIN_DIR;
    if (overrideDir) {
      const candidate = path.join(path.resolve(overrideDir), binaryName);
      if (fs.existsSync(candidate)) return candidate;
    }
    return whichSync(binaryName);
  }

  /**
   * Detect installed external agent CLIs on the host workstation.
   */
  detectHarnesses() {
    return HARNESS_CATALOG.map((item) => {
      const binPath = this.resolveBinary(item.binary);
      return {
        id: item.id,
        label: item.label,
        binary: item.binary,
        installed: Boolean(binPath),
        path: binPath,
        supportedModes: VALID_EXECUTION_MODES,
      };
    });
  }

  /**
   * Inspect `.git/index.lock` and `.agents/studio-live-state.json` for concurrent writers.
   *
   * @param {string} workspaceRoot
   */
  checkActiveWriter(workspaceRoot) {
    const root = path.resolve(workspaceRoot || this.defaultWorkspace);
    const gitIndexLock = path.join(root, ".git", "index.lock");
    if (fs.existsSync(gitIndexLock)) {
      return {
        activeWriter: true,
        reason: "Git index lock (.git/index.lock) is currently held in this workspace.",
      };
    }

    const liveStatePath = path.join(root, ".agents", "studio-live-state.json");
    if (fs.existsSync(liveStatePath)) {
      try {
        const state = JSON.parse(fs.readFileSync(liveStatePath, "utf8"));
        if (state?.activeTurn && state?.updatedAt) {
          const ageMs = Date.now() - Date.parse(state.updatedAt);
          if (Number.isFinite(ageMs) && ageMs >= 0 && ageMs < 30000) {
            return {
              activeWriter: true,
              reason: `Active agent turn detected (${state.harness || "agent"} updated ${Math.round(ageMs / 1000)}s ago).`,
            };
          }
        }
      } catch {
        // Ignore malformed telemetry file.
      }
    }

    for (const run of this.runs.values()) {
      if (
        run.status === "running" &&
        run.executionMode === "direct-workspace" &&
        path.resolve(run.workspacePath) === root
      ) {
        return {
          activeWriter: true,
          reason: `Cross-harness run ${run.id} (${run.harness}) is actively writing in this workspace.`,
        };
      }
    }

    return { activeWriter: false, reason: null };
  }

  /**
   * Build CLI arguments for the selected harness and execution mode.
   *
   * @param {string} harness
   * @param {string} executionMode
   * @param {string} prompt
   * @param {string | null} [model]
   * @returns {string[]}
   */
  buildHarnessArgs(harness, executionMode, prompt, model = null) {
    const isReadOnly = executionMode === "read-only";
    if (harness === "claude") {
      const args = ["-p", prompt, "--output-format", "stream-json", "--verbose"];
      if (model) args.push("--model", model);
      if (isReadOnly) {
        args.push("--allowedTools", "Read,Grep,Glob");
      }
      return args;
    }
    if (harness === "codex") {
      const sandboxMode = isReadOnly ? "read-only" : "workspace-write";
      const args = ["exec", "--json", "--sandbox", sandboxMode];
      if (model) args.push("--model", model);
      args.push(prompt);
      return args;
    }
    if (harness === "opencode") {
      const args = ["run", "--format", "json"];
      if (model) args.push("--model", model);
      if (isReadOnly) args.push("--agent", "plan");
      args.push(prompt);
      return args;
    }
    if (harness === "cursor-agent") {
      const args = ["-p", "--output-format", "stream-json"];
      if (model) args.push("--model", model);
      if (!isReadOnly) args.push("--force");
      args.push(prompt);
      return args;
    }
    if (harness === "agy") {
      const args = ["chat"];
      if (isReadOnly) args.push("--mode", "read-only");
      args.push(prompt);
      return args;
    }
    throw new Error(`Unsupported target harness: ${harness}`);
  }

  /**
   * Dispatch a prompt to an external harness CLI.
   *
   * @param {{
   *   workspacePath?: string,
   *   harness: string,
   *   executionMode?: "direct-workspace" | "worktree-isolated" | "read-only",
   *   prompt: string,
   *   model?: string,
   *   allowConcurrentWrite?: boolean,
   *   wait?: boolean
   * }} params
   */
  async dispatch(params) {
    const workspacePath = path.resolve(params.workspacePath || this.defaultWorkspace);
    const harness = String(params.harness || "").trim().toLowerCase();
    const executionMode = params.executionMode || "direct-workspace";
    const prompt = String(params.prompt || "").trim();

    if (!VALID_EXECUTION_MODES.includes(executionMode)) {
      throw new Error(`Invalid executionMode '${executionMode}'. Expected one of: ${VALID_EXECUTION_MODES.join(", ")}`);
    }
    if (!prompt) {
      throw new Error("Dispatch prompt cannot be empty.");
    }

    const catalogEntry = HARNESS_CATALOG.find((h) => h.id === harness);
    if (!catalogEntry) {
      throw new Error(`Unknown harness '${harness}'.`);
    }
    const binaryPath = this.resolveBinary(catalogEntry.binary);
    if (!binaryPath) {
      throw new Error(`Harness CLI '${catalogEntry.binary}' is not installed on PATH.`);
    }

    const writerGuard = this.checkActiveWriter(workspacePath);
    if (
      executionMode === "direct-workspace" &&
      writerGuard.activeWriter &&
      params.allowConcurrentWrite === false
    ) {
      return {
        id: null,
        status: "advisory_blocked",
        harness,
        executionMode,
        workspacePath,
        advisory: writerGuard,
      };
    }

    const runId = `run_${crypto.randomBytes(5).toString("hex")}`;
    let effectiveCwd = workspacePath;
    if (executionMode === "worktree-isolated") {
      effectiveCwd = this.#provisionWorktree(workspacePath, harness, runId);
    }

    const cliArgs = this.buildHarnessArgs(harness, executionMode, prompt, params.model || null);
    const record = {
      id: runId,
      harness,
      label: catalogEntry.label,
      executionMode,
      workspacePath,
      effectiveCwd,
      prompt,
      argv: [binaryPath, ...cliArgs],
      advisory: writerGuard,
      status: "running",
      startedAt: new Date().toISOString(),
      completedAt: null,
      exitCode: null,
      events: [],
      outputText: "",
    };
    this.runs.set(runId, record);
    this.#emit({ type: "harness.started", run: this.#summarize(record) });

    const completion = new Promise((resolve) => {
      const child = spawn(binaryPath, cliArgs, {
        cwd: effectiveCwd,
        env: { ...process.env },
        stdio: ["ignore", "pipe", "pipe"],
      });
      this.processes.set(runId, child);

      const rlOut = readline.createInterface({ input: child.stdout });
      rlOut.on("line", (line) => {
        const trimmed = line.trim();
        if (!trimmed) return;
        let parsed = null;
        try {
          parsed = JSON.parse(trimmed);
        } catch {
          parsed = { type: "raw", text: trimmed };
        }
        record.events.push(parsed);
        const textChunk =
          parsed?.text ||
          parsed?.message?.content?.[0]?.text ||
          parsed?.result ||
          trimmed;
        record.outputText = `${record.outputText}${record.outputText ? "\n" : ""}${textChunk}`.slice(-32000);
        this.#emit({ type: "harness.output", runId, event: parsed });
      });

      const rlErr = readline.createInterface({ input: child.stderr });
      rlErr.on("line", (line) => {
        if (!line.trim()) return;
        record.events.push({ type: "stderr", text: line });
      });

      child.on("close", (code) => {
        this.processes.delete(runId);
        record.exitCode = code ?? 0;
        record.status = record.status === "cancelled" ? "cancelled" : code === 0 ? "completed" : "failed";
        record.completedAt = new Date().toISOString();
        this.#emit({ type: "harness.completed", run: this.#summarize(record) });
        resolve(this.#summarize(record));
      });

      child.on("error", (err) => {
        this.processes.delete(runId);
        record.status = "failed";
        record.outputText = err.message;
        record.completedAt = new Date().toISOString();
        this.#emit({ type: "harness.completed", run: this.#summarize(record) });
        resolve(this.#summarize(record));
      });
    });

    if (params.wait) {
      return await completion;
    }
    return this.#summarize(record);
  }

  listRuns() {
    return Array.from(this.runs.values())
      .map((r) => this.#summarize(r))
      .reverse()
      .slice(0, 40);
  }

  /**
   * @param {string} runId
   */
  getRun(runId) {
    const r = this.runs.get(runId);
    return r ? { ...this.#summarize(r), events: r.events } : null;
  }

  /**
   * @param {string} runId
   */
  cancelRun(runId) {
    const r = this.runs.get(runId);
    if (!r) return null;
    const proc = this.processes.get(runId);
    r.status = "cancelled";
    if (proc) {
      proc.kill("SIGTERM");
    }
    return this.#summarize(r);
  }

  /**
   * Provision a detached Git worktree under `.agents/worktrees/<harness>-<runId>`.
   *
   * @param {string} workspacePath
   * @param {string} harness
   * @param {string} runId
   */
  #provisionWorktree(workspacePath, harness, runId) {
    const wtRoot = path.join(workspacePath, ".agents", "worktrees");
    fs.mkdirSync(wtRoot, { recursive: true });
    const targetDir = path.join(wtRoot, `${harness}-${runId}`);
    const res = spawnSync("git", ["worktree", "add", "--detach", targetDir, "HEAD"], {
      cwd: workspacePath,
      encoding: "utf8",
    });
    if (res.status !== 0) {
      throw new Error(`Failed to create isolated git worktree: ${res.stderr || res.stdout}`);
    }
    return targetDir;
  }

  /**
   * @param {any} record
   */
  #summarize(record) {
    return {
      id: record.id,
      harness: record.harness,
      label: record.label,
      executionMode: record.executionMode,
      workspacePath: record.workspacePath,
      effectiveCwd: record.effectiveCwd,
      prompt: record.prompt,
      argv: record.argv,
      advisory: record.advisory,
      status: record.status,
      startedAt: record.startedAt,
      completedAt: record.completedAt,
      exitCode: record.exitCode,
      outputText: record.outputText,
      eventCount: record.events.length,
    };
  }

  /**
   * @param {any} event
   */
  #emit(event) {
    try {
      this.onEvent(event);
    } catch {
      // Ignore subscriber callback errors.
    }
  }
}
