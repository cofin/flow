#!/usr/bin/env node
/**
 * Flow MCP server and `ui://flow/studio` MCP App provider over stdio JSON-RPC.
 *
 * Keeps all tool names `<= 20` characters (`flow_status`, `flow_preflight`, `flow_tasks`,
 * `flow_sync`, `flow_plan_strong`, `flow_verify_strong`) so prefixed names stay within
 * every harness limit.
 */

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

import { CrossHarnessRunner } from "./bridges/cli.mjs";
import { SpecFeedbackStore } from "./spec/feedback.mjs";
import { GitBranchSpecScanner, SpecPrPublisher } from "./spec/git-spec-branch.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";
import { TaskPlanner } from "./spec/task-planner.mjs";
import { WorkspaceSync } from "./spec/workspace-sync.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));

export const FLOW_MCP_TOOLS = Object.freeze([
  {
    name: "flow_status",
    description: "Inspect Flow spec status and next ready task.",
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
    description: "Run Flow preflight and dependency checks.",
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
    name: "flow_tasks",
    description: "Plan ready tasks into parallel steps on separate files and build each worker's brief.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        chapter_id: { type: "string" },
        all_ready_chapters: { type: "boolean" },
        workers: { type: "integer" },
      },
      required: ["flow_id"],
    },
  },
  {
    name: "flow_sync",
    description: "Sync checklist markers, commit SHAs, and spec frontmatter.",
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
    name: "flow_plan_strong",
    description: "Run planning on the strongest available model.",
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
    name: "flow_verify_strong",
    description: "Run spec validation or high-risk review on the strongest available model.",
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
    name: "flow_spec_branches",
    description: "Discover specs across local branches and remote tracking refs.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        include_archived: { type: "boolean" },
      },
    },
  },
  {
    name: "flow_spec_feedback",
    description: "List, add, reply to, or resolve out-of-tree spec review notes.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        action: { type: "string" },
        flow_id: { type: "string" },
        rel_path: { type: "string" },
        comment_id: { type: "string" },
        parent_comment_id: { type: "string" },
        body: { type: "string" },
        comment_kind: { type: "string" },
        start_line: { type: "integer" },
        end_line: { type: "integer" },
        quote: { type: "string" },
      },
    },
  },
  {
    name: "flow_spec_pr",
    description: "Publish a spec on a dedicated branch/PR or sync PR comments.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        action: { type: "string" },
        branch: { type: "string" },
        base: { type: "string" },
        pr_number: { type: "integer" },
        push: { type: "boolean" },
        draft: { type: "boolean" },
      },
      required: ["flow_id"],
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
              description: "Interactive Flow Studio view for specs, tasks, and review notes.",
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
      } else if (name === "flow_tasks") {
        payload = new TaskPlanner(ws, {
          ...(args.workers ? { workers: Number(args.workers) } : {}),
        }).plan({
          flowId: args.flow_id,
          chapterId: args.chapter_id || null,
          allReadyChapters: Boolean(args.all_ready_chapters),
          includeBriefs: true,
        });
      } else if (name === "flow_sync") {
        payload = await new WorkspaceSync(ws).run({
          flowId: args.flow_id || null,
          chapterId: args.chapter_id || null,
        });
      } else if (name === "flow_spec_branches") {
        const localSpecs = engine.listSpecs({ includeArchived: Boolean(args.include_archived) });
        payload = {
          specs: await new GitBranchSpecScanner(ws).listAllBranchSpecs({
            localSpecs,
            includeArchived: Boolean(args.include_archived),
          }),
        };
      } else if (name === "flow_spec_feedback") {
        const store = new SpecFeedbackStore(ws);
        const action = String(args.action || "list");
        const target = args.rel_path || args.flow_id || "";
        if (action === "add") {
          payload = {
            comment: store.add({
              flowId: args.flow_id || undefined,
              relPath: args.rel_path || undefined,
              startLine: Number(args.start_line || 1),
              endLine: Number(args.end_line || args.start_line || 1),
              quote: args.quote || undefined,
              commentKind: args.comment_kind || "feedback",
              body: String(args.body || ""),
            }),
          };
        } else if (action === "reply") {
          payload = {
            comment: store.replyToComment(target, String(args.parent_comment_id || args.comment_id || ""), {
              body: String(args.body || ""),
              commentKind: args.comment_kind || "feedback",
            }),
          };
        } else if (action === "resolve" || action === "edit") {
          payload = {
            comment: store.setResolvedOrUpdate(target, String(args.comment_id || ""), {
              ...(action === "resolve" ? { resolved: true } : {}),
              ...(args.body !== undefined ? { body: String(args.body) } : {}),
            }),
          };
        } else {
          payload = {
            comments: args.rel_path ? store.list(String(args.rel_path)) : store.listForFlow(String(args.flow_id || "")),
          };
        }
      } else if (name === "flow_spec_pr") {
        const publisher = new SpecPrPublisher(ws);
        if (args.action === "comments") {
          payload = await publisher.syncPullRequestComments(String(args.flow_id), {
            prNumber: args.pr_number ? Number(args.pr_number) : null,
            branch: args.branch || null,
          });
        } else {
          payload = await publisher.publishSpecToPr(String(args.flow_id), {
            branch: args.branch || null,
            base: args.base || null,
            draft: Boolean(args.draft),
            push: Boolean(args.push),
          });
        }
      } else if (name === "flow_plan_strong" || name === "flow_verify_strong") {
        const activeRunner = runner || new CrossHarnessRunner({ defaultWorkspace: ws });
        payload = await activeRunner.delegate({
          workspacePath: ws,
          harness: args.harness || null,
          taskKind: name === "flow_plan_strong" ? "planning" : "semantic_validation",
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
