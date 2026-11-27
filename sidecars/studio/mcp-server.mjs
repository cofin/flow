#!/usr/bin/env node
/**
 * Flow MCP server and Antigravity MCP App (`io.modelcontextprotocol/ui` +
 * `com.google.antigravity/ui`) provider over stdio JSON-RPC 2.0.
 *
 * Keeps all tool names `<= 20` characters so prefixed names stay well under every
 * harness limit (`mcp_<plugin>_<server>_<tool> <= 64` in Antigravity, `<= 59` in Cursor).
 */

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

import { CrossHarnessRunner } from "./bridges/cli.mjs";
import { isInternalSidecarPath } from "./core/fs-io.mjs";
import { StudioApiService, StudioRequestError } from "./router.mjs";
import { SpecFeedbackStore } from "./spec/feedback.mjs";
import { GitBranchSpecScanner, SpecPrPublisher } from "./spec/git-spec-branch.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";
import { TaskPlanner } from "./spec/task-planner.mjs";
import { WorkspaceSync } from "./spec/workspace-sync.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(STUDIO_DIR, "web");
const PLUGIN_ROOT = path.resolve(STUDIO_DIR, "..", "..");

const STUDIO_UI_URI = "ui://flow/studio.html";
const STUDIO_UI_LEGACY_URI = "ui://flow/studio";
const STATUS_CARD_UI_URI = "ui://flow/status-card.html";
const MCP_APP_MIME = "text/html;profile=mcp-app";

const PKG_VERSION = (() => {
  try {
    const raw = JSON.parse(fs.readFileSync(path.join(PLUGIN_ROOT, "package.json"), "utf8"));
    return String(raw.version || "0.33.0");
  } catch {
    return "0.33.0";
  }
})();

export const ALLOWED_STUDIO_API_ROUTES = Object.freeze(
  new Set([
    "/api/studio-context",
    "/api/pin-workspace",
    "/api/bundle-snapshot",
    "/api/portfolio-snapshot",
    "/api/spec-document",
    "/api/spec-dag",
    "/api/spec-review",
    "/api/review-comments",
    "/api/create-spec",
    "/api/import-plan",
    "/api/sync",
    "/api/spec-branches",
    "/api/spec-pull",
    "/api/spec-pr",
    "/api/spec-share-branch",
    "/api/remote-repo-specs",
    "/api/workspace-setup",
    "/api/workspace-asset",
    "/api/catalog-index",
    "/api/catalog-search",
    "/api/catalog-provenance",
    "/api/catalog-entry",
    "/api/catalog-drift",
    "/api/catalog-status",
    "/api/start-workspace-conversation",
    "/api/models-and-quota",
    "/api/review-plan",
    "/api/trajectories",
    "/api/activity",
    "/api/permissions",
    "/api/harnesses",
    "/api/harness-dispatch",
    "/api/harness-delegate",
    "/api/harness-runs",
    "/api/run-entrypoint",
  ]),
);

