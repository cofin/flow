/**
 * Local Agent-to-Agent (A2A v1) JSON-RPC 2.0 + Agent Card facade over CrossHarnessRunner.
 *
 * Exposes `GET /.well-known/agent-card.json` and `POST /a2a` (`message/send`,
 * `tasks/get`, `tasks/cancel`) on loopback so external A2A-capable orchestrators
 * can delegate Flow specs, reviews, and tasks across installed CLI harnesses.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_PACKAGE_JSON = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "package.json");

function readPluginVersion() {
  try {
    const parsed = JSON.parse(fs.readFileSync(PLUGIN_PACKAGE_JSON, "utf8"));
    return typeof parsed.version === "string" && parsed.version ? parsed.version : "0.28.0";
  } catch {
    return "0.28.0";
  }
}

export class A2AFacade {
  /**
   * @param {import("./harness-runner.mjs").CrossHarnessRunner} runner
   */
  constructor(runner) {
    this.runner = runner;
  }

  /**
   * Build the A2A v1 Agent Card discovery payload.
   *
   * @param {string} baseUrl
   */
  buildAgentCard(baseUrl) {
    const installed = this.runner.detectHarnesses().filter((h) => h.installed);
    return {
      protocolVersion: "1.0",
      name: "Flow Studio Cross-Harness Bridge",
      description:
        "Local multi-harness Spec-Driven Development coordinator routing Flow planning, execution, and zero-context reviews across installed agent CLIs.",
      url: `${String(baseUrl || "").replace(/\/+$/, "")}/a2a`,
      version: readPluginVersion(),
      capabilities: {
        streaming: true,
        pushNotifications: false,
        stateTransitionHistory: true,
      },
      defaultInputModes: ["text/plain", "application/json"],
      defaultOutputModes: ["text/plain", "application/json"],
      skills: [
        {
          id: "flow-plan",
          name: "Flow Spec Planning",
          description: "Author or revise OKF v0.2 specs and vertical-slice task plans.",
          tags: ["spec", "planning", "okf"],
        },
        {
          id: "flow-implement",
          name: "Flow Vertical-Slice Execution",
          description: "Execute approved chapter tasks in direct-workspace or worktree-isolated mode.",
          tags: ["tdd", "implementation"],
        },
        {
          id: "flow-review",
          name: "Flow Zero-Context Review",
          description: "Run isolated read-only spec conformance and quality reviews.",
          tags: ["review", "quality"],
        },
      ],
      metadata: {
        installedHarnesses: installed.map((h) => h.id),
        executionModes: ["direct-workspace", "worktree-isolated", "read-only"],
      },
    };
  }

  /**
   * Handle a JSON-RPC 2.0 request sent to `POST /a2a`.
   *
   * @param {Record<string, any>} payload
   */
  async handleJsonRpc(payload) {
    const id = payload?.id ?? null;
    const method = String(payload?.method || "");
    const params = payload?.params || {};

    try {
      if (method === "message/send") {
        const text = extractMessageText(params.message);
        const meta = params.metadata || {};
        const preferredHarness = meta.harness || this.#selectDefaultHarness();
        const executionMode = meta.executionMode || "direct-workspace";
        const wait = meta.wait !== false;

        const run = await this.runner.dispatch({
          workspacePath: meta.workspacePath,
          harness: preferredHarness,
          executionMode,
          prompt: text,
          model: meta.model,
          allowConcurrentWrite: meta.allowConcurrentWrite !== false,
          wait,
        });

        return {
          jsonrpc: "2.0",
          id,
          result: this.#toA2ATask(run),
        };
      }

      if (method === "tasks/get") {
        const taskId = String(params.id || params.taskId || "");
        const run = this.runner.getRun(taskId);
        if (!run) {
          return this.#rpcError(id, -32001, `Task not found: ${taskId}`);
        }
        return { jsonrpc: "2.0", id, result: this.#toA2ATask(run) };
      }

      if (method === "tasks/cancel") {
        const taskId = String(params.id || params.taskId || "");
        const run = this.runner.cancelRun(taskId);
        if (!run) {
          return this.#rpcError(id, -32001, `Task not found: ${taskId}`);
        }
        return { jsonrpc: "2.0", id, result: this.#toA2ATask(run) };
      }

      return this.#rpcError(id, -32601, `Unsupported A2A method: ${method}`);
    } catch (err) {
      return this.#rpcError(id, -32000, err instanceof Error ? err.message : String(err));
    }
  }

  #selectDefaultHarness() {
    const detected = this.runner.detectHarnesses();
    const first = detected.find((h) => h.installed);
    if (!first) {
      throw new Error("No supported external harness CLI found on PATH.");
    }
    return first.id;
  }

  /**
   * @param {any} run
   */
  #toA2ATask(run) {
    const stateMap = {
      running: "working",
      completed: "completed",
      failed: "failed",
      cancelled: "canceled",
      advisory_blocked: "input-required",
    };
    return {
      kind: "task",
      id: run.id || `task_${crypto.randomBytes(4).toString("hex")}`,
      status: {
        state: stateMap[run.status] || "unknown",
        timestamp: run.completedAt || run.startedAt || new Date().toISOString(),
        message: run.outputText
          ? {
              role: "agent",
              parts: [{ kind: "text", text: run.outputText }],
            }
          : undefined,
      },
      metadata: {
        harness: run.harness,
        executionMode: run.executionMode,
        effectiveCwd: run.effectiveCwd,
        advisory: run.advisory,
      },
    };
  }

  /**
   * @param {any} id
   * @param {number} code
   * @param {string} message
   */
  #rpcError(id, code, message) {
    return {
      jsonrpc: "2.0",
      id,
      error: { code, message },
    };
  }
}

/**
 * @param {any} message
 * @returns {string}
 */
function extractMessageText(message) {
  if (!message) return "";
  if (typeof message === "string") return message;
  if (Array.isArray(message.parts)) {
    return message.parts
      .map((p) => (typeof p?.text === "string" ? p.text : ""))
      .filter(Boolean)
      .join("\n");
  }
  return String(message.text || "");
}
