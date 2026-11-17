/**
 * Cross-harness CLI and upward Frontier delegation runner.
 *
 * Replaces static model-name regex fallbacks with live `DynamicModelCatalog` +
 * `AdaptiveModelRouter` `(model, effort, fallback_chain)` resolution across
 * Claude Code, Codex CLI (`codex app-server` or isolated `CODEX_HOME` `codex exec`),
 * OpenCode V2, Cursor Agent, and Google Antigravity.
 */

import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";

import { readStudioLiveState, StudioStateStore, whichSync } from "../core/fs-io.mjs";
import { provisionIsolatedWorktree } from "../core/worktree.mjs";
import { DynamicModelCatalog } from "../models/inventory.mjs";
import { AdaptiveModelRouter } from "../models/routing.mjs";
import { CodexAppServerBridge, prepareIsolatedCodexHome } from "./codex.mjs";

const HARNESS_CATALOG = [
  { id: "claude", label: "Claude Code", binary: "claude" },
  { id: "codex", label: "Codex CLI", binary: "codex" },
  { id: "opencode", label: "OpenCode V2", binary: "opencode" },
  { id: "cursor-agent", label: "Cursor Agent", binary: "cursor-agent" },
  { id: "agy", label: "Google Antigravity", binary: "agy" },
];

export const VALID_EXECUTION_MODES = ["direct-workspace", "worktree-isolated", "read-only"];
const QUOTA_OR_EFFORT_ERROR_RE =
  /\b429\b|rate[_ -]?limit|overloaded_error|resource_exhausted|quota.*exceeded|capacity|unsupported.*effort/i;

