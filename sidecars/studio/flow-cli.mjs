#!/usr/bin/env node
/**
 * Unified JSON CLI entrypoint for Flow across Node, workflows, hooks, and skills.
 *
 * Subcommands:
 *   flow-cli.mjs spec <status|preflight|sync|import|dag|closeout> [...]
 *   flow-cli.mjs tasks plan --flow <id> [--chapter <ch>] [--briefs] [--ws <dir>]
 *   flow-cli.mjs models <inspect|route|materialize> [...]
 *   flow-cli.mjs review plan [--range <r>] [--spec <p>] [--mode auto|single|dual|committee]
 *   flow-cli.mjs catalog <search|index|drift|status> [...]
 *   flow-cli.mjs harness <detect|dispatch|delegate> [...]
 *   flow-cli.mjs worktree <inspect|bootstrap|sync-from-main|sync-to-main> [--ws <dir>]
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { CrossHarnessRunner } from "./bridges/cli.mjs";
import { inspectOrBootstrapWorktree, syncMainBundleToWorktree, syncWorktreeBundleToMain } from "./core/worktree.mjs";
import { CatalogBridge, DEFAULT_PLUGIN_ROOT } from "./knowledge/catalog.mjs";
import { DynamicModelCatalog, loadModelCalibrationConfig } from "./models/inventory.mjs";
import { HarnessProfileMaterializer } from "./models/profiles.mjs";
import { AdaptiveModelRouter, DecisionEngine } from "./models/routing.mjs";
import { ReviewRoster } from "./spec/review-roster.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";
import { TaskPlanner } from "./spec/task-planner.mjs";

function parseFlags(args) {
  /** @type {Record<string, any>} */
  const opts = { _: [] };
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (!a.startsWith("--")) {
      opts._.push(a);
      continue;
    }
    const stripped = a.slice(2);
    if (stripped.includes("=")) {
      const [k, ...v] = stripped.split("=");
      opts[k] = v.join("=");
      continue;
    }
    const nxt = args[i + 1];
    if (nxt !== undefined && !nxt.startsWith("--")) {
      opts[stripped] = nxt;
      i += 1;
    } else {
      opts[stripped] = true;
    }
  }
  return opts;
}

