#!/usr/bin/env node
/**
 * Command-line interface for CrossHarnessRunner used by workflows and terminal automation.
 */

import path from "node:path";
import { CrossHarnessRunner } from "./harness-runner.mjs";

async function main() {
  const argv = process.argv.slice(2);
  const sub = argv[0] || "detect";
  const runner = new CrossHarnessRunner({ defaultWorkspace: process.cwd() });

  if (sub === "detect") {
    process.stdout.write(`${JSON.stringify({ harnesses: runner.detectHarnesses() }, null, 2)}\n`);
    return;
  }

  if (sub === "dispatch") {
    const harness = argv[1] || "";
    const modeIdx = argv.indexOf("--mode");
    const executionMode = modeIdx >= 0 && argv[modeIdx + 1] ? argv[modeIdx + 1] : "direct-workspace";
    const wsIdx = argv.indexOf("--workspace");
    const workspacePath = wsIdx >= 0 && argv[wsIdx + 1] ? path.resolve(argv[wsIdx + 1]) : process.cwd();
    const promptIdx = argv.indexOf("--prompt");
    const prompt = promptIdx >= 0 && argv[promptIdx + 1] ? argv[promptIdx + 1] : argv.slice(2).join(" ");

    const res = await runner.dispatch({
      workspacePath,
      harness,
      executionMode: /** @type {any} */ (executionMode),
      prompt,
      wait: true,
    });
    process.stdout.write(`${JSON.stringify(res, null, 2)}\n`);
    if (res.status === "failed") process.exitCode = 1;
    return;
  }

  throw new Error(`Unknown harness-cli subcommand: ${sub}`);
}

main().catch((err) => {
  process.stderr.write(`${JSON.stringify({ error: err.message })}\n`);
  process.exitCode = 1;
});
