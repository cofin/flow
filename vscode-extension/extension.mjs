/**
 * Flow Studio multi-harness extension for VS Code and Cursor.
 *
 * Shares the core `StudioApiService`, `BundleSnapshotBuilder`, `CrossHarnessRunner`,
 * and `detectWorkspacePython` modules directly with the Antigravity sidecar (`sidecars/studio/`).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildEntrypointCommand, detectWorkspacePython } from "../sidecars/studio/python-runner.mjs";
import { StudioApiService } from "../sidecars/studio/router.mjs";
import { BundleSnapshotBuilder } from "../sidecars/studio/snapshot.mjs";

const EXT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(EXT_DIR, "..");
const STUDIO_ASSETS_DIR = path.join(PLUGIN_ROOT, "sidecars", "studio");

/** @type {StudioApiService | null} */
let activeApiService = null;
/** @type {any} */
let activePanel = null;

function resolveWorkspaceRoot(vscode) {
  const folders = vscode.workspace?.workspaceFolders;
  if (Array.isArray(folders) && folders.length > 0 && folders[0]?.uri?.fsPath) {
    return folders[0].uri.fsPath;
  }
  return process.cwd();
}

class SpecsTreeProvider {
  constructor(vscode) {
    this.vscode = vscode;
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.emitter.event;
  }

  refresh() {
    this.emitter.fire(undefined);
  }

  getTreeItem(element) {
    return element;
  }

  async getChildren(element) {
    const ws = resolveWorkspaceRoot(this.vscode);
    const snap = BundleSnapshotBuilder.build(ws);
    if (!snap.bundleInitialized) {
      const empty = new this.vscode.TreeItem("No .agents/bundles found — run /flow:setup", this.vscode.TreeItemCollapsibleState.None);
      empty.command = { command: "flow.openStudio", title: "Open Flow Studio" };
      return [empty];
    }

    if (!element) {
      return snap.specs.map((spec) => {
        const hasChildren = (spec.chapters?.length || 0) > 0 || (spec.tasks?.length || 0) > 0;
        const item = new this.vscode.TreeItem(
          `${spec.title} (${spec.state})`,
          hasChildren ? this.vscode.TreeItemCollapsibleState.Expanded : this.vscode.TreeItemCollapsibleState.None
        );
        item.description = `${spec.completedTasks}/${spec.totalTasks} tasks`;
        item.contextValue = "flowSpec";
        item.flowSpec = spec;
        item.command = {
          command: "flow.openStudio",
          title: "Open in Flow Studio",
          arguments: [{ flowId: spec.flowId, relPath: spec.relPath }],
        };
        return item;
      });
    }

    if (element.flowSpec) {
      const spec = element.flowSpec;
      if (Array.isArray(spec.chapters) && spec.chapters.length > 0) {
        return spec.chapters.map((ch) => {
          const hasTasks = Array.isArray(ch.tasks) && ch.tasks.length > 0;
          const chItem = new this.vscode.TreeItem(
            `${ch.chapterId} (${ch.state})`,
            hasTasks ? this.vscode.TreeItemCollapsibleState.Collapsed : this.vscode.TreeItemCollapsibleState.None
          );
          chItem.description = `${ch.completedTasks}/${ch.totalTasks} tasks`;
          chItem.flowChapter = ch;
          chItem.flowId = spec.flowId;
          return chItem;
        });
      }
      return (spec.tasks || []).map((t) => this.#buildTaskItem(ws, t));
    }

    if (element.flowChapter) {
      return (element.flowChapter.tasks || []).map((t) => this.#buildTaskItem(ws, t));
    }

    return [];
  }

  #buildTaskItem(ws, task) {
    const item = new this.vscode.TreeItem(
      `${task.shortId}: ${task.title}`,
      this.vscode.TreeItemCollapsibleState.None
    );
    item.description = task.state;
    const absPath = path.join(ws, task.relPath);
    item.command = {
      command: "vscode.open",
      title: "Open Task Worksheet",
      arguments: [this.vscode.Uri.file(absPath)],
    };
    return item;
  }
}

class CatalogTreeProvider {
  constructor(vscode) {
    this.vscode = vscode;
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.emitter.event;
  }

  refresh() {
    this.emitter.fire(undefined);
  }

  getTreeItem(element) {
    return element;
  }

  async getChildren(element) {
    const ws = resolveWorkspaceRoot(this.vscode);
    const snap = BundleSnapshotBuilder.build(ws);
    if (!snap.bundleInitialized) return [];

    if (!element) {
      const docs = snap.knowledge || [];
      return docs.map((doc) => {
        const item = new this.vscode.TreeItem(doc.title, this.vscode.TreeItemCollapsibleState.None);
        item.description = doc.type || doc.section;
        const absPath = path.join(ws, doc.relPath);
        item.command = {
          command: "vscode.open",
          title: "Open Knowledge Entry",
          arguments: [this.vscode.Uri.file(absPath)],
        };
        return item;
      });
    }
    return [];
  }
}

class SpecCodeLensProvider {
  constructor(vscode) {
    this.vscode = vscode;
  }