export async function runFlowCli(argv = process.argv.slice(2)) {
  const [group, action, ...rest] = argv;
  const opts = parseFlags(rest);
  const ws = path.resolve(String(opts.ws || opts.workspace || opts.root || process.cwd()));

  if (group === "spec") {
    const engine = new SpecEngine(ws);
    if (action === "status") return engine.status(opts.flow || opts._[0] || null);
    if (action === "preflight") {
      return engine.preflight(opts.flow || opts._[0], {
        chapterId: opts.chapter || null,
        allReadyChapters: Boolean(opts["all-ready-chapters"]),
      });
    }
    if (action === "sync") {
      return engine.syncChecklists({
        flowId: opts.flow || opts._[0],
        chapterId: opts.chapter || null,
        dryRun: Boolean(opts["dry-run"]),
        releaseStaleClaims: !opts["no-release-stale"],
      });
    }
    if (action === "claim") {
      const rawTasks = String(opts.tasks || opts._[1] || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      return engine.claimTasks({
        flowId: opts.flow || opts._[0],
        taskIds: rawTasks,
        chapterId: opts.chapter || null,
        claimedBy: String(opts.by || opts["claimed-by"] || "coordinator:scheduler"),
        releaseStaleClaims: !opts["no-release-stale"],
      });
    }
    if (action === "complete") {
      let completions = [];
      if (opts.payload) {
        const parsed = JSON.parse(String(opts.payload));
        completions = Array.isArray(parsed) ? parsed : [parsed];
      } else if (opts.tasks) {
        completions = String(opts.tasks)
          .split(",")
          .map((s) => ({ taskId: s.trim(), commit: opts.commit || null }))
          .filter((item) => item.taskId);
      }
      return engine.completeTasks({
        flowId: opts.flow || opts._[0],
        completions,
        releaseStaleClaims: !opts["no-release-stale"],
        dryRun: Boolean(opts["dry-run"]),
      });
    }
    if (action === "import") {
      const srcPath = path.resolve(String(opts.from || opts._[0]));
      const md = fs.readFileSync(srcPath, "utf8");
      return engine.importPlan({
        markdownText: md,
        sourcePath: srcPath,
        flowId: opts.flow || null,
        title: opts.title || null,
      });
    }
    if (action === "dag") return engine.buildDag(opts.flow || opts._[0]);
    if (action === "closeout") {
      return engine.closeout({
        flowId: opts.flow || opts._[0],
        apply: Boolean(opts.apply),
        verifiedBy: opts["verified-by"] || null,
      });
    }
    throw new Error(`Unknown spec action: ${action}`);
  }

  if (group === "tasks") {
    const planner = new TaskPlanner(ws, {
      ...(opts["max-loc"] ? { maxTaskLoc: Number(opts["max-loc"]) } : {}),
      ...(opts["max-files"] ? { maxTaskFiles: Number(opts["max-files"]) } : {}),
      ...(opts.workers ? { workers: Number(opts.workers) } : {}),
    });
    if (action === "plan") {
      const excludeTaskIds = String(opts["exclude-tasks"] || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const excludePaths = String(opts["exclude-paths"] || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      return planner.plan({
        flowId: opts.flow || opts._[0],
        chapterId: opts.chapter || null,
        allReadyChapters: Boolean(opts["all-ready-chapters"]),
        includeBriefs: Boolean(opts.briefs),
        excludeTaskIds,
        excludePaths,
      });
    }
    throw new Error(`Unknown tasks action: ${action}`);
  }

  if (group === "models") {
    const catalog = new DynamicModelCatalog({ projectRoot: ws });
    const calibration = loadModelCalibrationConfig({ projectRoot: ws, configPath: opts.config || null });
    const harness = String(opts.harness || "agy");
    let customInventory = null;
    if (opts["models-file"]) {
      customInventory = JSON.parse(fs.readFileSync(path.resolve(String(opts["models-file"])), "utf8"));
    }
    const candidates = await catalog.discoverHarnessCatalog({
      harness,
      customInventory,
      calibration,
      allowNetwork: Boolean(opts.network),
    });

    if (action === "inspect") {
      return { harness, candidate_count: candidates.length, candidates };
    }
    if (action === "route") {
      const taskKind = String(opts.kind || opts["task-kind"] || "implementation");
      const engine = new DecisionEngine({
        provider: calibration.decision_provider,
        endpoint: calibration.decision_endpoint,
      });
      const evalRes = await engine.evaluate({
        taskKind,
        filesCount: Number(opts.files ?? 1),
        estimatedLoc: Number(opts.loc ?? 80),
        failedAttempts: Number(opts["failed-attempts"] ?? 0),
        risk: String(opts.risk || "normal"),
      });
      const explicitComplexity = opts.complexity !== undefined ? Number(opts.complexity) : evalRes.complexity_rubric;
      const router = new AdaptiveModelRouter({ decisionEngine: engine });
      const route = router.select(candidates, {
        taskKind,
        risk: String(opts.risk || "normal"),
        complexity: explicitComplexity,
        authorVendor: opts["author-vendor"] || null,
        requireVendorDiversity: Boolean(opts["cross-vendor"]),
      });
      return { ...route, decision: evalRes, route };
    }
    if (action === "materialize") {
      const written = HarnessProfileMaterializer.materialize(ws, candidates, {
        harness,
        outDir: opts["out-dir"] || null,
        target: opts.target === "copilot-cli" ? "copilot-cli" : "ide",
      });
      return { harness, written };
    }
    throw new Error(`Unknown models action: ${action}`);
  }

  if (group === "review") {
    if (action === "plan") {
      const harness = String(opts.harness || "agy");
      const catalog = new DynamicModelCatalog({ projectRoot: ws });
      const candidates = await catalog.discoverHarnessCatalog({ harness });
      const router = new AdaptiveModelRouter();
      return ReviewRoster.plan(ws, {
        range: String(opts.range || "HEAD~1..HEAD"),
        specPath: opts.spec || null,
        mode: String(opts.mode || "auto"),
        harness,
        authorVendor: opts["author-vendor"] || null,
        router: { route: (rOpts) => router.select(candidates, rOpts) },
      });
    }
    throw new Error(`Unknown review action: ${action}`);
  }

  if (group === "catalog") {
    const bridge = new CatalogBridge({ pluginRoot: DEFAULT_PLUGIN_ROOT, workspaceRoot: ws });
    try {
      if (action === "search") {
        return await bridge.federatedSearch({
          query: String(opts.query || opts._[0] || ""),
          planes: String(opts.planes || "local,siblings").split(","),
          limit: Number(opts.limit || 12),
        });
      }
      if (action === "index") return await bridge.index([ws]);
      if (action === "drift") return await bridge.drift(null);
      if (action === "status") return await bridge.status();
      throw new Error(`Unknown catalog action: ${action}`);
    } finally {
      bridge.close();
    }
  }

  if (group === "harness") {
    const runner = new CrossHarnessRunner({ defaultWorkspace: ws });
    if (action === "detect") return runner.detectHarnesses();
    if (action === "dispatch") {
      return await runner.dispatch({
        workspacePath: ws,
        harness: String(opts.harness || opts._[0]),
        executionMode: String(opts.mode || "direct-workspace"),
        prompt: String(opts.prompt || opts._[1] || ""),
        model: opts.model || null,
        effort: opts.effort || null,
        wait: true,
      });
    }
    if (action === "delegate") {
      return await runner.delegate({
        workspacePath: ws,
        harness: opts.harness || null,
        taskKind: String(opts.kind || "semantic_validation"),
        prompt: String(opts.prompt || opts._[0] || ""),
        useAppServer: Boolean(opts["app-server"]),
      });
    }
    throw new Error(`Unknown harness action: ${action}`);
  }

  if (group === "worktree") {
    if (action === "inspect") return inspectOrBootstrapWorktree(ws, { createLinks: false });
    if (action === "bootstrap") return inspectOrBootstrapWorktree(ws, { createLinks: true });
    if (action === "sync-from-main") return syncMainBundleToWorktree(ws);
    if (action === "sync-to-main") return syncWorktreeBundleToMain(ws);
    throw new Error(`Unknown worktree action: ${action}`);
  }

  throw new Error(`Unknown flow-cli group '${group}'. Expected spec, tasks, models, review, catalog, harness, or worktree.`);
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
