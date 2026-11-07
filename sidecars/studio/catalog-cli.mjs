#!/usr/bin/env node
/**
 * Node CLI wrapper around `CatalogBridge` for shell hooks and cross-harness scripts.
 */

import path from "node:path";
import { CatalogBridge } from "./catalog.mjs";

async function run() {
  const argv = process.argv.slice(2);
  const subcommand = argv[0] || "status";
  const bridge = new CatalogBridge({ workspaceRoot: process.cwd() });

  try {
    if (subcommand === "index") {
      const targets = argv.slice(1).length > 0 ? argv.slice(1) : [process.cwd()];
      const res = await bridge.index(targets.map((p) => path.resolve(p)));
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    } else if (subcommand === "search") {
      const query = argv[1] || "";
      const modeIdx = argv.indexOf("--mode");
      const mode = modeIdx >= 0 && argv[modeIdx + 1] ? argv[modeIdx + 1] : "hybrid";
      const res = await bridge.search({ query, mode });
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    } else if (subcommand === "provenance") {
      const filePath = argv[1] || "";
      const res = await bridge.provenance({ file_path: filePath });
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    } else if (subcommand === "drift") {
      const res = await bridge.drift();
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    } else {
      const res = await bridge.status();
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    }
  } finally {
    bridge.close();
  }
}

run().catch((err) => {
  process.stderr.write(`${JSON.stringify({ error: err.message })}\n`);
  process.exitCode = 1;
});
