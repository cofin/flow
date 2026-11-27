/**
 * Google Antigravity Sidecar SDK entrypoint for Flow Studio.
 *
 * Serves Flow Studio across both Antigravity Desktop App and Antigravity Web (`hub` proxy).
 * Read-only API routes are registered on both `GET` and `POST` because `sidecar_sdk` bypasses
 * per-frame `?token=` validation on `GET` requests (relying on the Hub gateway's authentication),
 * matching Antigravity's built-in `swarm_board` sidecar.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Response, SidecarApp } from "sidecar_sdk";

import { StudioApiService, StudioRequestError } from "./router.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(STUDIO_DIR, "web");
const PLUGIN_ROOT = path.resolve(STUDIO_DIR, "..", "..");

const SEC_HEADERS = {
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "no-store",
};

const HTML_HEADERS = {
  ...SEC_HEADERS,
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: blob:; media-src 'self' data: blob:; " +
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'",
};

/** @type {Map<string, { mtimeMs: number, data: Buffer | string }>} */
const STATIC_ASSET_CACHE = new Map();

function loadStaticAsset(fileName, binary = false) {
  const fullPath = path.join(WEB_DIR, fileName);
  const stat = fs.statSync(fullPath);
  const cached = STATIC_ASSET_CACHE.get(fileName);
  if (cached && cached.mtimeMs === stat.mtimeMs) {
    return cached.data;
  }
  const data = binary ? fs.readFileSync(fullPath) : fs.readFileSync(fullPath, "utf8");
  STATIC_ASSET_CACHE.set(fileName, { mtimeMs: stat.mtimeMs, data });
  return data;
}

/**
 * Decode JSON payload passed via `?payload=<json>` on `GET` read requests.
 *
 * @param {Record<string, any> | null | undefined} rawData
 * @returns {Record<string, any>}
 */
function normalizeApiData(rawData) {
  if (!rawData || typeof rawData !== "object") return {};
  if (typeof rawData.payload === "string" && rawData.payload.trim()) {
    try {
      const parsed = JSON.parse(rawData.payload);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        const { payload: _ignored, ...rest } = rawData;
        return { ...rest, ...parsed };
      }
    } catch {
      throw new StudioRequestError("Malformed JSON payload query parameter");
    }
  }
  return rawData;
}

const service = new StudioApiService({ env: process.env, pluginRoot: PLUGIN_ROOT });
const app = new SidecarApp();

const staticAsset = (fileName, contentType, { binary = false, headers = SEC_HEADERS } = {}) => () =>
  new Response(loadStaticAsset(fileName, binary), { contentType, status: 200, headers });

app.page("/", staticAsset("index.html", "text/html; charset=utf-8", { headers: HTML_HEADERS }));
app.page("/dashboard", staticAsset("index.html", "text/html; charset=utf-8", { headers: HTML_HEADERS }));
app.page("/styles.css", staticAsset("styles.css", "text/css; charset=utf-8"));
app.page("/host-bridge.js", staticAsset("host-bridge.js", "application/javascript; charset=utf-8"));
app.page("/app.js", staticAsset("app.js", "application/javascript; charset=utf-8"));
app.page("/logo.svg", staticAsset("logo.svg", "image/svg+xml"));
app.page("/favicon.svg", staticAsset("favicon.svg", "image/svg+xml"));
app.page("/favicon.ico", staticAsset("favicon.ico", "image/x-icon", { binary: true }));

const READ_API_ROUTES = new Set([
  "/api/studio-context",
  "/api/bundle-snapshot",
  "/api/portfolio-snapshot",
  "/api/spec-document",
  "/api/spec-dag",
  "/api/spec-review",
  "/api/review-comments",
  "/api/spec-branches",
  "/api/remote-repo-specs",
  "/api/catalog-search",
  "/api/catalog-provenance",
  "/api/catalog-entry",
  "/api/catalog-drift",
  "/api/catalog-status",
  "/api/models-and-quota",
  "/api/review-plan",
  "/api/trajectories",
  "/api/activity",
  "/api/permissions",
  "/api/harnesses",
  "/api/harness-runs",
]);

const API_ROUTES = [
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
];

function createApiHandler(routePath, { readOnly = false } = {}) {
  return async (rawData) => {
    try {
      const data = normalizeApiData(rawData);
      if (readOnly && routePath === "/api/review-comments") {
        const action = String(data.action || "list").toLowerCase();
        if (action !== "list") {
          return new Response(JSON.stringify({ error: "Mutating review-comments actions require POST" }), {
            contentType: "application/json; charset=utf-8",
            status: 405,
            headers: SEC_HEADERS,
          });
        }
      }
      const result = await service.handleApi(routePath, data);
      return new Response(JSON.stringify(result), {
        contentType: "application/json; charset=utf-8",
        status: 200,
        headers: SEC_HEADERS,
      });
    } catch (err) {
      const status = err instanceof StudioRequestError ? 400 : 500;
      const message = err instanceof Error ? err.message : "Unexpected sidecar error";
      return new Response(JSON.stringify({ error: message }), {
        contentType: "application/json; charset=utf-8",
        status,
        headers: SEC_HEADERS,
      });
    }
  };
}

for (const routePath of API_ROUTES) {
  app.api(routePath, createApiHandler(routePath, { readOnly: false }), "POST");
  if (READ_API_ROUTES.has(routePath)) {
    app.api(routePath, createApiHandler(routePath, { readOnly: true }), "GET");
  }
}

app.api(
  "/api/workspace-asset",
  async (rawData) => {
    try {
      const data = normalizeApiData(rawData);
      const ws = service.resolveWorkspace({ workspacePath: data.workspacePath || undefined });
      const relPath = String(data.relPath || "");
      const asset = service.readWorkspaceAssetBytes(ws, relPath);
      return new Response(asset.bytes, {
        contentType: asset.mimeType,
        status: 200,
        headers: SEC_HEADERS,
      });
    } catch (err) {
      const status = err instanceof StudioRequestError ? 400 : 404;
      return new Response(JSON.stringify({ error: err instanceof Error ? err.message : "Asset unavailable" }), {
        contentType: "application/json; charset=utf-8",
        status,
        headers: SEC_HEADERS,
      });
    }
  },
  "GET",
);

app.api(
  "/.well-known/agent-card.json",
  () => {
    const port = process.env.ANTIGRAVITY_SIDECAR_WEB_PORT || "0";
    return new Response(JSON.stringify(service.a2a.buildAgentCard(`http://127.0.0.1:${port}`)), {
      contentType: "application/json; charset=utf-8",
      status: 200,
      headers: SEC_HEADERS,
    });
  },
  "GET",
);

app.api(
  "/a2a",
  async (data) => {
    const rpcRes = await service.a2a.handleJsonRpc(data ?? {});
    return new Response(JSON.stringify(rpcRes), {
      contentType: "application/json; charset=utf-8",
      status: 200,
      headers: SEC_HEADERS,
    });
  },
  "POST",
);

async function shutdown() {
  try {
    service.close();
  } catch {
    // Ignore close errors on exit.
  }
  if (typeof app.close === "function") {
    await app.close();
  }
  process.exit(0);
}

process.once("SIGINT", () => void shutdown());
process.once("SIGTERM", () => void shutdown());

await app.run();
