#!/usr/bin/env node
/**
 * Backward-compatible JSON CLI wrapper forwarding to `bin/flow.mjs`.
 */

import fs from "node:fs";
import { fileURLToPath } from "node:url";

import { executeFlowCommand } from "../../bin/flow.mjs";

/**
 * Execute a CLI command with legacy JSON output semantics.
 *
 * @param {string[]} [argv]
 */
export async function runFlowCli(argv = process.argv.slice(2)) {
  const { data } = await executeFlowCommand([...argv, "--json"]);
  return data;
}

const isEntrypoint = (() => {
  try {
    return Boolean(process.argv[1]) && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();

if (isEntrypoint) {
  runFlowCli()
    .then((res) => {
      process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    })
    .catch((err) => {
      process.stderr.write(`${JSON.stringify({ ok: false, error: err instanceof Error ? err.message : String(err) })}\n`);
      process.exit(1);
    });
}