  async provideCodeLenses(document) {
    const fsPath = String(document?.uri?.fsPath || "").replace(/\\/g, "/");
    if (!fsPath.includes("/.agents/bundles/specs/") || !fsPath.endsWith("/spec.md")) {
      return [];
    }
    const text = typeof document.getText === "function" ? document.getText() : "";
    const flowId = text.match(/^flow_id:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() || "spec";
    const curChapter = text.match(/^current_chapter:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() || "";
    const topRange = new this.vscode.Range(0, 0, 0, 0);

    const implCmd = curChapter && curChapter !== "null"
      ? `/flow:implement ${flowId} ${curChapter}`
      : `/flow:implement ${flowId}`;

    return [
      new this.vscode.CodeLens(topRange, {
        title: "Open in Flow Studio",
        command: "flow.openStudio",
        arguments: [{ flowId }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: curChapter && curChapter !== "null" ? `Implement ${curChapter}` : "Implement Flow",
        command: "flow.dispatchTask",
        arguments: [{ prompt: implCmd }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: "Zero-Context Review",
        command: "flow.dispatchTask",
        arguments: [{ prompt: `/flow:review ${flowId}` }],
      }),
    ];
  }
}

function buildWebviewHtml(vscode, webview) {
  const stylesUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "styles.css")));
  const bridgeUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "host-bridge.js")));
  const appUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "app.js")));
  const logoUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "logo.svg")));
  const faviconUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "favicon.svg")));
  const rawHtml = fs.readFileSync(path.join(STUDIO_ASSETS_DIR, "index.html"), "utf8");
  return rawHtml
    .replace('<script src="/preload.js"></script>', `<script>window.__FLOW_LOGO_URI__ = "${logoUri}";</script>`)
    .replace('href="/favicon.svg"', `href="${faviconUri}"`)
    .replace('<link rel="shortcut icon" href="/favicon.ico">', "")
    .replace('href="/styles.css"', `href="${stylesUri}"`)
    .replace('src="/host-bridge.js"', `src="${bridgeUri}"`)
    .replace('src="/app.js"', `src="${appUri}"`);
}

async function routePromptToHostHarness(vscode, apiService, workspacePath, prompt, overrideMode) {
  const cfg = vscode.workspace.getConfiguration("flow");
  const defaultHarness = cfg.get("defaultHarness", "copilot");
  const executionMode = overrideMode || cfg.get("executionMode", "direct-workspace");

  if (defaultHarness === "copilot" || defaultHarness === "cursor") {
    await vscode.commands.executeCommand("workbench.action.chat.open", { query: prompt });
    return;
  }

  await apiService.handleApi("/api/harness-dispatch", {
    workspacePath,
    harness: defaultHarness,
    executionMode,
    prompt,
  });
}

/**
 * Core activation routine accepting an injected `vscode` module (for testability and runtime use).
 *
 * @param {any} context
 * @param {any} vscode
 */