const BASE_FLOW_MCP_TOOLS = Object.freeze([
  {
    name: "flow_studio",
    description:
      "Open Flow Studio to inspect active specs, chapters, review comments, and bundle notes.",
    inputSchema: {
      type: "object",
      properties: {
        workspace: { type: "string" },
        flow_id: { type: "string" },
        tab: { type: "string" },
        rel_path: { type: "string" },
      },
    },
    _meta: {
      ui: { resourceUri: STUDIO_UI_URI },
    },
  },
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
    _meta: {
      ui: { resourceUri: STATUS_CARD_UI_URI },
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
    description:
      "Plan ready tasks into parallel steps on separate files and build each worker's brief.",
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

const APP_ONLY_API_TOOL = Object.freeze({
  name: "flow_studio_api",
  description:
    "Internal UI RPC bridge for Flow Studio MCP App views (app-only; prefer flow_status/flow_tasks/flow_sync).",
  inputSchema: {
    type: "object",
    properties: {
      route: { type: "string" },
      payload: { type: "object" },
    },
    required: ["route"],
  },
  _meta: {
    ui: { visibility: ["app"] },
  },
});

export const FLOW_MCP_TOOLS = BASE_FLOW_MCP_TOOLS;

function escapeInlineScript(src) {
  return String(src || "").replace(/<\/script/gi, "<\\/script");
}

function escapeInlineStyle(src) {
  return String(src || "").replace(/<\/style/gi, "<\\/style");
}

function readWebAsset(fileName) {
  const fullPath = path.join(WEB_DIR, fileName);
  return fs.existsSync(fullPath) ? fs.readFileSync(fullPath, "utf8") : "";
}

function readLogoDataUri() {
  const svg = readWebAsset("logo.svg");
  if (!svg) return "";
  return `data:image/svg+xml;base64,${Buffer.from(svg, "utf8").toString("base64")}`;
}

const MCP_THEME_BRIDGE_CSS = `
:root {
  --flow-bg: var(--color-background-primary, var(--background, #f8fafc));
  --flow-fg: var(--color-text-primary, var(--foreground, #202235));
  --flow-surface: var(--color-background-secondary, var(--card, #ffffff));
  --flow-surface-subtle: var(--color-background-tertiary, var(--muted, #f1f4f8));
  --flow-muted-fg: var(--color-text-secondary, var(--muted-foreground, #5a6275));
  --flow-line: var(--color-border-primary, var(--border, #dcdfe4));
  --flow-primary: var(--color-ring-primary, var(--primary, #202235));
  --flow-primary-fg: var(--color-text-inverse, var(--primary-foreground, #ffffff));
  --flow-ok: var(--color-text-success, #188038);
  --flow-warn: var(--color-text-warning, #b06000);
  --font-sans: var(--font-sans, Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}
`;

/**
 * Assemble the self-contained single-file HTML document for `ui://flow/studio.html`
 * with all CSS, logo SVG, `@modelcontextprotocol/ext-apps` SDK bundle, `host-bridge.js`,
 * and `app.js` inlined so it satisfies MCP Apps' default-deny CSP (`default-src 'none'`).
 */
export function buildStudioMcpAppHtml() {
  const stylesCss = readWebAsset("styles.css");
  const sdkBundle = readWebAsset("mcp-ext-apps.bundle.js");
  const hostBridgeJs = readWebAsset("host-bridge.js");
  const appJs = readWebAsset("app.js");
  const logoDataUri = readLogoDataUri();

  return [
    "<!DOCTYPE html>",
    '<html lang="en">',
    "<head>",
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    "  <title>Flow Studio</title>",
    "  <style>",
    escapeInlineStyle(stylesCss),
    escapeInlineStyle(MCP_THEME_BRIDGE_CSS),
    "  </style>",
    "</head>",
    "<body>",
    '  <div id="studio-root" class="studio-shell"><div class="subtle-meta" style="padding:24px">Loading Flow Studio…</div></div>',
    '  <div id="drawer-backdrop" class="drawer-backdrop hidden"></div>',
    '  <aside id="new-spec-drawer" class="drawer hidden" aria-label="Create Specification"></aside>',
    '  <aside id="attention-drawer" class="drawer hidden" aria-label="Attention Queue"></aside>',
    '  <aside id="comment-modal" class="comment-modal hidden" aria-label="Spec Review Comments"></aside>',
    '  <div id="media-lightbox" class="media-lightbox hidden" aria-label="Media Lightbox"></div>',
    '  <div id="toast-region" class="toast-region" aria-live="polite"></div>',
    `  <script>window.__FLOW_MCP_APP__ = true; window.__FLOW_LOGO_URI__ = ${JSON.stringify(logoDataUri)};</script>`,
    `  <script>${escapeInlineScript(sdkBundle)}</script>`,
    `  <script>${escapeInlineScript(hostBridgeJs)}</script>`,
    `  <script>${escapeInlineScript(appJs)}</script>`,
    "</body>",
    "</html>",
  ].join("\n");
}

/**
 * Assemble a compact, auto-resizing inline MCP App card for `flow_status` (`ui://flow/status-card.html`).
 */
export function buildStatusCardMcpAppHtml() {
  const sdkBundle = readWebAsset("mcp-ext-apps.bundle.js");
  const cardScript = `
(async function initFlowStatusCard() {
  const root = document.getElementById("card-root");
  const sdk = window.__MCP_EXT_APPS__;
  if (!sdk || !root) return;
  const app = new sdk.App({ name: "Flow Status", version: ${JSON.stringify(PKG_VERSION)} }, {});

  function applyCtx(ctx) {
    if (!ctx) return;
    if (ctx.theme) sdk.applyDocumentTheme(ctx.theme);
    if (ctx.styles && ctx.styles.variables) sdk.applyHostStyleVariables(ctx.styles.variables);
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function renderStatus(payload) {
    root.textContent = "";
    if (!payload || typeof payload !== "object") {
      root.appendChild(el("div", "meta", "Waiting for Flow status..."));
      return;
    }
    const specs = Array.isArray(payload.specs) ? payload.specs : payload.spec ? [payload.spec] : [];
    const header = el("div", "head");
    const wsName = String(payload.workspace || "").split("/").filter(Boolean).pop() || "Workspace";
    header.appendChild(el("div", "title", "Flow · " + wsName));
    const caps = app.getHostCapabilities() || {};
    const actions = el("div", "actions");
    if (caps.updateModelContext && specs.length > 0) {
      const btn = el("button", "btn", "Attach to prompt");
      btn.addEventListener("click", async () => {
        const lines = specs.map((s) => "- " + s.flow_id + " [" + s.state + "] " + (s.task_counts?.completed || 0) + "/" + (s.task_counts?.total || 0));
        await app.updateModelContext({ content: [{ type: "text", text: "Flow status (" + wsName + "):\\n" + lines.join("\\n") }] });
        btn.textContent = "Attached";
      });
      actions.appendChild(btn);
    }
    header.appendChild(actions);
    root.appendChild(header);

    if (specs.length === 0) {
      root.appendChild(el("div", "meta", "No active specs in .agents/bundles/specs/."));
      return;
    }

    const list = el("div", "list");
    for (const spec of specs.slice(0, 6)) {
      const row = el("div", "row");
      const top = el("div", "row-top");
      top.appendChild(el("span", "spec-name", spec.title || spec.flow_id));
      const done = Number(spec.task_counts?.completed || 0);
      const total = Number(spec.task_counts?.total || 0);
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      top.appendChild(el("span", "badge", (spec.state || "draft") + " · " + done + "/" + total));
      row.appendChild(top);
      const bar = el("div", "bar");
      const fill = el("div", "fill");
      fill.style.width = pct + "%";
      bar.appendChild(fill);
      row.appendChild(bar);
      list.appendChild(row);
    }
    root.appendChild(list);

    if (payload.next_runnable) {
      const nxt = payload.next_runnable;
      root.appendChild(el("div", "next", "Next ready: " + nxt.flow_id + " → " + nxt.task_id + (nxt.title ? " (" + nxt.title + ")" : "")));
    }
  }

  app.ontoolinput = () => {
    root.textContent = "Loading Flow status...";
  };
  app.ontoolresult = (result) => {
    const data = result && result.structuredContent ? result.structuredContent : null;
    renderStatus(data);
  };
  app.onhostcontextchanged = applyCtx;
  await app.connect();
  applyCtx(app.getHostContext());
})();
`;

  return [
    "<!DOCTYPE html>",
    '<html lang="en">',
    "<head>",
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1">',
    "  <title>Flow Status</title>",
    "  <style>",
    "    body { margin: 0; padding: 12px 14px; background: var(--color-background-primary, #fff); color: var(--color-text-primary, #1f1f1f); font-family: var(--font-sans, system-ui, sans-serif); font-size: 13px; }",
    "    .head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 10px; }",
    "    .title { font-weight: 600; font-size: 14px; }",
    "    .actions { display: flex; gap: 6px; }",
    "    .btn { border: 1px solid var(--color-border-primary, #d0d7de); background: var(--color-background-secondary, #f6f8fa); color: var(--color-text-primary, #1f1f1f); border-radius: 6px; padding: 3px 9px; font-size: 12px; cursor: pointer; }",
    "    .list { display: flex; flex-direction: column; gap: 8px; }",
    "    .row { padding: 8px 10px; border: 1px solid var(--color-border-primary, #d0d7de); border-radius: 8px; background: var(--color-background-secondary, #f8fafc); }",
    "    .row-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }",
    "    .spec-name { font-weight: 500; }",
    "    .badge { font-size: 11px; color: var(--color-text-secondary, #57606a); }",
    "    .bar { height: 5px; border-radius: 999px; background: var(--color-background-tertiary, #e5e7eb); overflow: hidden; }",
    "    .fill { height: 100%; background: var(--color-ring-primary, #2563eb); border-radius: 999px; }",
    "    .next, .meta { margin-top: 8px; font-size: 12px; color: var(--color-text-secondary, #57606a); }",
    "  </style>",
    "</head>",
    "<body>",
    '  <div id="card-root">Loading Flow status...</div>',
    `  <script>${escapeInlineScript(sdkBundle)}</script>`,
    `  <script>${escapeInlineScript(cardScript)}</script>`,
    "</body>",
    "</html>",
  ].join("\n");
}

function buildToolsList(clientSupportsUi) {
  if (clientSupportsUi) {
    return [...BASE_FLOW_MCP_TOOLS, APP_ONLY_API_TOOL];
  }
  return BASE_FLOW_MCP_TOOLS.map((tool) => {
    if (!tool._meta) return tool;
    const { _meta, ...plain } = tool;
    return plain;
  });
}

function resolveDefaultWorkspace(service, fallbackWorkspace) {
  const candidate = fallbackWorkspace ? path.resolve(fallbackWorkspace) : process.cwd();
  if (candidate && !isInternalSidecarPath(candidate) && fs.existsSync(candidate)) {
    return candidate;
  }
  const fromRegistry = service?.workspaceRegistry?.getLastActiveWorkspace?.();
  if (fromRegistry && fs.existsSync(fromRegistry)) {
    return fromRegistry;
  }
  return candidate;
}

/**
 * Create a stateful MCP session handler (tracking client UI capabilities and a shared `StudioApiService`).
 *
 * @param {{ defaultWorkspace?: string, env?: NodeJS.ProcessEnv, runner?: CrossHarnessRunner | null, studioService?: StudioApiService | null }} [options]
 */
export function createMcpSession(options = {}) {
  const env = options.env || process.env;
  const service =
    options.studioService ||
    new StudioApiService({
      env,
      pluginRoot: PLUGIN_ROOT,
    });
  const state = {
    clientSupportsUi: false,
    clientSupportsAntigravityUi: false,
    service,
  };

  return {
    state,
    close() {
      if (!options.studioService) {
        service.close();
      }
    },
    async handle(req) {
      return handleMcpRequest(req, {
        defaultWorkspace: options.defaultWorkspace,
        runner: options.runner || null,
        session: state,
      });
    },
  };
}

/**
 * Handle one MCP JSON-RPC 2.0 message cleanly for both live stdio sessions and automated tests.
 *
 * @param {Record<string, any>} req
 * @param {{ defaultWorkspace?: string, runner?: CrossHarnessRunner | null, session?: { clientSupportsUi: boolean, clientSupportsAntigravityUi: boolean, service: StudioApiService } | null }} [options]
 */
export async function handleMcpRequest(
  req,
  { defaultWorkspace = process.cwd(), runner = null, session = null } = {},
) {
  const id = req?.id ?? null;
  const method = String(req?.method || "");
  const params = req?.params || {};
  const activeService =
    session?.service ||
    new StudioApiService({
      env: { ...process.env, FLOW_STUDIO_DEFAULT_WORKSPACE: defaultWorkspace },
      pluginRoot: PLUGIN_ROOT,
    });
  const ownsService = !session?.service;

  const explicitWs = params.arguments?.workspace || params.workspace;
  const ws = explicitWs
    ? path.resolve(String(explicitWs))
    : resolveDefaultWorkspace(activeService, defaultWorkspace);

  try {
    if (method === "initialize") {
      const uiExt = params?.capabilities?.extensions?.["io.modelcontextprotocol/ui"];
      const agyExt = params?.capabilities?.extensions?.["com.google.antigravity/ui"];
      const supportsUi = Boolean(uiExt || agyExt);
      if (session) {
        session.clientSupportsUi = supportsUi;
        session.clientSupportsAntigravityUi = Boolean(agyExt);
      }
      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2025-03-26",
          capabilities: {
            tools: {},
            resources: {},
            ...(supportsUi ? { extensions: { "io.modelcontextprotocol/ui": {} } } : {}),
          },
          serverInfo: { name: "flow", version: PKG_VERSION },
        },
      };
    }

    if (method === "ping") {
      return { jsonrpc: "2.0", id, result: {} };
    }

    if (method === "tools/list") {
      const includeUi = session ? session.clientSupportsUi : true;
      return { jsonrpc: "2.0", id, result: { tools: buildToolsList(includeUi) } };
    }

    if (method === "resources/list") {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          resources: [
            {
              uri: STUDIO_UI_URI,
              name: "Flow Studio",
              mimeType: MCP_APP_MIME,
              description: "Interactive Flow Studio view for specs, tasks, review comments, and bundle notes.",
              _meta: { ui: { prefersBorder: false } },
            },
            {
              uri: STATUS_CARD_UI_URI,
              name: "Flow Status Card",
              mimeType: MCP_APP_MIME,
              description: "Compact inline spec and chapter status card.",
              _meta: { ui: { prefersBorder: false } },
            },
          ],
        },
      };
    }

    if (method === "resources/read") {
      const uri = String(params.uri || "");
      if (uri === STUDIO_UI_URI || uri === STUDIO_UI_LEGACY_URI) {
        return {
          jsonrpc: "2.0",
          id,
          result: {
            contents: [
              {
                uri,
                mimeType: MCP_APP_MIME,
                text: buildStudioMcpAppHtml(),
                _meta: { ui: { prefersBorder: false } },
              },
            ],
          },
        };
      }
      if (uri === STATUS_CARD_UI_URI) {
        return {
          jsonrpc: "2.0",
          id,
          result: {
            contents: [
              {
                uri,
                mimeType: MCP_APP_MIME,
                text: buildStatusCardMcpAppHtml(),
                _meta: { ui: { prefersBorder: false } },
              },
            ],
          },
        };
      }
      return { jsonrpc: "2.0", id, error: { code: -32602, message: `Unknown resource URI: ${uri}` } };
    }

    if (method === "tools/call") {
      const name = String(params.name || "");
      const args = params.arguments || {};
      const engine = new SpecEngine(ws);
      let payload;

      if (name === "flow_studio") {
        const ctx = await activeService.handleApi("/api/studio-context", {
          ...(args.workspace ? { workspacePath: ws } : {}),
        });
        const targetWs = ctx.defaultWorkspace || ws;
        const statusSummary = new SpecEngine(targetWs).status(args.flow_id || null);
        payload = {
          workspace: targetWs,
          studioContext: ctx,
          statusSummary,
          initialTab: args.tab || (args.flow_id || args.rel_path ? "review" : "roadmap"),
          initialFlowId: args.flow_id || null,
          initialRelPath: args.rel_path || null,
        };
        const specCount = Array.isArray(statusSummary.specs) ? statusSummary.specs.length : statusSummary.spec ? 1 : 0;
        return {
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              {
                type: "text",
                text: `Flow Studio ready for ${targetWs} (${specCount} spec(s)).`,
              },
            ],
            structuredContent: payload,
          },
        };
      }

      if (name === "flow_studio_api") {
        const route = String(args.route || "").trim();
        if (!ALLOWED_STUDIO_API_ROUTES.has(route)) {
          return {
            jsonrpc: "2.0",
            id,
            error: { code: -32602, message: `Disallowed or unknown Studio API route: ${route}` },
          };
        }
        const routePayload = args.payload && typeof args.payload === "object" ? args.payload : {};
        const apiResult = await activeService.handleApi(route, routePayload);
        return {
          jsonrpc: "2.0",
          id,
          result: {
            content: [{ type: "text", text: `ok (${route})` }],
            structuredContent: apiResult,
          },
        };
      }

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
            comments: args.rel_path
              ? store.list(String(args.rel_path))
              : store.listForFlow(String(args.flow_id || "")),
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

    if (method.startsWith("notifications/")) {
      return null;
    }

    return { jsonrpc: "2.0", id, error: { code: -32601, message: `Unsupported MCP method: ${method}` } };
  } catch (err) {
    const code = err instanceof StudioRequestError ? -32602 : -32000;
    return {
      jsonrpc: "2.0",
      id,
      error: { code, message: err instanceof Error ? err.message : String(err) },
    };
  } finally {
    if (ownsService) {
      activeService.close();
    }
  }
}

const isMain = (() => {
  try {
    return (
      Boolean(process.argv[1]) &&
      fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))
    );
  } catch {
    return false;
  }
})();

if (isMain) {
  const session = createMcpSession({ defaultWorkspace: process.cwd(), env: process.env });
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
    const resp = await session.handle(parsed);
    if (resp) {
      process.stdout.write(`${JSON.stringify(resp)}\n`);
    }
  });
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => {
      session.close();
      process.exit(0);
    });
  }
}
