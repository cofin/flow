/**
 * Stateful JSON-RPC 2.0 client for `codex app-server`.
 *
 * Gives Codex CLI sidecar-grade orchestration matching Antigravity's bridge:
 *   - `model/list` live model and supported reasoning-effort discovery
 *   - Isolated `CODEX_HOME` worker seeding (`auth.json` + `models_cache.json`)
 *   - `thread/start`, `thread/fork`, `turn/start`, `turn/steer`, and `turn/interrupt`
 *   - Live streaming notification tracking (`turn/started`, `item/*`, `turn/completed`)
 */

import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";

import { safeLinkPath } from "../core/worktree.mjs";
import { whichSync } from "../core/fs-io.mjs";

/**
 * Create an isolated `CODEX_HOME` directory for a concurrent Codex process so SQLite
 * history and `models_cache.json` never lock across parallel runs.
 *
 * @param {string} baseRoot
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string}
 */
export function prepareIsolatedCodexHome(baseRoot, env = process.env) {
  const sourceHome = env.CODEX_HOME ? path.resolve(env.CODEX_HOME) : path.join(os.homedir(), ".codex");
  const isoDir = path.join(baseRoot, `.codex-home-${process.pid}-${crypto.randomBytes(3).toString("hex")}`);
  fs.mkdirSync(isoDir, { recursive: true });
  for (const name of ["auth.json", "config.toml"]) {
    safeLinkPath(path.join(sourceHome, name), path.join(isoDir, name));
  }
  const cacheSrc = path.join(sourceHome, "models_cache.json");
  if (fs.existsSync(cacheSrc)) {
    try {
      fs.copyFileSync(cacheSrc, path.join(isoDir, "models_cache.json"));
    } catch {
      // Ignore optional cache copy failure.
    }
  }
  return isoDir;
}

export class CodexAppServerBridge {
  /**
   * @param {{ codexBin?: string | null, env?: NodeJS.ProcessEnv, onEvent?: (evt: any) => void }} [options]
   */
  constructor({ codexBin = null, env = process.env, onEvent = null } = {}) {
    this.env = env;
    this.codexBin = codexBin || null;
    this.onEvent = typeof onEvent === "function" ? onEvent : () => {};
    this.child = null;
    this.nextId = 1;
    /** @type {Map<number, { resolve: Function, reject: Function, timer: NodeJS.Timeout }>} */
    this.pending = new Map();
    /** @type {Map<string, any>} */
    this.threads = new Map();
    this.initialized = false;
  }

  resolveBinary() {
    if (this.codexBin) return this.codexBin;
    const override = this.env.FLOW_HARNESS_BIN_DIR;
    if (override) {
      const hit = whichSync("codex", { ...this.env, PATH: override });
      if (hit) return hit;
    }
    return whichSync("codex", this.env);
  }