export async function activateWithVscode(context, vscode) {
  const wsRoot = resolveWorkspaceRoot(vscode);
  const cfg = vscode.workspace.getConfiguration("flow");
  const customDb = cfg.get("catalogDbPath", "");

  activeApiService = new StudioApiService({
    pluginRoot: PLUGIN_ROOT,
    env: {
      ...process.env,
      FLOW_STUDIO_DEFAULT_WORKSPACE: wsRoot,
      ...(customDb ? { FLOW_CATALOG_DB: customDb } : {}),
    },
    onEvent: (event) => {
      if (activePanel?.webview) {
        activePanel.webview.postMessage({ type: "studioEvent", event });
      }
    },
  });

  const specsTree = new SpecsTreeProvider(vscode);
  const catalogTree = new CatalogTreeProvider(vscode);

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("flowSpecsTree", specsTree),
    vscode.window.registerTreeDataProvider("flowCatalogTree", catalogTree),
    vscode.languages.registerCodeLensProvider({ language: "markdown", scheme: "file" }, new SpecCodeLensProvider(vscode))
  );

  const watcher = vscode.workspace.createFileSystemWatcher("**/.agents/**");
  watcher.onDidChange(() => {
    specsTree.refresh();
    catalogTree.refresh();
  });
  watcher.onDidCreate(() => {
    specsTree.refresh();
    catalogTree.refresh();
  });
  watcher.onDidDelete(() => {
    specsTree.refresh();
    catalogTree.refresh();
  });
  context.subscriptions.push(watcher);

  context.subscriptions.push(
    vscode.commands.registerCommand("flow.openStudio", async () => {
      if (activePanel) {
        activePanel.reveal(vscode.ViewColumn.One);
        return;
      }
      const panel = vscode.window.createWebviewPanel(
        "flowStudio",
        "Flow Studio",
        vscode.ViewColumn.One,
        {
          enableScripts: true,
          retainContextWhenHidden: true,
          localResourceRoots: [vscode.Uri.file(STUDIO_ASSETS_DIR)],
        }
      );
      activePanel = panel;
      panel.webview.html = buildWebviewHtml(vscode, panel.webview);
      panel.onDidDispose(() => {
        activePanel = null;
      });
      panel.webview.onDidReceiveMessage(async (msg) => {
        if (!msg || typeof msg !== "object" || !activeApiService) return;
        if (msg.type === "apiRequest") {
          try {
            const result = await activeApiService.handleApi(msg.routePath, msg.payload || {});
            await panel.webview.postMessage({ type: "apiResponse", id: msg.id, result });
          } catch (err) {
            await panel.webview.postMessage({
              type: "apiResponse",
              id: msg.id,
              error: err instanceof Error ? err.message : String(err),
            });
          }
          return;
        }
        if (msg.type === "dispatchPrompt") {
          await routePromptToHostHarness(
            vscode,
            activeApiService,
            msg.workspacePath || resolveWorkspaceRoot(vscode),
            String(msg.message || ""),
            msg.executionMode
          );
          return;
        }
        if (msg.type === "openFile" && msg.absPath) {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(msg.absPath));
          await vscode.window.showTextDocument(doc);
        }
      });
    }),

    vscode.commands.registerCommand("flow.newSpec", async () => {
      await vscode.commands.executeCommand("flow.openStudio");
    }),

    vscode.commands.registerCommand("flow.searchCatalog", async () => {
      const query = await vscode.window.showInputBox({ prompt: "Search local Flow Knowledge Catalog (Hybrid BM25 + Vector)" });
      if (!query || !activeApiService) return;
      const res = await activeApiService.handleApi("/api/catalog-search", {
        workspacePath: resolveWorkspaceRoot(vscode),
        query,
        mode: "hybrid",
      });
      const hits = res.hits || [];
      if (hits.length === 0) {
        await vscode.window.showInformationMessage(`No catalog matches for "${query}".`);
        return;
      }
      const picked = await vscode.window.showQuickPick(
        hits.map((h) => ({
          label: h.title,
          description: `${h.concept_type} · ${h.rel_path}`,
          detail: h.description,
          hit: h,
        }))
      );
      if (picked?.hit) {
        const abs = path.join(picked.hit.workspace_path, picked.hit.rel_path);
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(abs));
        await vscode.window.showTextDocument(doc);
      }
    }),

    vscode.commands.registerCommand("flow.dispatchTask", async (arg) => {
      const prompt = arg?.prompt || (await vscode.window.showInputBox({ prompt: "Enter Flow command or prompt to dispatch" }));
      if (!prompt || !activeApiService) return;
      await routePromptToHostHarness(vscode, activeApiService, resolveWorkspaceRoot(vscode), prompt);
    }),

    vscode.commands.registerCommand("flow.runEntrypoint", async () => {
      const ws = resolveWorkspaceRoot(vscode);
      const py = detectWorkspacePython(ws);
      const scripts = Object.keys(py.projectScripts || {});
      if (scripts.length === 0) {
        await vscode.window.showInformationMessage(`Detected Python runner: ${py.runner} (no [project.scripts] declared).`);
        return;
      }
      const picked = await vscode.window.showQuickPick(scripts.map((s) => ({ label: s, description: `Run via ${py.runner}` })));
      if (!picked) return;
      const spec = buildEntrypointCommand(ws, picked.label, ["--help"]);
      const term = vscode.window.createTerminal({ name: `Flow: ${picked.label}`, cwd: spec.cwd });
      term.show();
      term.sendText([spec.command, ...spec.args].join(" "));
    }),

    vscode.commands.registerCommand("flow.selectTargetHarness", async () => {
      const choices = ["copilot", "cursor", "claude", "codex", "opencode", "agy"];
      const picked = await vscode.window.showQuickPick(choices.map((c) => ({ label: c })));
      if (picked) {
        await vscode.workspace.getConfiguration("flow").update("defaultHarness", picked.label, true);
      }
    })
  );
}

export async function activate(context) {
  const vscode = await import("vscode");
  return activateWithVscode(context, vscode.default ?? vscode);
}

export async function deactivate() {
  if (activeApiService) {
    activeApiService.close();
    activeApiService = null;
  }
  activePanel = null;
}
