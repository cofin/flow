/**
 * Unified backend API service shared across Antigravity `SidecarApp`, standalone loopback HTTP/SSE server,
 * and VS Code / Cursor Webview (`vscode-extension/extension.mjs`).
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { A2AFacade } from "./a2a.mjs";
import { ActivityMonitor } from "./activity-monitor.mjs";
import { AntigravityBridge } from "./bridges/antigravity.mjs";
import { CrossHarnessRunner } from "./bridges/cli.mjs";
import { buildEntrypointCommand, detectWorkspacePython } from "./bridges/python.mjs";
import { isInternalSidecarPath, sha1Hex, uriToWorkspacePath } from "./core/fs-io.mjs";
import { CatalogBridge, DEFAULT_PLUGIN_ROOT } from "./knowledge/catalog.mjs";
import { DynamicModelCatalog } from "./models/inventory.mjs";
import { AdaptiveModelRouter, DecisionEngine } from "./models/routing.mjs";
import { BundleSnapshotBuilder } from "./snapshot.mjs";
import { ReviewRoster } from "./spec/review-roster.mjs";
import { TaskPlanner } from "./spec/task-planner.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";
import { WorkspacePermissionAdvisor, WorkspaceRegistry } from "./workspaces.mjs";

export class StudioRequestError extends Error {}

export class StudioApiService {
  /**
   * @param {{ env?: NodeJS.ProcessEnv, pluginRoot?: string, onEvent?: (event: any) => void }} [options]
   */
  constructor(options = {}) {
    this.env = options.env || process.env;
    this.pluginRoot = path.resolve(options.pluginRoot || DEFAULT_PLUGIN_ROOT);
    this.onEvent = options.onEvent || (() => {});

    const explicitEnvDefault = this.env.FLOW_STUDIO_DEFAULT_WORKSPACE
      ? path.resolve(this.env.FLOW_STUDIO_DEFAULT_WORKSPACE)
      : null;
    const cwdCandidate = process.cwd() ? path.resolve(process.cwd()) : null;
    this.workspaceRegistry = new WorkspaceRegistry(explicitEnvDefault || cwdCandidate, {
      env: this.env,
      explicitDefault: Boolean(explicitEnvDefault),
    });
    const safeCwd =
      cwdCandidate && !isInternalSidecarPath(cwdCandidate) ? cwdCandidate : null;
    this.defaultWorkspace =
      explicitEnvDefault || safeCwd || this.workspaceRegistry.getLastActiveWorkspace() || this.pluginRoot;

    this.catalog = new CatalogBridge({
      pluginRoot: this.pluginRoot,
      workspaceRoot: this.defaultWorkspace,
      dbPath: this.env.FLOW_CATALOG_DB,
      embedder: this.env.FLOW_CATALOG_EMBEDDER,
    });
    this.coordinator = new AntigravityBridge(this.env);
    this.harnessRunner = new CrossHarnessRunner({
      defaultWorkspace: this.defaultWorkspace,
      env: this.env,
      onEvent: (evt) => this.onEvent(evt),
    });
    this.a2a = new A2AFacade(this.harnessRunner);
    this.activityMonitor = new ActivityMonitor({
      env: this.env,
      antigravityBridge: this.coordinator,
      codexBridge: this.harnessRunner.codexBridge,
      cliRunner: this.harnessRunner,
    });
    /** @type {Set<string>} */
    this.indexedWorkspaces = new Set();
  }

  /**
   * Ingest live VS Code / Copilot chat model metadata into the shared catalog.
   *
   * @param {any[]} chatModels
   * @returns {Promise<any[]>}
   */
  async ingestVsCodeChatModels(chatModels) {
    this.harnessRunner.modelCatalog.ingestVsCodeChatModels(chatModels);
    return this.harnessRunner.modelCatalog.discoverHarnessCatalog({ harness: "vscode" });
  }

  /**
   * @param {Record<string, any>} data
   */
  resolveWorkspace(data = {}) {
    if (typeof data.workspaceUri === "string" && data.workspaceUri.trim()) {
      if (!data.workspaceUri.startsWith("file:")) {
        throw new StudioRequestError("workspaceUri must start with file://");
      }
      try {
        return path.resolve(fileURLToPath(data.workspaceUri));
      } catch {
        throw new StudioRequestError("Invalid file:// workspaceUri");
      }
    }
    if (typeof data.workspacePath === "string" && data.workspacePath.trim()) {
      return path.resolve(data.workspacePath.trim());
    }
    if (Array.isArray(data.activeWorkspaceUris) && data.activeWorkspaceUris.length > 0) {
      for (const raw of data.activeWorkspaceUris) {
        const candidate = uriToWorkspacePath(raw);
        if (candidate && fs.existsSync(candidate)) return candidate;
      }
    }
    return this.workspaceRegistry.getLastActiveWorkspace() || this.defaultWorkspace;
  }

  /**
   * Handle a named API route and return a JSON-serializable response.
   *
   * @param {string} routePath
   * @param {Record<string, any>} [data]
   */
  async handleApi(routePath, data = {}) {
    if (routePath === "/api/studio-context") {
      const hasExplicitWs =
        (typeof data.workspaceUri === "string" && data.workspaceUri.trim()) ||
        (typeof data.workspacePath === "string" && data.workspacePath.trim());
      const explicitWs = hasExplicitWs ? this.resolveWorkspace(data) : null;
      const activeFromClient = Array.isArray(data.activeWorkspaceUris)
        ? this.workspaceRegistry.recordActiveWorkspaces(data.activeWorkspaceUris)
        : [];
      if (explicitWs && fs.existsSync(explicitWs)) {
        this.workspaceRegistry.addWorkspace(explicitWs, { setActive: true });
      }
      if (this.coordinator.available) {
        const discovered = await this.coordinator.discoverWorkspaces({ conversationId: data.conversationId });
        for (const dWs of discovered.workspaces) {
          if (fs.existsSync(dWs)) this.workspaceRegistry.addWorkspace(dWs, { setActive: false });
        }
        if (!explicitWs && activeFromClient.length === 0 && discovered.activeWorkspace && fs.existsSync(discovered.activeWorkspace)) {
          this.workspaceRegistry.addWorkspace(discovered.activeWorkspace, { setActive: true });
        }
      }

      const ws =
        explicitWs || activeFromClient[0] || this.workspaceRegistry.getLastActiveWorkspace() || this.defaultWorkspace;
      const workspaces = this.workspaceRegistry.listWorkspaces();
      if (ws && !workspaces.includes(ws)) workspaces.unshift(ws);

      return {
        defaultWorkspace: ws,
        activeWorkspace: ws,
        activeWorkspaces: activeFromClient.length > 0 ? activeFromClient : [ws],
        workspaces,
        pinnedWorkspaces: this.workspaceRegistry.listPinnedWorkspaces(),
        antigravityConnected: this.coordinator.available,
        harnesses: this.harnessRunner.detectHarnesses(),
        python: detectWorkspacePython(ws),
      };
    }

    if (routePath === "/api/pin-workspace") {
      const ws = this.resolveWorkspace(data);
      const pinned = this.workspaceRegistry.setPinned(ws, data.pinned !== false);
      return { pinnedWorkspaces: pinned, workspaces: this.workspaceRegistry.listWorkspaces() };
    }

    if (routePath === "/api/bundle-snapshot") {
      const ws = this.resolveWorkspace(data);
      if (data.registerWorkspace && fs.existsSync(ws)) {
        this.workspaceRegistry.addWorkspace(ws, { setActive: data.setActive !== false });
      }
      const snap = BundleSnapshotBuilder.build(ws);
      const contentEtag = sha1Hex(JSON.stringify({ specs: snap.specs, knowledge: snap.knowledge, counts: snap.counts }));
      return { ...snap, contentEtag };
    }

    if (routePath === "/api/portfolio-snapshot") {
      const workspaces = this.workspaceRegistry.listWorkspaces();
      const snapshots = workspaces.map((ws) => BundleSnapshotBuilder.build(ws));
      return { generatedAt: new Date().toISOString(), workspaces: snapshots };
    }

    if (routePath === "/api/spec-document") {
      const ws = this.resolveWorkspace(data);
      if (!data.relPath) throw new StudioRequestError("relPath is required");
      return new SpecEngine(ws).readDocument(String(data.relPath));
    }

    if (routePath === "/api/spec-dag") {
      const ws = this.resolveWorkspace(data);
      if (!data.flowId) throw new StudioRequestError("flowId is required");
      const engine = new SpecEngine(ws);
      const dag = engine.buildDag(String(data.flowId));
      const plan = new TaskPlanner(ws).plan({ flowId: String(data.flowId), chapterId: data.chapterId || null });
      return { ...dag, steps: plan.steps, inline_fast_path_eligible: plan.inline_fast_path_eligible };
    }

    if (routePath === "/api/spec-review") {
      const ws = this.resolveWorkspace(data);
      if (!data.flowId) throw new StudioRequestError("flowId is required");
      return new SpecEngine(ws).getSpecReview(String(data.flowId));
    }

    if (routePath === "/api/review-comments") {
      const ws = this.resolveWorkspace(data);
      const engine = new SpecEngine(ws);
      const store = engine.feedback;
      const action = String(data.action || "list");
      const relPath = String(data.relPath || "");
      const flowId = data.flowId ? String(data.flowId) : store.inferFlowId(relPath);
      if (!relPath && !flowId) throw new StudioRequestError("relPath or flowId is required");

      if (action === "add") {
        const comment = store.add({
          relPath: relPath || undefined,
          flowId: flowId || undefined,
          chapterId: data.chapterId || undefined,
          taskId: data.taskId || undefined,
          startLine: Number(data.startLine) || 1,
          endLine: Number(data.endLine) || Number(data.startLine) || 1,
          quote: data.quote,
          quotedText: data.quote,
          commentKind: data.commentKind || "feedback",
          body: String(data.body || ""),
          author: data.author,
          authorEmail: data.authorEmail,
          authorName: data.authorName,
        });
        const list = relPath ? store.list(relPath) : store.listForFlow(flowId);
        return { comment, comments: list, revisePrompt: store.buildRevisePrompt(relPath || flowId, flowId) };
      }
      if (action === "resolve" || action === "update") {
        const comment = store.setResolvedOrUpdate(relPath || flowId, String(data.commentId || ""), {
          ...(data.resolved !== undefined ? { resolved: data.resolved !== false } : {}),
          ...(data.state !== undefined ? { state: data.state } : {}),
          ...(data.body !== undefined ? { body: data.body } : {}),
          ...(data.toggleUpvote !== undefined ? { toggleUpvote: Boolean(data.toggleUpvote) } : {}),
        });
        const list = relPath ? store.list(relPath) : store.listForFlow(flowId);
        return { comment, comments: list, revisePrompt: store.buildRevisePrompt(relPath || flowId, flowId) };
      }
      const list = relPath ? store.list(relPath) : store.listForFlow(flowId);
      return { comments: list, revisePrompt: store.buildRevisePrompt(relPath || flowId, flowId) };
    }

    if (routePath === "/api/create-spec") {
      const ws = this.resolveWorkspace(data);
      const created = new SpecEngine(ws).scaffold({
        flowId: String(data.flowId || ""),
        title: String(data.title || ""),
        kind: data.kind === "PRD" ? "PRD" : "Spec",
        problem: data.problem,
        goals: data.goals,
        parentPrd: data.parentPrd,
        hasChapters: Boolean(data.hasChapters),
      });
      this.indexedWorkspaces.delete(ws);
      this.onEvent({ type: "spec.created", workspacePath: ws, spec: created });
      return created;
    }

    if (routePath === "/api/import-plan") {
      const ws = this.resolveWorkspace(data);
      return new SpecEngine(ws).importPlan({
        markdownText: String(data.markdownText || ""),
        sourcePath: data.sourcePath || null,
        flowId: data.flowId || null,
        title: data.title || null,
      });
    }

    if (routePath === "/api/catalog-index") {
      const ws = this.resolveWorkspace(data);
      const targets =
        Array.isArray(data.workspaces) && data.workspaces.length > 0 ? data.workspaces.map((p) => path.resolve(String(p))) : [ws];
      const stats = await this.catalog.index(targets);
      for (const t of targets) this.indexedWorkspaces.add(t);
      return stats;
    }

    if (routePath === "/api/catalog-search") {
      const ws = this.resolveWorkspace(data);
      if (data.mode === "federated") {
        const fedBridge = new CatalogBridge({ pluginRoot: this.pluginRoot, workspaceRoot: ws });
        const hits = await fedBridge.federatedSearch({
          query: String(data.query || ""),
          planes: Array.isArray(data.planes) ? data.planes : ["local", "siblings"],
          limit: Number(data.limit) || 20,
        });
        fedBridge.close();
        return { hits, status: { mode: "federated" } };
      }
      await this.#ensureWorkspaceIndexed(ws);
      const hits = await this.catalog.search({
        query: String(data.query || ""),
        mode: String(data.mode || "hybrid"),
        workspace_id: data.workspaceId || null,
        concept_type: data.conceptType || null,
        trust_tier: data.trustTier || null,
        limit: Number(data.limit) || 20,
      });
      const status = await this.catalog.status();
      return { hits, status };
    }

    if (routePath === "/api/catalog-provenance") {
      const ws = this.resolveWorkspace(data);
      await this.#ensureWorkspaceIndexed(ws);
      return { hits: await this.catalog.provenance({ file_path: String(data.filePath || ""), workspace_id: data.workspaceId || null, limit: Number(data.limit) || 20 }) };
    }

    if (routePath === "/api/catalog-entry") {
      const ws = this.resolveWorkspace(data);
      await this.#ensureWorkspaceIndexed(ws);
      return { detail: await this.catalog.entry(String(data.entryId || "")) };
    }

    if (routePath === "/api/catalog-drift") {
      const ws = this.resolveWorkspace(data);
      await this.#ensureWorkspaceIndexed(ws);
      return { report: await this.catalog.drift(data.workspaceId || null), facets: await this.catalog.facets() };
    }

    if (routePath === "/api/catalog-status") {
      return { status: await this.catalog.status(), facets: await this.catalog.facets() };
    }

    if (routePath === "/api/start-workspace-conversation") {
      const ws = this.resolveWorkspace(data);
      return this.coordinator.startWorkspaceConversation({
        workspacePath: ws,
        message: String(data.message || ""),
        title: data.title ? String(data.title) : undefined,
        preferredModel: data.preferredModel ? String(data.preferredModel) : undefined,
      });
    }

    if (routePath === "/api/models-and-quota") {
      const ws = this.resolveWorkspace(data);
      const agyData = await this.coordinator.getModelsAndQuota();
      const dynamicCatalog = this.harnessRunner.modelCatalog;
      dynamicCatalog.projectRoot = ws;
      const harnessIds = ["agy", "claude", "codex", "opencode", "cursor-agent", "vscode"];
      /** @type {Record<string, any>} */
      const byHarness = {};
      const router = new AdaptiveModelRouter();
      const engine = new DecisionEngine();

      for (const hid of harnessIds) {
        const candidates = await dynamicCatalog.discoverHarnessCatalog({
          harness: hid,
          antigravityCatalog: hid === "agy" ? agyData : null,
        });
        byHarness[hid] = {
          candidateCount: candidates.length,
          candidates: candidates.slice(0, 12),
          recommendations: {
            strong: router.select(candidates, { taskKind: "planning", risk: "high" }),
            standard: router.select(candidates, { taskKind: "implementation", risk: "normal" }),
            light: router.select(candidates, { taskKind: "sync", risk: "low" }),
          },
        };
      }
      return {
        ...agyData,
        decisionProvider: engine.provider,
        dynamicByHarness: byHarness,
      };
    }

    if (routePath === "/api/review-plan") {
      const ws = this.resolveWorkspace(data);
      const harness = String(data.harness || "agy");
      const candidates = await this.harnessRunner.modelCatalog.discoverHarnessCatalog({ harness });
      const router = new AdaptiveModelRouter();
      return ReviewRoster.plan(ws, {
        range: String(data.range || "HEAD~1..HEAD"),
        specPath: data.specPath || null,
        mode: String(data.mode || "auto"),
        harness,
        authorVendor: data.authorVendor || null,
        router: { route: (rOpts) => router.select(candidates, rOpts) },
      });
    }

    if (routePath === "/api/trajectories") {
      return this.coordinator.listTrajectories(this.resolveWorkspace(data));
    }

    if (routePath === "/api/activity") {
      return this.activityMonitor.snapshot(this.resolveWorkspace(data));
    }

    if (routePath === "/api/permissions") {
      const advisor = new WorkspacePermissionAdvisor(this.resolveWorkspace(data));
      if (data.action === "apply") {
        return advisor.apply({
          allowGrants: Array.isArray(data.allowGrants) ? data.allowGrants : [],
          denyGrants: Array.isArray(data.denyGrants) ? data.denyGrants : [],
          enableHook: Boolean(data.enableHook),
        });
      }
      return advisor.inspect();
    }

    if (routePath === "/api/harnesses") {
      const ws = this.resolveWorkspace(data);
      return {
        harnesses: this.harnessRunner.detectHarnesses(),
        writerGuard: this.harnessRunner.checkActiveWriter(ws),
        runs: this.harnessRunner.listRuns(),
      };
    }

    if (routePath === "/api/harness-dispatch") {
      const ws = this.resolveWorkspace(data);
      return this.harnessRunner.dispatch({
        workspacePath: ws,
        harness: String(data.harness || ""),
        executionMode: data.executionMode || "direct-workspace",
        prompt: String(data.prompt || ""),
        model: data.model ? String(data.model) : undefined,
        effort: data.effort ? String(data.effort) : undefined,
        allowConcurrentWrite: data.allowConcurrentWrite !== false,
        wait: Boolean(data.wait),
      });
    }

    if (routePath === "/api/harness-delegate") {
      const ws = this.resolveWorkspace(data);
      return this.harnessRunner.delegate({
        workspacePath: ws,
        harness: data.harness || null,
        taskKind: String(data.taskKind || "semantic_validation"),
        prompt: String(data.prompt || ""),
        authorVendor: data.authorVendor || null,
        useAppServer: Boolean(data.useAppServer),
      });
    }

    if (routePath === "/api/harness-runs") {
      if (data.cancelRunId) return { run: this.harnessRunner.cancelRun(String(data.cancelRunId)) };
      if (data.runId) return { run: this.harnessRunner.getRun(String(data.runId)) };
      return { runs: this.harnessRunner.listRuns() };
    }

    if (routePath === "/api/run-entrypoint") {
      const ws = this.resolveWorkspace(data);
      const entrypoint = String(data.entrypoint || "").trim();
      if (!entrypoint) throw new StudioRequestError("entrypoint is required");
      const extraArgs = Array.isArray(data.args) ? data.args.map(String) : [];
      const cmd = buildEntrypointCommand(ws, entrypoint, extraArgs);
      const output = await runCommandCapture(cmd.command, cmd.args, cmd.cwd);
      return { ...cmd, ...output };
    }

    throw new StudioRequestError(`Unknown API route: ${routePath}`);
  }

  close() {
    this.catalog.close();
    this.harnessRunner.codexBridge?.close();
  }

  async #ensureWorkspaceIndexed(ws) {
    if (this.indexedWorkspaces.has(ws)) return;
    if (!fs.existsSync(path.join(ws, ".agents", "bundles"))) return;
    await this.catalog.index([ws]);
    this.indexedWorkspaces.add(ws);
  }
}

function runCommandCapture(command, args, cwd) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd, env: { ...process.env } });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => child.kill("SIGTERM"), 20000);
    child.stdout.on("data", (c) => {
      stdout = (stdout + c.toString("utf8")).slice(-32000);
    });
    child.stderr.on("data", (c) => {
      stderr = (stderr + c.toString("utf8")).slice(-32000);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ exitCode: code ?? 0, stdout, stderr });
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ exitCode: 1, stdout, stderr: err.message });
    });
  });
}