  /**
   * Spawn and initialize `codex app-server` over stdio if not already running.
   *
   * @param {{ cwd?: string, isolatedHomeRoot?: string }} [options]
   */
  async connect({ cwd = process.cwd(), isolatedHomeRoot = null } = {}) {
    if (this.child && this.initialized) return true;
    const bin = this.resolveBinary();
    if (!bin) throw new Error("codex CLI binary not found on PATH.");

    const env = { ...this.env };
    if (isolatedHomeRoot) {
      env.CODEX_HOME = prepareIsolatedCodexHome(isolatedHomeRoot, this.env);
    }

    const child = spawn(bin, ["app-server"], {
      cwd: path.resolve(cwd),
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    const rl = readline.createInterface({ input: child.stdout });
    rl.on("line", (line) => this.#handleStdoutLine(line));
    child.stderr.on("data", (chunk) => {
      const text = chunk.toString("utf8").trim();
      if (text) this.onEvent({ type: "codex.stderr", text });
    });
    child.on("exit", () => {
      this.child = null;
      this.initialized = false;
      for (const [, req] of this.pending) {
        clearTimeout(req.timer);
        req.reject(new Error("codex app-server exited"));
      }
      this.pending.clear();
      for (const [, state] of this.threads) {
        if (typeof state._rejectWait === "function") {
          const abort = state._rejectWait;
          delete state._resolveWait;
          delete state._rejectWait;
          abort(new Error("codex app-server exited"));
        }
      }
    });

    this.child = child;
    await this.request("initialize", {
      clientInfo: { name: "flow-studio", title: "Flow Studio", version: "0.31.0" },
    });
    this.notify("initialized", {});
    this.initialized = true;
    return true;
  }

  /**
   * Query live available Codex models and supported reasoning efforts.
   */
  async listModels() {
    const res = await this.request("model/list", {});
    return Array.isArray(res?.data) ? res.data : Array.isArray(res?.models) ? res.models : [];
  }

  /**
   * Start a persistent or ephemeral thread with explicit model & sandbox settings.
   *
   * @param {Record<string, any>} params
   */
  async startThread(params = {}) {
    const res = await this.request("thread/start", params);
    const thread = res?.thread || res;
    if (thread?.id) {
      this.threads.set(thread.id, {
        id: thread.id,
        cwd: params.cwd || null,
        model: params.model || null,
        status: "idle",
        lastOutput: "",
        updatedAt: new Date().toISOString(),
      });
    }
    return thread;
  }

  /**
   * Fork an existing Codex thread.
   *
   * @param {string} threadId
   */
  async forkThread(threadId) {
    return this.request("thread/fork", { threadId });
  }

  /**
   * Run a turn inside `threadId` and resolve when `turn/completed` arrives.
   *
   * @param {{ threadId: string, prompt: string, model?: string | null, effort?: string | null, timeoutMs?: number }} params
   */
  async runTurn({ threadId, prompt, model = null, effort = null, timeoutMs = 120000 }) {
    const turnParams = {
      threadId,
      input: [{ type: "text", text: prompt }],
      ...(model ? { model } : {}),
      ...(effort && effort !== "default" ? { effort } : {}),
    };
    const tState = this.threads.get(threadId) || { id: threadId, lastOutput: "" };
    tState.status = "running";
    tState.lastOutput = "";
    tState._turnId = null;
    this.threads.set(threadId, tState);

    /** @type {(payload: any) => void} */
    let resolveCompletion = () => {};
    /** @type {(err: Error) => void} */
    let rejectCompletion = () => {};
    const completionPromise = new Promise((resolve, reject) => {
      resolveCompletion = resolve;
      rejectCompletion = reject;
    });
    completionPromise.catch(() => {});

    const timer = setTimeout(() => {
      delete tState._resolveWait;
      delete tState._rejectWait;
      rejectCompletion(new Error(`Codex turn timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    tState._resolveWait = (payload) => {
      clearTimeout(timer);
      delete tState._resolveWait;
      delete tState._rejectWait;
      resolveCompletion(payload);
    };
    tState._rejectWait = (err) => {
      clearTimeout(timer);
      delete tState._resolveWait;
      delete tState._rejectWait;
      rejectCompletion(err);
    };

    try {
      const startRes = await this.request("turn/start", turnParams, timeoutMs);
      const turnId = startRes?.turn?.id || startRes?.turnId || null;
      if (turnId) tState._turnId = turnId;
      if (startRes?.turn?.status === "completed") {
        tState.status = "completed";
        tState._resolveWait?.({ threadId, turnId, output: tState.lastOutput, status: "completed" });
      }
      return await completionPromise;
    } catch (err) {
      clearTimeout(timer);
      delete tState._resolveWait;
      delete tState._rejectWait;
      throw err;
    }
  }

  async steerTurn(threadId, expectedTurnId, prompt) {
    return this.request("turn/steer", {
      threadId,
      expectedTurnId,
      input: [{ type: "text", text: prompt }],
    });
  }

  async interruptTurn(threadId, turnId) {
    return this.request("turn/interrupt", { threadId, turnId });
  }

  listThreads() {
    return Array.from(this.threads.values());
  }

  request(method, params = {}, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      if (!this.child || !this.child.stdin?.writable) {
        reject(new Error("codex app-server stdin is not writable"));
        return;
      }
      const id = this.nextId++;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`codex app-server request '${method}' timed out`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    });
  }

  notify(method, params = {}) {
    if (!this.child || !this.child.stdin?.writable) return;
    this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`);
  }

  close() {
    if (this.child) {
      try {
        this.child.stdin?.end();
        this.child.kill("SIGTERM");
      } catch {
        // Ignore shutdown errors.
      }
      this.child = null;
      this.initialized = false;
    }
  }

  #handleStdoutLine(rawLine) {
    const trimmed = String(rawLine || "").trim();
    if (!trimmed) return;
    let msg;
    try {
      msg = JSON.parse(trimmed);
    } catch {
      return;
    }

    if (msg.id !== undefined && msg.id !== null) {
      const pending = this.pending.get(msg.id);
      if (!pending) return;
      this.pending.delete(msg.id);
      clearTimeout(pending.timer);
      if (msg.error) pending.reject(new Error(msg.error.message || "codex app-server error"));
      else pending.resolve(msg.result);
      return;
    }

    const method = String(msg.method || "");
    const p = msg.params || {};
    const tid = p.threadId || p.thread_id || null;
    if (tid) {
      const state = this.threads.get(tid) || { id: tid, lastOutput: "" };
      state.updatedAt = new Date().toISOString();
      if (method === "item/agentMessage/delta" && typeof p.delta === "string") {
        state.lastOutput += p.delta;
      } else if (method === "item/completed" && p.item?.text) {
        state.lastOutput += (state.lastOutput ? "\n" : "") + p.item.text;
      } else if (method === "turn/completed") {
        state.status = p.turn?.status || "completed";
        if (typeof state._resolveWait === "function") {
          const done = state._resolveWait;
          delete state._resolveWait;
          done({ threadId: tid, turnId: state._turnId || p.turn?.id || null, status: state.status, output: state.lastOutput });
        }
      }
      this.threads.set(tid, state);
    }
    this.onEvent({ type: `codex.${method || "notification"}`, params: p });
  }
}
