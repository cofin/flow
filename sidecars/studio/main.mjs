/**
 * Google Antigravity Sidecar SDK entrypoint for Flow Studio.
 *
 * Serves the compact pinned Flow Companion (`AuxPane` at `/`) and full-bleed
 * Flow Studio (`Sidebar` at `/dashboard`) alongside JSON API routes.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Response, SidecarApp } from "sidecar_sdk";

import { StudioApiService, StudioRequestError } from "./router.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(STUDIO_DIR, "..", "..");

const SEC_HEADERS = {
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "no-store",
};

const HTML_HEADERS = {
  ...SEC_HEADERS,
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'",
};

const INDEX_HTML = fs.readFileSync(path.join(STUDIO_DIR, "index.html"), "utf8");
const STYLES_CSS = fs.readFileSync(path.join(STUDIO_DIR, "styles.css"), "utf8");
const HOST_BRIDGE_JS = fs.readFileSync(path.join(STUDIO_DIR, "host-bridge.js"), "utf8");
const APP_JS = fs.readFileSync(path.join(STUDIO_DIR, "app.js"), "utf8");
const LOGO_SVG = fs.readFileSync(path.join(STUDIO_DIR, "logo.svg"), "utf8");
const FAVICON_SVG = fs.readFileSync(path.join(STUDIO_DIR, "favicon.svg"), "utf8");
const FAVICON_ICO = fs.readFileSync(path.join(STUDIO_DIR, "favicon.ico"));

const service = new StudioApiService({ env: process.env, pluginRoot: PLUGIN_ROOT });
const app = new SidecarApp();

const staticAsset = (body, contentType, headers = SEC_HEADERS) => () =>
  new Response(body, { contentType, status: 200, headers });

app.page("/", staticAsset(INDEX_HTML, "text/html; charset=utf-8", HTML_HEADERS));
app.page("/dashboard", staticAsset(INDEX_HTML, "text/html; charset=utf-8", HTML_HEADERS));
app.page("/styles.css", staticAsset(STYLES_CSS, "text/css; charset=utf-8"));
app.page("/host-bridge.js", staticAsset(HOST_BRIDGE_JS, "application/javascript; charset=utf-8"));
app.page("/app.js", staticAsset(APP_JS, "application/javascript; charset=utf-8"));
app.page("/logo.svg", staticAsset(LOGO_SVG, "image/svg+xml"));
app.page("/favicon.svg", staticAsset(FAVICON_SVG, "image/svg+xml"));
app.page("/favicon.ico", staticAsset(FAVICON_ICO, "image/x-icon"));

const API_ROUTES = [
  "/api/studio-context",
  "/api/bundle-snapshot",
  "/api/portfolio-snapshot",
  "/api/spec-document",
  "/api/review-comments",
  "/api/create-spec",
  "/api/catalog-index",
  "/api/catalog-search",
  "/api/catalog-provenance",
  "/api/catalog-entry",
  "/api/catalog-drift",
  "/api/catalog-status",
  "/api/start-workspace-conversation",
  "/api/models-and-quota",
  "/api/trajectories",
  "/api/harnesses",
  "/api/harness-dispatch",
  "/api/harness-runs",
  "/api/run-entrypoint",
];

for (const routePath of API_ROUTES) {
  app.api(
    routePath,
    async (data) => {
      try {
        const result = await service.handleApi(routePath, data ?? {});
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
    },
    "POST"
  );
}

app.api(
  "/.well-known/agent-card.json",
  () => {
    const port = process.env.ANTIGRAVITY_SIDECAR_WEB_PORT || "0";
    const card = service.a2a.buildAgentCard(`http://127.0.0.1:${port}`);
    return new Response(JSON.stringify(card), {
      contentType: "application/json; charset=utf-8",
      status: 200,
      headers: SEC_HEADERS,
    });
  },
  "GET"
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
  "POST"
);

await app.run();
