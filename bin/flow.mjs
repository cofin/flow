#!/usr/bin/env node
/**
 * First-class `flow` CLI for Flow workflows, specs, Git sync, knowledge hygiene, and agent control.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { AntigravityBridge } from "../sidecars/studio/bridges/antigravity.mjs";
import { CrossHarnessRunner } from "../sidecars/studio/bridges/cli.mjs";
import { CliShimInstaller } from "../sidecars/studio/core/cli-shim.mjs";
import { writeJsonAtomic } from "../sidecars/studio/core/fs-io.mjs";
import { CoAuthorAuditor, PRBodyValidator, StackInspector, StackRestackPlanner } from "../sidecars/studio/core/git-tools.mjs";
import {
  inspectOrBootstrapWorktree,
  syncMainBundleToWorktree,
  syncWorktreeBundleToMain,
} from "../sidecars/studio/core/worktree.mjs";
import { BundleGraph, BundleGraphLinter, TriStateClaimCorrector } from "../sidecars/studio/knowledge/bundle-graph.mjs";
import { CatalogBridge, DEFAULT_PLUGIN_ROOT } from "../sidecars/studio/knowledge/catalog.mjs";
import { DynamicModelCatalog, loadModelCalibrationConfig } from "../sidecars/studio/models/inventory.mjs";
import { HarnessProfileMaterializer } from "../sidecars/studio/models/profiles.mjs";
import { AdaptiveModelRouter, DecisionEngine } from "../sidecars/studio/models/routing.mjs";
import { WorkspaceBundleMigrator } from "../sidecars/studio/spec/bundle-migrator.mjs";
import { SpecFeedbackStore } from "../sidecars/studio/spec/feedback.mjs";
import {
  GitBranchSpecScanner,
  OrphanSpecBranchSync,
  RemoteRepoSpecClient,
  SpecBranchPuller,
  SpecPrPublisher,
} from "../sidecars/studio/spec/git-spec-branch.mjs";
import { ReviewRoster } from "../sidecars/studio/spec/review-roster.mjs";
import { SpecActivity } from "../sidecars/studio/spec/spec-activity.mjs";
import { SpecCloseout } from "../sidecars/studio/spec/spec-closeout.mjs";
import { SpecEngine } from "../sidecars/studio/spec/spec-engine.mjs";
import { TaskPlanner } from "../sidecars/studio/spec/task-planner.mjs";
import { WorkspaceSync } from "../sidecars/studio/spec/workspace-sync.mjs";

const BIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(BIN_DIR, "..");

const HELP_TEXT = `flow — Context-Driven Development CLI

Usage:
  flow sync [--flow <id>] [--dry-run] [--local] [--sync-branch] [--push] [--json]
  flow status [--flow <id>] [--branches] [--json]
  flow spec <list|status|sync|dag|init|import|preflight|claim|complete|phase|pull|pr|share|feedback|closeout|release-claim> [...]
  flow tasks plan --flow <id> [--chapter <ch>] [--briefs] [--workers <n>] [--json]
  flow setup <audit|apply|migrate|compact> [--migrate-specs] [--compact-specs] [--policy shared|local-only] [--json]
  flow catalog <search|index|drift|status|lint|scan|correct> [...]
  flow review plan [--range <r>] [--spec <p>] [--mode auto|single|dual|committee|simplify] [--json]
  flow models <inspect|route|materialize> [...]
  flow agent <list|inspect|send|start> [...]
  flow git <validate-pr-body|stack-check|stack-plan|coauthors> [...]
  flow harness <detect|dispatch|delegate> [...]
  flow worktree <inspect|bootstrap|sync-from-main|sync-to-main> [...]
  flow install-cli [--status] [--json]
`;

const BOOLEAN_FLAGS = new Set([
  "json",
  "dry-run",
  "local",
  "no-local",
  "sync-branch",
  "push",
  "release-stale",
  "no-release-stale",
  "stamp-head",
  "no-stamp-head",
  "all-ready-chapters",
  "briefs",
  "network",
  "cross-vendor",
  "branches",
  "force",
  "draft",
  "confirm-foreign-pr",
  "keep",
  "apply",
  "migrate-specs",
  "compact-specs",
  "approve",
  "request-changes",
  "include-subagents",
  "blocking",
  "app-server",
  "help",
  "status",
  "chapters",
  "worker",
  "finish",
  "clear",
]);

/**
 * Parse CLI flags and positional tokens while preserving `--flag=val` and boolean switches.
 *
 * @param {string[]} args
 */
