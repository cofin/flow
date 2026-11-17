#!/usr/bin/env node
/**
 * Zero-dependency Flow MCP server & `ui://flow/studio` MCP App provider over stdio JSON-RPC.
 *
 * Keeps all tool names `<= 20` characters (`flow_status`, `flow_preflight`, `flow_slice_pack`,
 * `flow_sync`, `flow_plan_frontier`, `flow_verify_frontier`) so fully prefixed tool names stay well
 * below every harness limit (`<= 59` in Cursor, `<= 64` in Antigravity, `<= 128` in Claude/Codex).
 */

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

import { CrossHarnessRunner } from "./bridges/cli.mjs";
import { SliceCompiler } from "./spec/slice-compiler.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));

export const FLOW_MCP_TOOLS = Object.freeze([
  {
    name: "flow_status",
    description: "Inspect Flow spec status and next runnable slice deterministically (0 LLM tokens).",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
      },
    },
  },
  {
    name: "flow_preflight",
    description: "Run deterministic Flow dispatch preflight and dependency checks (0 LLM tokens).",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        chapter_id: { type: "string" },
        all_ready_chapters: { type: "boolean" },
      },
      required: ["flow_id"],
    },
  },
  {
    name: "flow_slice_pack",
    description: "Compile <=250-LOC disjoint waves and pre-extracted <4k-token Context Packs (0 LLM tokens).",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        chapter_id: { type: "string" },
        all_ready_chapters: { type: "boolean" },
        max_workers: { type: "integer" },
      },
      required: ["flow_id"],
    },
  },
  {
    name: "flow_sync",
    description: "Synchronize checklist markers, SHAs, and spec frontmatter deterministically (0 LLM tokens).",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        chapter_id: { type: "string" },
      },
      required: ["flow_id"],
    },
  },
  {
    name: "flow_plan_frontier",
    description: "Delegate deep planning upward to the strongest healthy Thinking / Frontier model.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        harness: { type: "string" },
        prompt: { type: "string" },
      },
      required: ["prompt"],
    },
  },
  {
    name: "flow_verify_frontier",
    description: "Delegate semantic contract validation or high-risk review upward to a Frontier model.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        harness: { type: "string" },
        prompt: { type: "string" },
      },
      required: ["prompt"],
    },
  },
]);

/**
 * Handle one MCP JSON-RPC 2.0 message cleanly for both live stdio sessions and automated tests.
 *
 * @param {Record<string, any>} req
 * @param {{ defaultWorkspace?: string, runner?: CrossHarnessRunner }} [options]
 */
export async function handleMcpRequest(req, { defaultWorkspace = process.cwd(), runner = null } = {}) {
  const id = req?.id ?? null;
  const method = String(req?.method || "");
  const params = req?.params || {};
  const ws = path.resolve(String(params.arguments?.workspace || params.workspace || defaultWorkspace));

  try {
    if (method === "initialize") {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2025-03-26",
          capabilities: { tools: {}, resources: {} },
          serverInfo: { name: "flow", version: "0.31.0" },
        },
      };
    }

    if (method === "tools/list") {
      return { jsonrpc: "2.0", id, result: { tools: FLOW_MCP_TOOLS } };
    }

    if (method === "resources/list") {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          resources: [
            {
              uri: "ui://flow/studio",
              name: "Flow Studio Companion",
              mimeType: "text/html;profile=mcp-app",
              description: "Interactive Flow spec DAG, wave progress, and review view.",
            },
          ],
        },
      };
    }

    if (method === "resources/read") {
      const uri = String(params.uri || "");
      if (uri !== "ui://flow/studio") {
        return { jsonrpc: "2.0", id, error: { code: -32602, message: `Unknown resource URI: ${uri}` } };
      }
      const htmlPath = path.join(STUDIO_DIR, "web", "index.html");
      const fallbackHtml = "<!doctype html><html><body><div id='studio-root'>Flow Studio</div></body></html>";
      const text = fs.existsSync(htmlPath) ? fs.readFileSync(htmlPath, "utf8") : fallbackHtml;
      return {
        jsonrpc: "2.0",
        id,
        result: { contents: [{ uri: "ui://flow/studio", mimeType: "text/html;profile=mcp-app", text }] },
      };
    }

    if (method === "tools/call") {
      const name = String(params.name || "");
      const args = params.arguments || {};
      const engine = new SpecEngine(ws);
      let payload;

      if (name === "flow_status") {
        payload = engine.status(args.flow_id || null);
      } else if (name === "flow_preflight") {
        payload = engine.preflight(args.flow_id, {
          chapterId: args.chapter_id || null,
          allReadyChapters: Boolean(args.all_ready_chapters),
        });
      } else if (name === "flow_slice_pack") {
        payload = new SliceCompiler(ws, {
          ...(args.max_workers ? { maxWaveWorkers: Number(args.max_workers) } : {}),
        }).compile({
          flowId: args.flow_id,
          chapterId: args.chapter_id || null,
          allReadyChapters: Boolean(args.all_ready_chapters),
          includeContextPacks: true,
        });
      } else if (name === "flow_sync") {
        payload = engine.syncChecklists({ flowId: args.flow_id, chapterId: args.chapter_id || null });
      } else if (name === "flow_plan_frontier" || name === "flow_verify_frontier") {
        const activeRunner = runner || new CrossHarnessRunner({ defaultWorkspace: ws });
        payload = await activeRunner.delegate({
          workspacePath: ws,
          harness: args.harness || null,
          taskKind: name === "flow_plan_frontier" ? "planning" : "semantic_validation",
          prompt: String(args.prompt || ""),
        });
      } else {
        return { jsonrpc: "2.0", id, error: { code: -32601, message: `Unknown MCP tool: ${name}` } };
      }

      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
          structuredContent: payload,
        },
      };
    }

    if (method === "notifications/initialized") {
      return null;
    }

    return { jsonrpc: "2.0", id, error: { code: -32601, message: `Unsupported MCP method: ${method}` } };
  } catch (err) {
    return {
      jsonrpc: "2.0",
      id,
      error: { code: -32000, message: err instanceof Error ? err.message : String(err) },
    };
  }
}

const isMain = (() => {
  try {
    return Boolean(process.argv[1]) && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();

if (isMain) {
  const rl = readline.createInterface({ input: process.stdin });
  rl.on("line", async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    let parsed;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      return;
    }
    const resp = await handleMcpRequest(parsed);
    if (resp) {
      process.stdout.write(`${JSON.stringify(resp)}\n`);
    }
  });
}
