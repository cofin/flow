#!/usr/bin/env node
/**
 * Standalone loopback HTTP + SSE + A2A v1 server (`npx --yes --package github:cofin/flow flow-studio`).
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { StudioApiService, StudioRequestError } from "./router.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(STUDIO_DIR, "web");
const PLUGIN_ROOT = path.resolve(STUDIO_DIR, "..", "..");

const STATIC_FILES = new Map([
  ["/", { file: "index.html", type: "text/html; charset=utf-8" }],
  ["/dashboard", { file: "index.html", type: "text/html; charset=utf-8" }],
  ["/styles.css", { file: "styles.css", type: "text/css; charset=utf-8" }],
  ["/host-bridge.js", { file: "host-bridge.js", type: "application/javascript; charset=utf-8" }],
  ["/app.js", { file: "app.js", type: "application/javascript; charset=utf-8" }],
  ["/logo.svg", { file: "logo.svg", type: "image/svg+xml" }],
  ["/favicon.svg", { file: "favicon.svg", type: "image/svg+xml" }],
  ["/favicon.ico", { file: "favicon.ico", type: "image/x-icon", binary: true }],
]);

const argv = process.argv.slice(2);
const portArgIdx = argv.indexOf("--port");
const requestedPort =
  portArgIdx >= 0 && argv[portArgIdx + 1]
    ? Number(argv[portArgIdx + 1])
    : Number(process.env.FLOW_STUDIO_PORT || 4319);
const wsArgIdx = argv.indexOf("--workspace");
const defaultWorkspace =
  wsArgIdx >= 0 && argv[wsArgIdx + 1]
    ? path.resolve(argv[wsArgIdx + 1])
    : path.resolve(process.env.FLOW_STUDIO_DEFAULT_WORKSPACE || process.cwd());

const sseClients = new Set();
const service = new StudioApiService({
  env: { ...process.env, FLOW_STUDIO_DEFAULT_WORKSPACE: defaultWorkspace },
  pluginRoot: PLUGIN_ROOT,
  onEvent: (event) => broadcastSse(event),
});

const agentsDir = path.join(defaultWorkspace, ".agents");
let fsWatchTimer = null;
if (fs.existsSync(agentsDir)) {
  try {
    fs.watch(agentsDir, { recursive: true }, () => {
      if (fsWatchTimer) clearTimeout(fsWatchTimer);
      fsWatchTimer = setTimeout(() => {
        service.indexedWorkspaces.delete(defaultWorkspace);
        broadcastSse({ type: "bundle.changed", workspacePath: defaultWorkspace });
      }, 250);
    });
  } catch {
    // Recursive fs.watch is best-effort.
  }
}

function broadcastSse(payload) {
  const frame = `data: ${JSON.stringify(payload)}\n\n`;
  for (const res of sseClients) {
    try {
      res.write(frame);
    } catch {
      sseClients.delete(res);
    }
  }
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on("data", (chunk) => {
      total += chunk.length;
      if (total > 4 * 1024 * 1024) {
        reject(new StudioRequestError("Request payload exceeds 4 MiB limit"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8").trim();
      if (!raw) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new StudioRequestError("Malformed JSON request body"));
      }
    });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
  const pathname = urlObj.pathname;

  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Cache-Control", "no-store");

  if (req.method === "GET" && pathname === "/preload.js") {
    res.writeHead(200, { "Content-Type": "application/javascript; charset=utf-8" });
    res.end("window.__FLOW_STANDALONE__ = true;\n");
    return;
  }

  if (req.method === "GET" && pathname === "/api/events") {
    res.writeHead(200, { "Content-Type": "text/event-stream; charset=utf-8", Connection: "keep-alive" });
    res.write(": connected\n\n");
    sseClients.add(res);
    req.on("close", () => sseClients.delete(res));
    return;
  }

  if (req.method === "GET" && pathname === "/.well-known/agent-card.json") {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(service.a2a.buildAgentCard(`http://127.0.0.1:${requestedPort}`)));
    return;
  }

  if (req.method === "GET" && pathname === "/api/workspace-asset") {
    try {
      const ws = service.resolveWorkspace({ workspacePath: urlObj.searchParams.get("workspacePath") || undefined });
      const relPath = urlObj.searchParams.get("relPath") || "";
      const asset = service.readWorkspaceAssetBytes(ws, relPath);
      res.writeHead(200, { "Content-Type": asset.mimeType, "Content-Length": String(asset.bytes.length) });
      res.end(asset.bytes);
    } catch (err) {
      const status = err instanceof StudioRequestError ? 400 : 404;
      res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Asset unavailable" }));
    }
    return;
  }

  if (req.method === "GET" && STATIC_FILES.has(pathname)) {
    const asset = STATIC_FILES.get(pathname);
    const fullPath = path.join(WEB_DIR, asset.file);
    if (pathname === "/" || pathname === "/dashboard") {
      res.setHeader(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
          "img-src 'self' data: blob:; media-src 'self' data: blob:; " +
          "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'",
      );
    }
    res.writeHead(200, { "Content-Type": asset.type });
    res.end(asset.binary ? fs.readFileSync(fullPath) : fs.readFileSync(fullPath, "utf8"));
    return;
  }

  if (req.method === "POST" && pathname === "/a2a") {
    try {
      const body = await readJsonBody(req);
      const rpcRes = await service.a2a.handleJsonRpc(body);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(rpcRes));
    } catch (err) {
      res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Bad A2A request" }));
    }
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/")) {
    try {
      const body = await readJsonBody(req);
      const result = await service.handleApi(pathname, body);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(result));
    } catch (err) {
      const status = err instanceof StudioRequestError ? 400 : 500;
      res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Studio error" }));
    }
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(requestedPort, "127.0.0.1", () => {
  const url = `http://127.0.0.1:${requestedPort}/dashboard`;
  process.stdout.write(`Flow Studio running at ${url} (workspace: ${defaultWorkspace})\n`);
  const shouldOpen = argv.includes("--open") && !argv.includes("--no-open");
  if (shouldOpen) {
    const opener = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
    const openArgs = process.platform === "win32" ? ["/c", "start", "", url] : [url];
    try {
      spawn(opener, openArgs, { detached: true, stdio: "ignore" }).unref();
    } catch {
      // Ignore headless browser open failures.
    }
  }
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    service.close();
    server.close(() => process.exit(0));
  });
}
