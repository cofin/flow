#!/usr/bin/env node
/**
 * Standalone loopback HTTP + SSE + A2A v1 server (`npx flow-studio`).
 *
 * Serves the exact same calm Flow Studio UI and DuckDB catalog backend for
 * Claude Code, Codex CLI, OpenCode V2, Cursor, and browser workflows without
 * requiring an Antigravity host process.
 */

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { StudioApiService, StudioRequestError } from "./router.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
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

/** @type {Set<http.ServerResponse>} */
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
    // Recursive fs.watch is best-effort across OS filesystems.
  }
}

/**
 * @param {any} payload
 */
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

/**
 * @param {http.IncomingMessage} req
 * @returns {Promise<Record<string, any>>}
 */
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
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Connection": "keep-alive",
      "Cache-Control": "no-cache",
    });
    res.write(`data: ${JSON.stringify({ type: "connected", workspacePath: defaultWorkspace })}\n\n`);
    sseClients.add(res);
    req.on("close", () => sseClients.delete(res));
    return;
  }

  if (req.method === "GET" && pathname === "/.well-known/agent-card.json") {
    const addr = server.address();
    const port = typeof addr === "object" && addr ? addr.port : requestedPort;
    const card = service.a2a.buildAgentCard(`http://127.0.0.1:${port}`);
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(card));
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
      res.end(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }));
    }
    return;
  }

  if (req.method === "GET" && STATIC_FILES.has(pathname)) {
    const entry = STATIC_FILES.get(pathname);
    const assetPath = path.join(STUDIO_DIR, entry.file);
    const content = entry.binary ? fs.readFileSync(assetPath) : fs.readFileSync(assetPath, "utf8");
    res.writeHead(200, { "Content-Type": entry.type });
    res.end(content);
    return;
  }

  if (req.method === "POST" && pathname.startsWith("/api/")) {
    try {
      const payload = await readJsonBody(req);
      const output = await service.handleApi(pathname, payload);
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(output));
    } catch (err) {
      const status = err instanceof StudioRequestError ? 400 : 500;
      const msg = err instanceof Error ? err.message : "Internal Studio error";
      res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: msg }));
    }
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify({ error: `Not found: ${pathname}` }));
});

server.listen(requestedPort, "127.0.0.1", () => {
  const addr = server.address();
  const actualPort = typeof addr === "object" && addr ? addr.port : requestedPort;
  process.stdout.write(
    `Flow Studio listening on http://127.0.0.1:${actualPort}/dashboard (workspace: ${defaultWorkspace})\n`
  );
});

const shutdown = () => {
  service.close();
  server.close(() => process.exit(0));
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
