/**
 * Unified backend API service shared across Antigravity `SidecarApp` (`main.mjs`),
 * standalone loopback HTTP + SSE server (`server.mjs`), and VS Code Webview (`extension.mjs`).
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { A2AFacade } from "./a2a.mjs";
import { CatalogBridge, DEFAULT_PLUGIN_ROOT } from "./catalog.mjs";
import { AntigravityCoordinator } from "./coordinator.mjs";
import { CrossHarnessRunner } from "./harness-runner.mjs";
import { buildEntrypointCommand, detectWorkspacePython } from "./python-runner.mjs";
import {
  BundleSnapshotBuilder,
  isInternalSidecarPath,
  ReviewCommentsStore,
  SpecMarkdownReader,
  SpecScaffoldWriter,
  uriToWorkspacePath,
  WorkspaceRegistry,
} from "./snapshot.mjs";

export class StudioRequestError extends Error {}

export class StudioApiService {
  /**
   * @param {{
   *   env?: NodeJS.ProcessEnv,
   *   pluginRoot?: string,
   *   onEvent?: (event: any) => void
   * }} [options]
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
      cwdCandidate && !isInternalSidecarPath(cwdCandidate, this.workspaceRegistry.configPath)
        ? cwdCandidate
        : null;
    this.defaultWorkspace =
      explicitEnvDefault ||
      safeCwd ||
      this.workspaceRegistry.getLastActiveWorkspace() ||
      this.pluginRoot;
    this.catalog = new CatalogBridge({
      pluginRoot: this.pluginRoot,
      workspaceRoot: this.defaultWorkspace,
      dbPath: this.env.FLOW_CATALOG_DB,
      embedder: this.env.FLOW_CATALOG_EMBEDDER,
    });
    this.coordinator = new AntigravityCoordinator(this.env);
    this.harnessRunner = new CrossHarnessRunner({
      defaultWorkspace: this.defaultWorkspace,
      onEvent: (evt) => this.onEvent(evt),
    });
    this.a2a = new A2AFacade(this.harnessRunner);
    /** @type {Set<string>} */
    this.indexedWorkspaces = new Set();
  }

  /**
   * Resolve workspace path from `{ workspaceUri, workspacePath, activeWorkspaceUris }` request payload.
   *
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
        if (candidate && fs.existsSync(candidate)) {
          return candidate;
        }
      }
    }
    const lastActive = this.workspaceRegistry.getLastActiveWorkspace();
    if (lastActive) return lastActive;
    return this.defaultWorkspace;
  }

  /**
   * Handle a named API route and return a JSON-serializable object.
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
        const discovered = await this.coordinator.discoverWorkspaces({
          conversationId: data.conversationId,
        });
        for (const dWs of discovered.workspaces) {
          if (fs.existsSync(dWs)) {
            this.workspaceRegistry.addWorkspace(dWs, { setActive: false });
          }
        }
        if (
          !explicitWs &&
          activeFromClient.length === 0 &&
          discovered.activeWorkspace &&
          fs.existsSync(discovered.activeWorkspace)
        ) {
          this.workspaceRegistry.addWorkspace(discovered.activeWorkspace, { setActive: true });
        }
      }

      const ws =
        explicitWs ||
        activeFromClient[0] ||
        this.workspaceRegistry.getLastActiveWorkspace() ||
        this.defaultWorkspace;
      const workspaces = this.workspaceRegistry.listWorkspaces();
      if (ws && !workspaces.includes(ws)) {
        workspaces.unshift(ws);
      }
      return {
        defaultWorkspace: ws,
        activeWorkspace: ws,
        activeWorkspaces: activeFromClient.length > 0 ? activeFromClient : [ws],
        workspaces,
        antigravityConnected: this.coordinator.available,
        harnesses: this.harnessRunner.detectHarnesses(),
        python: detectWorkspacePython(ws),
      };
    }

    if (routePath === "/api/bundle-snapshot") {
      const ws = this.resolveWorkspace(data);
      if (data.registerWorkspace && fs.existsSync(ws)) {
        this.workspaceRegistry.addWorkspace(ws, { setActive: data.setActive !== false });
      }
      return BundleSnapshotBuilder.build(ws);
    }

    if (routePath === "/api/portfolio-snapshot") {
      const workspaces = this.workspaceRegistry.listWorkspaces();
      const snapshots = workspaces.map((ws) => BundleSnapshotBuilder.build(ws));
      return {
        generatedAt: new Date().toISOString(),
        workspaces: snapshots,
      };
    }

    if (routePath === "/api/spec-document") {
      const ws = this.resolveWorkspace(data);
      if (!data.relPath) {
        throw new StudioRequestError("relPath is required");
      }
      return SpecMarkdownReader.read(ws, String(data.relPath));
    }

    if (routePath === "/api/review-comments") {
      const ws = this.resolveWorkspace(data);
      const store = new ReviewCommentsStore(ws);
      const action = String(data.action || "list");
      const relPath = String(data.relPath || "");
      if (!relPath) {
        throw new StudioRequestError("relPath is required");
      }
      if (action === "add") {
        const comment = store.add({
          relPath,
          startLine: Number(data.startLine) || 1,
          endLine: Number(data.endLine) || Number(data.startLine) || 1,
          quote: data.quote,
          body: String(data.body || ""),
          author: data.author,
        });
        return {
          comment,
          comments: store.list(relPath),
          revisePrompt: store.buildRevisePrompt(relPath, data.flowId),
        };
      }
      if (action === "resolve") {
        const comment = store.setResolved(relPath, String(data.commentId || ""), data.resolved !== false);
        return {
          comment,
          comments: store.list(relPath),
          revisePrompt: store.buildRevisePrompt(relPath, data.flowId),
        };
      }
      return {
        comments: store.list(relPath),
        revisePrompt: store.buildRevisePrompt(relPath, data.flowId),
      };
    }

    if (routePath === "/api/create-spec") {
      const ws = this.resolveWorkspace(data);
      const created = SpecScaffoldWriter.create(ws, {
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

    if (routePath === "/api/catalog-index") {
      const ws = this.resolveWorkspace(data);
      const targets = Array.isArray(data.workspaces) && data.workspaces.length > 0
        ? data.workspaces.map((p) => path.resolve(String(p)))
        : [ws];
      const stats = await this.catalog.index(targets);
      for (const t of targets) this.indexedWorkspaces.add(t);
      return stats;
    }

    if (routePath === "/api/catalog-search") {
      const ws = this.resolveWorkspace(data);
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
      const hits = await this.catalog.provenance({
        file_path: String(data.filePath || ""),
        workspace_id: data.workspaceId || null,
        limit: Number(data.limit) || 20,
      });
      return { hits };
    }

    if (routePath === "/api/catalog-entry") {
      const ws = this.resolveWorkspace(data);
      await this.#ensureWorkspaceIndexed(ws);
      const detail = await this.catalog.entry(String(data.entryId || ""));
      return { detail };
    }

    if (routePath === "/api/catalog-drift") {
      const ws = this.resolveWorkspace(data);
      await this.#ensureWorkspaceIndexed(ws);
      const report = await this.catalog.drift(data.workspaceId || null);
      const facets = await this.catalog.facets();
      return { report, facets };
    }

    if (routePath === "/api/catalog-status") {
      const status = await this.catalog.status();
      const facets = await this.catalog.facets();
      return { status, facets };
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
      return this.coordinator.getModelsAndQuota();
    }

    if (routePath === "/api/trajectories") {
      const ws = this.resolveWorkspace(data);
      return this.coordinator.listTrajectories(ws);
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
        allowConcurrentWrite: data.allowConcurrentWrite !== false,
        wait: Boolean(data.wait),
      });
    }

    if (routePath === "/api/harness-runs") {
      if (data.cancelRunId) {
        return { run: this.harnessRunner.cancelRun(String(data.cancelRunId)) };
      }
      if (data.runId) {
        return { run: this.harnessRunner.getRun(String(data.runId)) };
      }
      return { runs: this.harnessRunner.listRuns() };
    }

    if (routePath === "/api/run-entrypoint") {
      const ws = this.resolveWorkspace(data);
      const entrypoint = String(data.entrypoint || "").trim();
      if (!entrypoint) {
        throw new StudioRequestError("entrypoint is required");
      }
      const extraArgs = Array.isArray(data.args) ? data.args.map(String) : [];
      const cmd = buildEntrypointCommand(ws, entrypoint, extraArgs);
      const output = await runCommandCapture(cmd.command, cmd.args, cmd.cwd);
      return { ...cmd, ...output };
    }

    throw new StudioRequestError(`Unknown API route: ${routePath}`);
  }

  close() {
    this.catalog.close();
  }

  /**
   * @param {string} ws
   */
  async #ensureWorkspaceIndexed(ws) {
    if (this.indexedWorkspaces.has(ws)) return;
    if (!fs.existsSync(path.join(ws, ".agents", "bundles"))) return;
    await this.catalog.index([ws]);
    this.indexedWorkspaces.add(ws);
  }
}

/**
 * Run a short-lived project entrypoint command and capture bounded output.
 *
 * @param {string} command
 * @param {string[]} args
 * @param {string} cwd
 */
function runCommandCapture(command, args, cwd) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd, env: { ...process.env } });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => child.kill("SIGTERM"), 20000);

    child.stdout.on("data", (chunk) => {
      stdout = (stdout + chunk.toString("utf8")).slice(-32000);
    });
    child.stderr.on("data", (chunk) => {
      stderr = (stderr + chunk.toString("utf8")).slice(-32000);
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