export function parseFlowFlags(args) {
  /** @type {Record<string, any>} */
  const opts = { _: [] };
  for (let i = 0; i < args.length; i += 1) {
    const a = String(args[i]);
    if (a === "-h") {
      opts.help = true;
      continue;
    }
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
    if (!BOOLEAN_FLAGS.has(stripped) && nxt !== undefined && !String(nxt).startsWith("--")) {
      opts[stripped] = nxt;
      i += 1;
    } else {
      opts[stripped] = true;
    }
  }
  return opts;
}

function splitCsv(val) {
  return String(val || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Render concise human-readable text when `--json` is omitted.
 *
 * @param {string} commandKey
 * @param {any} result
 */
export function formatFlowText(commandKey, result) {
  if (typeof result === "string") return result;
  if (commandKey === "sync" && result && Array.isArray(result.specs)) {
    return WorkspaceSync.renderText(result);
  }
  if (commandKey === "install-cli" && result) {
    if (result.installed) {
      return `Installed flow shim at ${result.shim_path} (on PATH: ${result.on_path ? "yes" : "no"}).`;
    }
    return `flow shim (${result.shim_path || "uninstalled"}): exists=${Boolean(result.installed)}, onPath=${Boolean(result.on_path)}`;
  }
  if (commandKey === "status" && result && Array.isArray(result.specs)) {
    const lines = [`Workspace: ${result.workspace}`];
    for (const s of result.specs) {
      const counts = s.task_counts ? `${s.task_counts.completed}/${s.task_counts.total}` : "0/0";
      lines.push(`- ${s.flow_id} [${s.state}] (${counts}) ${s.title}`);
    }
    if (result.next_runnable) {
      lines.push(`Next: ${result.next_runnable.flow_id} -> ${result.next_runnable.task_id}`);
    }
    if (Array.isArray(result.branch_specs) && result.branch_specs.length > 0) {
      lines.push(`Other branches: ${result.branch_specs.filter((b) => !b.on_current_branch).length} spec(s)`);
    }
    return lines.join("\n");
  }
  return JSON.stringify(result, null, 2);
}

/**
 * Execute one `flow` CLI invocation and return `{ commandKey, data, json }`.
 *
 * @param {string[]} [argv]
 * @param {{ env?: NodeJS.ProcessEnv, cwd?: string }} [ctx]
 */
export async function executeFlowCommand(argv = process.argv.slice(2), ctx = {}) {
  const env = ctx.env || process.env;
  const globalOpts = parseFlowFlags(argv);
  const wantJson = Boolean(globalOpts.json);
  const positionals = globalOpts._;
  const group = positionals[0];

  if (!group || globalOpts.help || group === "help") {
    return { commandKey: "help", data: HELP_TEXT, json: wantJson };
  }

  const ws = path.resolve(String(globalOpts.ws || globalOpts.workspace || globalOpts.root || ctx.cwd || process.cwd()));

  if (group === "install-cli") {
    const installer = new CliShimInstaller({ pluginRoot: PLUGIN_ROOT, env });
    const data = globalOpts.status ? installer.status() : installer.install();
    return { commandKey: "install-cli", data, json: wantJson };
  }

  if (group === "sync") {
    const syncer = new WorkspaceSync(ws, { env });
    const data = await syncer.run({
      flowId: globalOpts.flow || positionals[1] || null,
      chapterId: globalOpts.chapter || null,
      dryRun: Boolean(globalOpts["dry-run"]),
      useGit: !globalOpts["no-local"],
      local: Boolean(globalOpts.local),
      syncBranch: Boolean(globalOpts["sync-branch"] || globalOpts.push),
      pushBranch: Boolean(globalOpts.push),
      releaseStale: !globalOpts["no-release-stale"],
      stampHead: !globalOpts["no-stamp-head"],
      acknowledge: splitCsv(globalOpts.ack),
    });
    return { commandKey: "sync", data, json: wantJson };
  }

  if (group === "status") {
    const engine = new SpecEngine({ workspacePath: ws, env });
    const base = engine.status(globalOpts.flow || positionals[1] || null);
    const live = SpecActivity.overlay(ws, { env });
    let branchSpecs = [];
    if (globalOpts.branches) {
      const scanner = new GitBranchSpecScanner(ws, { env });
      branchSpecs = await scanner.listAllBranchSpecs({
        localSpecs: Array.isArray(base.specs) ? base.specs : [base.spec].filter(Boolean),
      });
    }
    return {
      commandKey: "status",
      data: { ...base, live: live.flows, live_etag: live.live_etag, branch_specs: branchSpecs },
      json: wantJson,
    };
  }

  const action = positionals[1];
  const tail = positionals.slice(2);

  if (group === "spec") {
    if (action === "list") {
      const repo = globalOpts.repo ? String(globalOpts.repo) : null;
      if (repo) {
        const client = new RemoteRepoSpecClient(repo, { workspacePath: ws, env });
        const specs = await client.listSpecs();
        return { commandKey: "spec.list", data: { repo, specs }, json: wantJson };
      }
      const engine = new SpecEngine({ workspacePath: ws, env });
      const localSpecs = engine.listSpecs({ includeArchived: Boolean(globalOpts["include-archived"]) });
      if (globalOpts.branches) {
        const scanner = new GitBranchSpecScanner(ws, { env });
        const branchSpecs = await scanner.listAllBranchSpecs({ localSpecs });
        return { commandKey: "spec.list", data: { specs: branchSpecs }, json: wantJson };
      }
      return { commandKey: "spec.list", data: { specs: localSpecs }, json: wantJson };
    }

    if (action === "status") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      return { commandKey: "spec.status", data: engine.status(globalOpts.flow || tail[0] || null), json: wantJson };
    }

    if (action === "init") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      const initRes = engine.ensureInitialized({ ignorePolicy: globalOpts.policy || null });
      const title = globalOpts.title || globalOpts.flow || tail[0];
      const scaffold = title
        ? engine.scaffold({
            flowId: globalOpts.flow || tail[0] || undefined,
            title,
            kind: globalOpts.kind === "PRD" ? "PRD" : "Spec",
            hasChapters: Boolean(globalOpts.chapters),
          })
        : null;
      return { commandKey: "spec.init", data: { ...initRes, ...(scaffold ? { spec: scaffold } : {}) }, json: wantJson };
    }

    if (action === "preflight") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      const data = engine.preflight(globalOpts.flow || tail[0], {
        chapterId: globalOpts.chapter || null,
        allReadyChapters: Boolean(globalOpts["all-ready-chapters"]),
      });
      return { commandKey: "spec.preflight", data, json: wantJson };
    }

    if (action === "sync") {
      const syncer = new WorkspaceSync(ws, { env });
      const data = await syncer.run({
        flowId: globalOpts.flow || tail[0] || null,
        chapterId: globalOpts.chapter || null,
        dryRun: Boolean(globalOpts["dry-run"]),
        useGit: !globalOpts.local && !globalOpts["no-local"],
        local: Boolean(globalOpts.local),
        syncBranch: Boolean(globalOpts["sync-branch"] || globalOpts.push),
        pushBranch: Boolean(globalOpts.push),
        releaseStale: !globalOpts["no-release-stale"],
        stampHead: !globalOpts["no-stamp-head"],
        acknowledge: splitCsv(globalOpts.ack),
      });
      return { commandKey: "sync", data, json: wantJson };
    }

    if (action === "claim") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      const rawTasks = splitCsv(globalOpts.tasks || tail[1] || "");
      const data = engine.claimTasks({
        flowId: globalOpts.flow || tail[0],
        taskIds: rawTasks,
        chapterId: globalOpts.chapter || null,
        claimedBy: String(globalOpts.by || globalOpts["claimed-by"] || "coordinator:scheduler"),
        releaseStaleClaims: !globalOpts["no-release-stale"],
      });
      return { commandKey: "spec.claim", data, json: wantJson };
    }

    if (action === "complete") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      let completions = [];
      if (globalOpts.payload) {
        const parsed = JSON.parse(String(globalOpts.payload));
        completions = Array.isArray(parsed) ? parsed : [parsed];
      } else if (globalOpts.tasks) {
        completions = splitCsv(globalOpts.tasks).map((taskId) => ({ taskId, commit: globalOpts.commit || null }));
      }
      const data = engine.completeTasks({
        flowId: globalOpts.flow || tail[0],
        completions,
        releaseStaleClaims: !globalOpts["no-release-stale"],
        dryRun: Boolean(globalOpts["dry-run"]),
      });
      return { commandKey: "spec.complete", data, json: wantJson };
    }

    if (action === "phase") {
      const flowId = globalOpts.flow || tail[0];
      const phase = String(globalOpts.phase || tail[1] || "").trim();
      const data = SpecActivity.setPhase(ws, flowId, {
        phase,
        detail: globalOpts.detail ? String(globalOpts.detail) : "",
        env,
      });
      return { commandKey: "spec.phase", data, json: wantJson };
    }

    if (action === "activity") {
      if (globalOpts.finish) {
        const res = SpecActivity.finishTurn(ws, String(globalOpts.conv || ""), { env });
        return { commandKey: "spec.activity", data: res || { finished: true }, json: wantJson };
      }
      if (globalOpts.clear) {
        SpecActivity.clearConversation(ws, String(globalOpts.conv || ""), { env });
        return { commandKey: "spec.activity", data: { cleared: true }, json: wantJson };
      }
      const res = SpecActivity.recordEdit({
        workspace: ws,
        conversationId: String(globalOpts.conv || ""),
        parentConversationId: globalOpts["parent-conv"] ? String(globalOpts["parent-conv"]) : null,
        filePath: String(globalOpts.file || tail[0] || ""),
        tool: String(globalOpts.tool || "edit_file"),
        isWorker: Boolean(globalOpts.worker),
        env,
      });
      return { commandKey: "spec.activity", data: res, json: wantJson };
    }

    if (action === "release-claim") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      const data = engine.releaseClaim({
        flowId: globalOpts.flow || tail[0],
        taskId: String(globalOpts.task || tail[1] || ""),
        chapterId: globalOpts.chapter || null,
      });
      return { commandKey: "spec.release-claim", data, json: wantJson };
    }

    if (action === "import") {
      const engine = new SpecEngine({ workspacePath: ws, env });
      const srcPath = path.resolve(String(globalOpts.from || tail[0]));
      const md = fs.readFileSync(srcPath, "utf8");
      const data = engine.importPlan({
        markdownText: md,
        sourcePath: srcPath,
        flowId: globalOpts.flow || null,
        title: globalOpts.title || null,
      });
      return { commandKey: "spec.import", data, json: wantJson };
    }

    if (action === "dag") {
      if (globalOpts.repo) {
        const client = new RemoteRepoSpecClient(String(globalOpts.repo), { workspacePath: ws, env });
        const review = await client.getSpecReview(String(globalOpts.flow || tail[0]), {
          gitRef: globalOpts["git-ref"] || null,
        });
        return { commandKey: "spec.dag", data: review.dag, json: wantJson };
      }
      const gitRef = globalOpts["git-ref"];
      if (gitRef) {
        const scanner = new GitBranchSpecScanner(ws, { env });
        return { commandKey: "spec.dag", data: await scanner.buildDagFromRef(String(globalOpts.flow || tail[0]), gitRef), json: wantJson };
      }
      const engine = new SpecEngine({ workspacePath: ws, env });
      return { commandKey: "spec.dag", data: engine.buildDag(globalOpts.flow || tail[0]), json: wantJson };
    }

    if (action === "pull") {
      const puller = new SpecBranchPuller(ws, { env });
      const data = await puller.pullSpec(String(globalOpts.flow || tail[0]), {
        fromRef: String(globalOpts.from || globalOpts["git-ref"] || ""),
        force: Boolean(globalOpts.force),
        dryRun: Boolean(globalOpts["dry-run"]),
      });
      return { commandKey: "spec.pull", data, json: wantJson };
    }

    if (action === "share") {
      const orphanSync = new OrphanSpecBranchSync(ws, { env });
      const data = await orphanSync.sync({
        flowId: globalOpts.flow || tail[0] || null,
        push: Boolean(globalOpts.push),
        localOnly: Boolean(globalOpts.local),
      });
      return { commandKey: "spec.share", data, json: wantJson };
    }

    if (action === "pr") {
      const publisher = new SpecPrPublisher(ws, { env });
      const flowId = String(globalOpts.flow || tail[0] || "");
      const subAction = tail[1] || (globalOpts["sync-comments"] ? "comments" : "publish");
      if (subAction === "comments" || globalOpts["sync-comments"]) {
        const data = await publisher.syncPullRequestComments(flowId, {
          prNumber: globalOpts.pr ? Number(globalOpts.pr) : null,
          branch: globalOpts.branch || null,
        });
        return { commandKey: "spec.pr", data, json: wantJson };
      }
      if (subAction === "review" || globalOpts.approve || globalOpts["request-changes"]) {
        const event = globalOpts.approve ? "APPROVE" : globalOpts["request-changes"] ? "REQUEST_CHANGES" : "COMMENT";
        const data = await publisher.publishPullRequestReview(flowId, {
          prNumber: globalOpts.pr ? Number(globalOpts.pr) : null,
          branch: globalOpts.branch || null,
          event,
          commentIds: globalOpts["comment-id"] ? [String(globalOpts["comment-id"])] : null,
          confirmForeignPr: Boolean(globalOpts["confirm-foreign-pr"]),
        });
        return { commandKey: "spec.pr", data, json: wantJson };
      }
      const data = await publisher.publishSpecToPr(flowId, {
        branch: globalOpts.branch || null,
        base: globalOpts.base || null,
        draft: Boolean(globalOpts.draft),
        title: globalOpts.title || null,
        push: Boolean(globalOpts.push),
      });
      return { commandKey: "spec.pr", data, json: wantJson };
    }

    if (action === "feedback") {
      const store = new SpecFeedbackStore(ws, { env });
      const sub = tail[0] || "list";
      const flowId = globalOpts.flow || (sub !== "list" && sub !== "add" && sub !== "reply" && sub !== "resolve" && sub !== "edit" ? sub : tail[1]) || "";
      if (sub === "add") {
        const comment = store.add({
          flowId: globalOpts.flow || undefined,
          relPath: globalOpts["rel-path"] || undefined,
          startLine: Number(globalOpts["start-line"] || 1),
          endLine: Number(globalOpts["end-line"] || globalOpts["start-line"] || 1),
          quote: globalOpts.quote || undefined,
          commentKind: globalOpts.kind || "feedback",
          body: String(globalOpts.body || ""),
          author: globalOpts.author || undefined,
          gitBranch: globalOpts.branch || undefined,
          commitSha: globalOpts.commit || undefined,
        });
        return { commandKey: "spec.feedback", data: { comment }, json: wantJson };
      }
      if (sub === "reply") {
        const comment = store.replyToComment(
          String(globalOpts["rel-path"] || globalOpts.flow || tail[1]),
          String(globalOpts["parent-comment-id"] || globalOpts["comment-id"] || tail[2]),
          {
            body: String(globalOpts.body || ""),
            author: globalOpts.author || undefined,
            commentKind: globalOpts.kind || "feedback",
          },
        );
        return { commandKey: "spec.feedback", data: { comment }, json: wantJson };
      }
      if (sub === "resolve" || sub === "edit") {
        const target = String(globalOpts["rel-path"] || globalOpts.flow || tail[1]);
        const commentId = String(globalOpts["comment-id"] || tail[2]);
        const comment = store.setResolvedOrUpdate(target, commentId, {
          ...(sub === "resolve" ? { resolved: true } : {}),
          ...(globalOpts.state ? { state: String(globalOpts.state) } : {}),
          ...(globalOpts.body !== undefined ? { body: String(globalOpts.body) } : {}),
        });
        return { commandKey: "spec.feedback", data: { comment }, json: wantJson };
      }
      if (globalOpts.repo) {
        const client = new RemoteRepoSpecClient(String(globalOpts.repo), { workspacePath: ws, env });
        const data = await client.getSpecReview(String(flowId));
        return { commandKey: "spec.feedback", data: { flowId, comments: data.comments }, json: wantJson };
      }
      const comments = globalOpts["rel-path"] ? store.list(String(globalOpts["rel-path"])) : store.listForFlow(flowId);
      return { commandKey: "spec.feedback", data: { flowId, comments }, json: wantJson };
    }

    if (action === "closeout") {
      const closeout = new SpecCloseout(ws, { env });
      const data = closeout.run(String(globalOpts.flow || tail[0]), {
        apply: Boolean(globalOpts.apply),
        keep: Boolean(globalOpts.keep),
        verifiedBy: globalOpts["verified-by"] || null,
      });
      return { commandKey: "spec.closeout", data, json: wantJson };
    }

    throw new Error(`Unknown spec action: ${action}`);
  }

  if (group === "tasks") {
    const planner = new TaskPlanner(ws, {
      ...(globalOpts["max-loc"] ? { maxTaskLoc: Number(globalOpts["max-loc"]) } : {}),
      ...(globalOpts["max-files"] ? { maxTaskFiles: Number(globalOpts["max-files"]) } : {}),
      ...(globalOpts.workers ? { workers: Number(globalOpts.workers) } : {}),
    });
    if (action === "plan") {
      const data = planner.plan({
        flowId: globalOpts.flow || tail[0],
        chapterId: globalOpts.chapter || null,
        allReadyChapters: Boolean(globalOpts["all-ready-chapters"]),
        includeBriefs: Boolean(globalOpts.briefs),
        excludeTaskIds: splitCsv(globalOpts["exclude-tasks"]),
        excludePaths: splitCsv(globalOpts["exclude-paths"]),
      });
      return { commandKey: "tasks.plan", data, json: wantJson };
    }
    throw new Error(`Unknown tasks action: ${action}`);
  }

  if (group === "setup") {
    const migrator = new WorkspaceBundleMigrator(ws, { env });
    if (action === "audit") return { commandKey: "setup.audit", data: migrator.audit(), json: wantJson };
    if (action === "compact") {
      return {
        commandKey: "setup.compact",
        data: migrator.compactSpec(String(globalOpts.flow || tail[0]), { dryRun: Boolean(globalOpts["dry-run"]) }),
        json: wantJson,
      };
    }
    if (action === "apply" || action === "migrate") {
      const data = migrator.apply({
        migrateSpecs: action === "migrate" || Boolean(globalOpts["migrate-specs"]),
        compactSpecs: Boolean(globalOpts["compact-specs"]),
        policy: globalOpts.policy || null,
        dryRun: Boolean(globalOpts["dry-run"]),
      });
      return { commandKey: "setup.apply", data, json: wantJson };
    }
    throw new Error(`Unknown setup action: ${action}`);
  }

  if (group === "catalog") {
    const engine = new SpecEngine({ workspacePath: ws, env });
    if (action === "lint" || action === "scan" || action === "correct") {
      const graph = BundleGraph.load(engine.bundleDir, { workspaceRoot: ws });
      if (action === "correct") {
        const plan = TriStateClaimCorrector.plan(graph, {
          claim: String(globalOpts.claim || tail[0] || ""),
          replacement: String(globalOpts.replace || tail[1] || ""),
          canonicalPath: globalOpts.canonical || null,
        });
        const applied = TriStateClaimCorrector.apply(plan, { dryRun: Boolean(globalOpts["dry-run"]) });
        return { commandKey: "catalog.correct", data: applied, json: wantJson };
      }
      const report = BundleGraphLinter.lint(graph);
      return { commandKey: `catalog.${action}`, data: report, json: wantJson };
    }
    const bridge = new CatalogBridge({ pluginRoot: DEFAULT_PLUGIN_ROOT, workspaceRoot: ws });
    try {
      if (action === "search") {
        const data = await bridge.federatedSearch({
          query: String(globalOpts.query || tail[0] || ""),
          planes: splitCsv(globalOpts.planes || "local,siblings"),
          limit: Number(globalOpts.limit || 12),
        });
        return { commandKey: "catalog.search", data, json: wantJson };
      }
      if (action === "index") return { commandKey: "catalog.index", data: await bridge.index([ws]), json: wantJson };
      if (action === "drift") return { commandKey: "catalog.drift", data: await bridge.drift(null), json: wantJson };
      if (action === "status") return { commandKey: "catalog.status", data: await bridge.status(), json: wantJson };
      throw new Error(`Unknown catalog action: ${action}`);
    } finally {
      bridge.close();
    }
  }

  if (group === "review") {
    if (action === "plan") {
      const harness = String(globalOpts.harness || "agy");
      const catalog = new DynamicModelCatalog({ projectRoot: ws });
      const candidates = await catalog.discoverHarnessCatalog({ harness });
      const router = new AdaptiveModelRouter();
      const data = ReviewRoster.plan(ws, {
        range: String(globalOpts.range || "HEAD~1..HEAD"),
        specPath: globalOpts.spec || null,
        mode: String(globalOpts.mode || "auto"),
        harness,
        authorVendor: globalOpts["author-vendor"] || null,
        router: { route: (rOpts) => router.select(candidates, rOpts) },
      });
      return { commandKey: "review.plan", data, json: wantJson };
    }
    throw new Error(`Unknown review action: ${action}`);
  }

  if (group === "models") {
    const catalog = new DynamicModelCatalog({ projectRoot: ws });
    const calibration = loadModelCalibrationConfig({ projectRoot: ws, configPath: globalOpts.config || null });
    const harness = String(globalOpts.harness || "agy");
    let customInventory = null;
    if (globalOpts["models-file"]) {
      customInventory = JSON.parse(fs.readFileSync(path.resolve(String(globalOpts["models-file"])), "utf8"));
    }
    const candidates = await catalog.discoverHarnessCatalog({
      harness,
      customInventory,
      calibration,
      allowNetwork: Boolean(globalOpts.network),
    });

    if (action === "inspect") {
      return { commandKey: "models.inspect", data: { harness, candidate_count: candidates.length, candidates }, json: wantJson };
    }
    if (action === "route") {
      const taskKind = String(globalOpts.kind || globalOpts["task-kind"] || "implementation");
      const engine = new DecisionEngine({
        provider: calibration.decision_provider,
        endpoint: calibration.decision_endpoint,
      });
      const evalRes = await engine.evaluate({
        taskKind,
        filesCount: Number(globalOpts.files ?? 1),
        estimatedLoc: Number(globalOpts.loc ?? 80),
        failedAttempts: Number(globalOpts["failed-attempts"] ?? 0),
        risk: String(globalOpts.risk || "normal"),
      });
      const explicitComplexity =
        globalOpts.complexity !== undefined ? Number(globalOpts.complexity) : evalRes.complexity_rubric;
      const router = new AdaptiveModelRouter({ decisionEngine: engine });
      const route = router.select(candidates, {
        taskKind,
        risk: String(globalOpts.risk || "normal"),
        complexity: explicitComplexity,
        authorVendor: globalOpts["author-vendor"] || null,
        requireVendorDiversity: Boolean(globalOpts["cross-vendor"]),
      });
      return { commandKey: "models.route", data: { ...route, decision: evalRes, route }, json: wantJson };
    }
    if (action === "materialize") {
      const written = HarnessProfileMaterializer.materialize(ws, candidates, {
        harness,
        outDir: globalOpts["out-dir"] || null,
        target: globalOpts.target === "copilot-cli" ? "copilot-cli" : "ide",
      });
      return { commandKey: "models.materialize", data: { harness, written }, json: wantJson };
    }
    throw new Error(`Unknown models action: ${action}`);
  }

  if (group === "agent") {
    const bridge = new AntigravityBridge(env);
    if (action === "list") {
      const data = await bridge.listConversations({
        workspace: globalOpts.workspace || globalOpts.ws ? ws : null,
        status: globalOpts.status || null,
        includeSubagents: Boolean(globalOpts["include-subagents"]),
        limit: Number(globalOpts.limit || 25),
      });
      return { commandKey: "agent.list", data, json: wantJson };
    }
    if (action === "inspect") {
      const convId = String(globalOpts.conv || globalOpts["conversation-id"] || tail[0] || "");
      const data = await bridge.inspectConversation(convId, { steps: Number(globalOpts.steps || 20) });
      return { commandKey: "agent.inspect", data, json: wantJson };
    }
    if (action === "send") {
      const convId = String(globalOpts.conv || globalOpts["conversation-id"] || tail[0] || "");
      const data = await bridge.sendMessage({
        conversationId: convId,
        prompt: String(globalOpts.prompt || tail[1] || ""),
        blocking: Boolean(globalOpts.blocking),
      });
      return { commandKey: "agent.send", data, json: wantJson };
    }
    if (action === "start") {
      const data = await bridge.startWorkspaceConversation({
        workspacePath: ws,
        message: String(globalOpts.prompt || globalOpts.message || tail[0] || ""),
        title: globalOpts.title ? String(globalOpts.title) : undefined,
        preferredModel: globalOpts.model ? String(globalOpts.model) : undefined,
      });
      return { commandKey: "agent.start", data, json: wantJson };
    }
    throw new Error(`Unknown agent action: ${action}`);
  }

  if (group === "git") {
    if (action === "validate-pr-body") {
      const body = globalOpts.from
        ? fs.readFileSync(path.resolve(String(globalOpts.from)), "utf8")
        : String(globalOpts.body || "");
      const data = new PRBodyValidator().validate(String(globalOpts.title || ""), body);
      return { commandKey: "git.validate-pr-body", data, json: wantJson };
    }
    if (action === "stack-check") {
      const data = await new StackInspector(ws).inspect({
        base: globalOpts.base || null,
        branches: splitCsv(globalOpts.branches),
      });
      return { commandKey: "git.stack-check", data, json: wantJson };
    }
    if (action === "stack-plan") {
      const data = await new StackRestackPlanner(ws).plan({
        base: globalOpts.base || null,
        branches: splitCsv(globalOpts.branches),
      });
      return { commandKey: "git.stack-plan", data, json: wantJson };
    }
    if (action === "coauthors") {
      const data = await new CoAuthorAuditor(ws).check({
        base: globalOpts.base || null,
        head: globalOpts.head || "HEAD",
      });
      return { commandKey: "git.coauthors", data, json: wantJson };
    }
    throw new Error(`Unknown git action: ${action}`);
  }

  if (group === "harness") {
    const runner = new CrossHarnessRunner({ defaultWorkspace: ws });
    if (action === "detect") return { commandKey: "harness.detect", data: runner.detectHarnesses(), json: wantJson };
    if (action === "dispatch") {
      const data = await runner.dispatch({
        workspacePath: ws,
        harness: String(globalOpts.harness || tail[0]),
        executionMode: String(globalOpts.mode || "direct-workspace"),
        prompt: String(globalOpts.prompt || tail[1] || ""),
        model: globalOpts.model || null,
        effort: globalOpts.effort || null,
        wait: true,
      });
      return { commandKey: "harness.dispatch", data, json: wantJson };
    }
    if (action === "delegate") {
      const data = await runner.delegate({
        workspacePath: ws,
        harness: globalOpts.harness || null,
        taskKind: String(globalOpts.kind || "semantic_validation"),
        prompt: String(globalOpts.prompt || tail[0] || ""),
        useAppServer: Boolean(globalOpts["app-server"]),
      });
      return { commandKey: "harness.delegate", data, json: wantJson };
    }
    throw new Error(`Unknown harness action: ${action}`);
  }

  if (group === "worktree") {
    if (action === "inspect") return { commandKey: "worktree.inspect", data: inspectOrBootstrapWorktree(ws, { createLinks: false }), json: wantJson };
    if (action === "bootstrap") return { commandKey: "worktree.bootstrap", data: inspectOrBootstrapWorktree(ws, { createLinks: true }), json: wantJson };
    if (action === "sync-from-main") return { commandKey: "worktree.sync-from-main", data: syncMainBundleToWorktree(ws), json: wantJson };
    if (action === "sync-to-main") return { commandKey: "worktree.sync-to-main", data: syncWorktreeBundleToMain(ws), json: wantJson };
    throw new Error(`Unknown worktree action: ${action}`);
  }

  throw new Error(`Unknown command '${group}'. Run 'flow --help' for usage.`);
}

// Keep reference used for CLI helper completeness if needed.
export { writeJsonAtomic };

const isEntrypoint = (() => {
  try {
    return Boolean(process.argv[1]) && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();

if (isEntrypoint) {
  executeFlowCommand(process.argv.slice(2))
    .then(({ commandKey, data, json }) => {
      if (json) {
        process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
      } else {
        const rendered = formatFlowText(commandKey, data);
        process.stdout.write(rendered.endsWith("\n") ? rendered : `${rendered}\n`);
      }
    })
    .catch((err) => {
      const wantJson = process.argv.includes("--json");
      const msg = err instanceof Error ? err.message : String(err);
      if (wantJson) {
        process.stderr.write(`${JSON.stringify({ ok: false, error: msg })}\n`);
      } else {
        process.stderr.write(`flow error: ${msg}\n`);
      }
      process.exit(1);
    });
}
