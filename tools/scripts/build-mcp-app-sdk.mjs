#!/usr/bin/env node
/**
 * Build the self-contained browser IIFE bundle for `@modelcontextprotocol/ext-apps`
 * (`sidecars/studio/web/mcp-ext-apps.bundle.js`) using an ephemeral temp directory so the
 * plugin repository keeps zero runtime `node_modules`.
 */

import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..");
const OUT_FILE = path.join(REPO_ROOT, "sidecars", "studio", "web", "mcp-ext-apps.bundle.js");

const ENTRY_SRC = `
import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
} from "@modelcontextprotocol/ext-apps";

const PASSTHROUGH_SCHEMA = {
  safeParse(data) {
    return { success: true, data };
  },
  parse(data) {
    return data;
  },
};

async function toggleAuxPaneFile(app, uri) {
  return app.request(
    {
      method: "com.google.antigravity/toggle-aux-pane",
      params: { tabType: "fileView", uri },
    },
    PASSTHROUGH_SCHEMA,
  );
}

globalThis.__MCP_EXT_APPS__ = {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
  toggleAuxPaneFile,
};
`;

function hasBinary(name) {
  const res = spawnSync(name, ["--version"], { stdio: "ignore" });
  return res.status === 0;
}

const env = {
  ...process.env,
  NPM_CONFIG_REGISTRY: process.env.NPM_CONFIG_REGISTRY || "https://registry.npmjs.org",
};

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-mcp-ext-apps-"));
try {
  fs.writeFileSync(
    path.join(tmpDir, "package.json"),
    JSON.stringify({ name: "flow-mcp-sdk-build", private: true, type: "module" }, null, 2),
    "utf8",
  );
  fs.writeFileSync(path.join(tmpDir, "entry.js"), ENTRY_SRC, "utf8");

  if (hasBinary("bun")) {
    execFileSync("bun", ["add", "@modelcontextprotocol/ext-apps"], {
      cwd: tmpDir,
      env,
      stdio: "inherit",
    });
    execFileSync(
      "bun",
      [
        "build",
        path.join(tmpDir, "entry.js"),
        "--target=browser",
        "--format=iife",
        "--minify",
        `--outfile=${OUT_FILE}`,
      ],
      { cwd: tmpDir, env, stdio: "inherit" },
    );
  } else {
    execFileSync(
      "npm",
      ["install", "--no-audit", "--no-fund", "@modelcontextprotocol/ext-apps", "esbuild"],
      { cwd: tmpDir, env, stdio: "inherit" },
    );
    const esbuildBin = path.join(
      tmpDir,
      "node_modules",
      ".bin",
      process.platform === "win32" ? "esbuild.cmd" : "esbuild",
    );
    execFileSync(
      esbuildBin,
      [
        path.join(tmpDir, "entry.js"),
        "--bundle",
        "--format=iife",
        "--platform=browser",
        "--target=es2022",
        "--minify",
        `--outfile=${OUT_FILE}`,
      ],
      { cwd: tmpDir, env, stdio: "inherit" },
    );
  }

  const stat = fs.statSync(OUT_FILE);
  process.stdout.write(`Built ${path.relative(REPO_ROOT, OUT_FILE)} (${stat.size} bytes)\n`);
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}