export class CrossHarnessRunner {
  /**
   * @param {{ defaultWorkspace?: string, onEvent?: (event: any) => void, env?: NodeJS.ProcessEnv, stateStore?: StudioStateStore, codexBridge?: CodexAppServerBridge }} [options]
   */
  constructor(options = {}) {
    this.env = options.env || process.env;
    this.defaultWorkspace = path.resolve(options.defaultWorkspace || process.cwd());
    this.onEvent = options.onEvent || (() => {});
    this.stateStore = options.stateStore || new StudioStateStore({ env: this.env });
    this.modelCatalog = new DynamicModelCatalog({ env: this.env, projectRoot: this.defaultWorkspace, stateStore: this.stateStore });
    this.router = new AdaptiveModelRouter();
    this.codexBridge = options.codexBridge || new CodexAppServerBridge({ env: this.env, onEvent: (e) => this.#emit(e) });
    /** @type {Map<string, any>} */
    this.runs = new Map();
    /** @type {Map<string, import("node:child_process").ChildProcess>} */
    this.processes = new Map();
  }

  /**
   * @param {string} binaryName
   * @returns {string | null}
   */
  resolveBinary(binaryName) {
    const overrideDir = this.env.FLOW_HARNESS_BIN_DIR || process.env.FLOW_HARNESS_BIN_DIR;
    if (overrideDir) {
      const resolvedDir = path.resolve(overrideDir);
      const hit = whichSync(binaryName, { ...this.env, PATH: resolvedDir });
      if (hit) return hit;
    }
    return whichSync(binaryName, this.env);
  }

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
   * @param {string} workspaceRoot
   */
  checkActiveWriter(workspaceRoot) {
    const root = path.resolve(workspaceRoot || this.defaultWorkspace);
    if (fs.existsSync(path.join(root, ".git", "index.lock"))) {
      return { activeWriter: true, reason: "Git index lock (.git/index.lock) is currently held in this workspace." };
    }
    const state = readStudioLiveState(root, { agentsDir: path.join(root, ".agents"), env: this.env });
    if (state?.activeTurn && state?.updatedAt) {
      const ageMs = Date.now() - Date.parse(state.updatedAt);
      if (Number.isFinite(ageMs) && ageMs >= 0 && ageMs < 30000) {
        return {
          activeWriter: true,
          reason: `Active agent turn detected (${state.harness || "agent"} updated ${Math.round(ageMs / 1000)}s ago).`,
        };
      }
    }
    for (const run of this.runs.values()) {
      if (run.status === "running" && run.executionMode === "direct-workspace" && path.resolve(run.workspacePath) === root) {
        return { activeWriter: true, reason: `Cross-harness run ${run.id} (${run.harness}) is actively writing in this workspace.` };
      }
    }
    return { activeWriter: false, reason: null };
  }

  /**
   * Build CLI arguments for the selected harness, execution mode, model, and effort.
   *
   * @param {string} harness
   * @param {string} executionMode
   * @param {string} prompt
   * @param {string | null} [model]
   * @param {string | null} [effort]
   */
  buildHarnessArgs(harness, executionMode, prompt, model = null, effort = null) {
    const isReadOnly = executionMode === "read-only";
    const cleanEffort = effort && effort !== "default" ? String(effort) : null;
    if (harness === "claude") {
      const args = ["-p", prompt, "--output-format", "stream-json", "--verbose"];
      if (model) args.push("--model", model);
      if (cleanEffort) args.push("--effort", cleanEffort);
      if (isReadOnly) args.push("--allowedTools", "Read,Grep,Glob");
      return args;
    }
    if (harness === "codex") {
      const args = ["exec", "--json", "--sandbox", isReadOnly ? "read-only" : "workspace-write"];
      if (model) args.push("--model", model);
      if (cleanEffort) args.push("-c", `model_reasoning_effort=${JSON.stringify(cleanEffort)}`);
      args.push(prompt);
      return args;
    }
    if (harness === "opencode") {
      const args = ["run", "--format", "json"];
      if (model) args.push("--model", model);
      if (cleanEffort) args.push("--variant", cleanEffort);
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
   * Delegate deep reasoning (`planning`, `semantic_validation`, `spec_review`, `diagnosis`)
   * upward to the strongest healthy Thinking / Frontier `(model, effort)` candidate.
   *
   * @param {{
   *   workspacePath?: string,
   *   harness?: string | null,
   *   taskKind?: string,
   *   prompt: string,
   *   authorVendor?: string | null,
   *   useAppServer?: boolean,
   * }} params
   */
  async delegate(params) {
    const workspacePath = path.resolve(params.workspacePath || this.defaultWorkspace);
    const installed = this.detectHarnesses().filter((h) => h.installed);
    const chosenHarness =
      params.harness ||
      installed.find((h) => ["claude", "codex", "opencode", "cursor-agent", "agy"].includes(h.id))?.id;
    if (!chosenHarness) {
      throw new Error("No installed external harness CLI found for upward delegation.");
    }

    const catalogCandidates = await this.modelCatalog.discoverHarnessCatalog({ harness: chosenHarness });
    const selected = this.router.select(catalogCandidates, {
      taskKind: params.taskKind || "semantic_validation",
      risk: "high",
      authorVendor: params.authorVendor || null,
      requireVendorDiversity: params.taskKind === "adversarial",
    });

    if (chosenHarness === "codex" && params.useAppServer === true) {
      await this.codexBridge.connect({ cwd: workspacePath, isolatedHomeRoot: path.join(workspacePath, ".agents", "worktrees") });
      const thread = await this.codexBridge.startThread({
        cwd: workspacePath,
        model: selected.model || undefined,
        sandbox: "read-only",
        approvalPolicy: "never",
        ephemeral: true,
      });
      const turn = await this.codexBridge.runTurn({
        threadId: thread.id,
        prompt: params.prompt,
        model: selected.model,
        effort: selected.effort,
      });
      return {
        delegated: true,
        harness: "codex-app-server",
        model: selected.model,
        effort: selected.effort,
        degraded: selected.degraded,
        status: turn.status,
        outputText: turn.output,
      };
    }

    return this.dispatch({
      workspacePath,
      harness: chosenHarness,
      executionMode: "read-only",
      prompt: params.prompt,
      model: selected.model || undefined,
      effort: selected.effort || undefined,
      fallbackChain: selected.fallback_chain || [],
      wait: true,
    });
  }

  /**
   * Dispatch a prompt to an external harness CLI with ordered cooldown-aware fallback stepping.
   *
   * @param {Record<string, any>} params
   */
  async dispatch(params) {
    const workspacePath = path.resolve(params.workspacePath || this.defaultWorkspace);
    const harness = String(params.harness || "").trim().toLowerCase();
    const executionMode = params.executionMode || "direct-workspace";
    const prompt = String(params.prompt || "").trim();

    if (!VALID_EXECUTION_MODES.includes(executionMode)) {
      throw new Error(`Invalid executionMode '${executionMode}'.`);
    }
    if (!prompt) throw new Error("Dispatch prompt cannot be empty.");

    const entry = HARNESS_CATALOG.find((h) => h.id === harness);
    if (!entry) throw new Error(`Unknown harness '${harness}'.`);
    const binaryPath = this.resolveBinary(entry.binary);
    if (!binaryPath) throw new Error(`Harness CLI '${entry.binary}' is not installed on PATH.`);

    const writerGuard = this.checkActiveWriter(workspacePath);
    if (executionMode === "direct-workspace" && writerGuard.activeWriter && params.allowConcurrentWrite === false) {
      return { id: null, status: "advisory_blocked", harness, executionMode, workspacePath, advisory: writerGuard };
    }

    const runId = `run_${crypto.randomBytes(5).toString("hex")}`;
    const effectiveCwd =
      executionMode === "worktree-isolated"
        ? provisionIsolatedWorktree(workspacePath, harness, runId)
        : workspacePath;

    const candidates = await this.modelCatalog.discoverHarnessCatalog({ harness });
    const routed = this.router.select(candidates, {
      taskKind: params.taskKind || (executionMode === "read-only" ? "code_review" : "implementation"),
      risk: params.risk || "normal",
    });

    const requestedModel = params.model ?? null;
    const requestedEffort = params.effort ?? (requestedModel ? null : routed.effort);

    /** @type {Array<{ model: string | null, effort: string | null }>} */
    const attemptChain = [{ model: requestedModel, effort: requestedEffort }];
    if (params.fallbackModel) {
      attemptChain.push({ model: params.fallbackModel, effort: requestedEffort });
    }
    const orderedDynamic = Array.isArray(params.fallbackChain) && params.fallbackChain.length > 0
      ? params.fallbackChain
      : routed.fallback_chain || [];
    for (const step of orderedDynamic) {
      if (!step?.model || step.model === requestedModel) continue;
      if (!attemptChain.some((a) => a.model === step.model && a.effort === (step.effort || null))) {
        attemptChain.push({ model: step.model, effort: step.effort || null });
      }
    }

    const initialArgs = this.buildHarnessArgs(harness, executionMode, prompt, requestedModel, requestedEffort);
    const record = {
      id: runId,
      harness,
      label: entry.label,
      executionMode,
      workspacePath,
      effectiveCwd,
      prompt,
      requestedModel,
      requestedEffort,
      effectiveModel: requestedModel,
      effectiveEffort: requestedEffort,
      modelFallbackUsed: false,
      argv: [binaryPath, ...initialArgs],
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

    const spawnEnv = { ...this.env };
    if (harness === "codex" && executionMode !== "direct-workspace") {
      spawnEnv.CODEX_HOME = prepareIsolatedCodexHome(effectiveCwd, this.env);
    }

    const runAttempt = (modelForAttempt, effortForAttempt) =>
      new Promise((resolve) => {
        const args = this.buildHarnessArgs(harness, executionMode, prompt, modelForAttempt, effortForAttempt);
        record.effectiveModel = modelForAttempt;
        record.effectiveEffort = effortForAttempt;
        record.argv = [binaryPath, ...args];
        const isWinBatch = process.platform === "win32" && /\.(cmd|bat)$/i.test(binaryPath);
        const cmd = isWinBatch ? process.env.ComSpec || "cmd.exe" : binaryPath;
        const finalArgs = isWinBatch ? ["/d", "/c", binaryPath, ...args] : args;
        const child = spawn(cmd, finalArgs, { cwd: effectiveCwd, env: spawnEnv, stdio: ["ignore", "pipe", "pipe"] });
        this.processes.set(runId, child);
        let stderrCombined = "";

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
          const chunk = parsed?.text || parsed?.message?.content?.[0]?.text || parsed?.result || trimmed;
          record.outputText = `${record.outputText}${record.outputText ? "\n" : ""}${chunk}`.slice(-32000);
          this.#emit({ type: "harness.output", runId, event: parsed });
        });
        const rlErr = readline.createInterface({ input: child.stderr });
        rlErr.on("line", (line) => {
          if (!line.trim()) return;
          stderrCombined = `${stderrCombined}\n${line}`.slice(-8000);
          record.events.push({ type: "stderr", text: line });
        });
        child.on("close", (code) => {
          this.processes.delete(runId);
          resolve({ code: code ?? 0, stderrCombined, spawnError: null });
        });
        child.on("error", (err) => {
          this.processes.delete(runId);
          resolve({ code: 1, stderrCombined, spawnError: err });
        });
      });

    const completion = (async () => {
      let attempt = await runAttempt(attemptChain[0].model, attemptChain[0].effort);
      for (let idx = 1; idx < attemptChain.length && idx < 4; idx += 1) {
        if (attempt.code === 0 || record.status === "cancelled") break;
        const errText = `${attempt.stderrCombined}\n${record.outputText}`;
        if (!QUOTA_OR_EFFORT_ERROR_RE.test(errText)) break;
        if (record.effectiveModel) {
          this.stateStore.recordCooldown({
            harness,
            model: record.effectiveModel,
            effort: record.effectiveEffort || "default",
            reason: "quota_or_effort_error",
          });
        }
        const nextCandidate = attemptChain[idx];
        record.modelFallbackUsed = true;
        const evt = { type: "model.fallback", from: record.effectiveModel, to: nextCandidate.model, effort: nextCandidate.effort };
        record.events.push(evt);
        this.#emit({ type: "harness.output", runId, event: evt });
        record.outputText = "";
        attempt = await runAttempt(nextCandidate.model, nextCandidate.effort);
      }

      if (attempt.spawnError) {
        record.exitCode = 1;
        record.status = "failed";
        record.outputText = attempt.spawnError.message;
      } else {
        record.exitCode = attempt.code;
        record.status = record.status === "cancelled" ? "cancelled" : attempt.code === 0 ? "completed" : "failed";
      }
      record.completedAt = new Date().toISOString();
      this.#emit({ type: "harness.completed", run: this.#summarize(record) });
      return this.#summarize(record);
    })();

    if (params.wait) return await completion;
    return this.#summarize(record);
  }

  listRuns() {
    return Array.from(this.runs.values()).map((r) => this.#summarize(r)).reverse().slice(0, 40);
  }

  getRun(runId) {
    const r = this.runs.get(runId);
    return r ? { ...this.#summarize(r), events: r.events } : null;
  }

  cancelRun(runId) {
    const r = this.runs.get(runId);
    if (!r) return null;
    r.status = "cancelled";
    const proc = this.processes.get(runId);
    if (proc) proc.kill("SIGTERM");
    return this.#summarize(r);
  }

  #summarize(record) {
    return {
      id: record.id,
      harness: record.harness,
      label: record.label,
      executionMode: record.executionMode,
      workspacePath: record.workspacePath,
      effectiveCwd: record.effectiveCwd,
      prompt: record.prompt,
      requestedModel: record.requestedModel ?? null,
      requestedEffort: record.requestedEffort ?? null,
      effectiveModel: record.effectiveModel ?? null,
      effectiveEffort: record.effectiveEffort ?? null,
      modelFallbackUsed: Boolean(record.modelFallbackUsed),
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

  #emit(event) {
    try {
      this.onEvent(event);
    } catch {
      // Ignore subscriber errors.
    }
  }
}
