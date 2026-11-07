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
/** @type {string | null} */
let selectedWorkspaceRoot = null;

function listVscodeWorkspacePaths(vscode) {
  const folders = vscode.workspace?.workspaceFolders;
  if (!Array.isArray(folders)) return [];
  return folders
    .map((f) => (f?.uri?.fsPath ? path.resolve(f.uri.fsPath) : null))
    .filter(Boolean);
}

function resolveUriWorkspaceRoot(vscode, uri) {
  if (!uri?.fsPath) return null;
  if (typeof vscode.workspace?.getWorkspaceFolder === "function") {
    const matched = vscode.workspace.getWorkspaceFolder(uri);
    if (matched?.uri?.fsPath) {
      return path.resolve(matched.uri.fsPath);
    }
  }
  const target = path.resolve(uri.fsPath).replace(/\\/g, "/");
  for (const folderPath of listVscodeWorkspacePaths(vscode)) {
    const normFolder = folderPath.replace(/\\/g, "/").replace(/\/+$/, "");
    if (target === normFolder || target.startsWith(`${normFolder}/`)) {
      return folderPath;
    }
  }
  return null;
}

function resolveActiveEditorWorkspaceRoot(vscode) {
  const activeUri = vscode.window?.activeTextEditor?.document?.uri;
  return resolveUriWorkspaceRoot(vscode, activeUri);
}

function resolveWorkspaceRoot(vscode) {
  if (selectedWorkspaceRoot && fs.existsSync(selectedWorkspaceRoot)) {
    return selectedWorkspaceRoot;
  }
  const editorWs = resolveActiveEditorWorkspaceRoot(vscode);
  if (editorWs) {
    return editorWs;
  }
  const folders = listVscodeWorkspacePaths(vscode);
  if (folders.length > 0) {
    return folders[0];
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
    const docWorkspace = resolveUriWorkspaceRoot(this.vscode, document.uri);
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
        arguments: [{ flowId, workspacePath: docWorkspace }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: curChapter && curChapter !== "null" ? `Implement ${curChapter}` : "Implement Flow",
        command: "flow.dispatchTask",
        arguments: [{ prompt: implCmd, workspacePath: docWorkspace }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: "Zero-Context Review",
        command: "flow.dispatchTask",
        arguments: [{ prompt: `/flow:review ${flowId}`, workspacePath: docWorkspace }],
      }),
    ];
  }
}

function buildWebviewHtml(vscode, webview, initialWorkspace = "") {
  const stylesUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "styles.css")));
  const bridgeUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "host-bridge.js")));
  const appUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "app.js")));
  const logoUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "logo.svg")));
  const faviconUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_ASSETS_DIR, "favicon.svg")));
  const themeBridgeStyle = `<style id="flow-vscode-theme-bridge">
:root,
body.vscode-light,
body.vscode-dark,
body.vscode-high-contrast,
body.vscode-high-contrast-light {
  --flow-bg: var(--vscode-editor-background, var(--background));
  --flow-fg: var(--vscode-editor-foreground, var(--foreground));
  --flow-surface: var(--vscode-editorWidget-background, var(--vscode-sideBar-background, var(--card)));
  --flow-surface-subtle: var(--vscode-input-background, var(--vscode-list-hoverBackground, var(--muted)));
  --flow-muted-fg: var(--vscode-descriptionForeground, var(--vscode-editorLineNumber-foreground, var(--muted-foreground)));
  --flow-line: var(--vscode-panel-border, var(--vscode-widget-border, var(--vscode-editorWidget-border, var(--border))));
  --flow-primary: var(--vscode-button-background, var(--primary));
  --flow-primary-fg: var(--vscode-button-foreground, var(--primary-foreground));
  --flow-highlight: var(--vscode-focusBorder, var(--brand-gold));
  --flow-accent-soft: var(--vscode-list-activeSelectionBackground, rgba(0, 122, 204, 0.18));
  --flow-accent-text: var(--vscode-textLink-foreground, var(--vscode-editor-foreground));
  --flow-ok: var(--vscode-testing-iconPassed, #3fb950);
  --flow-warn: var(--vscode-editorWarning-foreground, #cca700);
  --font-sans: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  --font-mono: var(--vscode-editor-font-family, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
}
</style>`;
  const rawHtml = fs.readFileSync(path.join(STUDIO_ASSETS_DIR, "index.html"), "utf8");
  const initScript = `<script>window.__FLOW_LOGO_URI__ = "${logoUri}"; window.__FLOW_INITIAL_WORKSPACE__ = ${JSON.stringify(initialWorkspace || "")};</script>`;
  return rawHtml
    .replace('<script src="/preload.js"></script>', initScript)
    .replace('href="/favicon.svg"', `href="${faviconUri}"`)
    .replace('<link rel="shortcut icon" href="/favicon.ico">', "")
    .replace('href="/styles.css"', `href="${stylesUri}"`)
    .replace("</head>", `${themeBridgeStyle}\n</head>`)
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
  selectedWorkspaceRoot =
    resolveActiveEditorWorkspaceRoot(vscode) || listVscodeWorkspacePaths(vscode)[0] || process.cwd();
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

  const registerOpenWorkspaceFolders = () => {
    if (!activeApiService) return;
    const allFolders = listVscodeWorkspacePaths(vscode);
    for (const folder of allFolders) {
      if (fs.existsSync(folder)) {
        activeApiService.workspaceRegistry.addWorkspace(folder, {
          setActive: folder === selectedWorkspaceRoot,
        });
      }
    }
    if (selectedWorkspaceRoot && fs.existsSync(selectedWorkspaceRoot)) {
      activeApiService.workspaceRegistry.addWorkspace(selectedWorkspaceRoot, { setActive: true });
    }
  };
  registerOpenWorkspaceFolders();

  const specsTree = new SpecsTreeProvider(vscode);
  const catalogTree = new CatalogTreeProvider(vscode);

  const syncActiveWorkspace = (nextWorkspacePath, notifyWebview = true) => {
    if (!nextWorkspacePath) return;
    const resolved = path.resolve(nextWorkspacePath);
    if (!fs.existsSync(resolved)) return;
    const changed = resolved !== selectedWorkspaceRoot;
    selectedWorkspaceRoot = resolved;
    registerOpenWorkspaceFolders();
    if (changed) {
      specsTree.refresh();
      catalogTree.refresh();
    }
    if (notifyWebview && activePanel?.webview) {
      const allFolders = listVscodeWorkspacePaths(vscode);
      const orderedUris = [resolved, ...allFolders.filter((w) => w !== resolved)];
      activePanel.webview.postMessage({
        type: "studioEvent",
        event: {
          type: "workspace.changed",
          workspacePath: resolved,
          uris: orderedUris,
        },
      });
    }
  };

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("flowSpecsTree", specsTree),
    vscode.window.registerTreeDataProvider("flowCatalogTree", catalogTree),
    vscode.languages.registerCodeLensProvider({ language: "markdown", scheme: "file" }, new SpecCodeLensProvider(vscode))
  );

  if (typeof vscode.window?.onDidChangeActiveTextEditor === "function") {
    context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        const nextWs = resolveUriWorkspaceRoot(vscode, editor?.document?.uri);
        if (nextWs && nextWs !== selectedWorkspaceRoot) {
          syncActiveWorkspace(nextWs, true);
        }
      })
    );
  }

  if (typeof vscode.workspace?.onDidChangeWorkspaceFolders === "function") {
    context.subscriptions.push(
      vscode.workspace.onDidChangeWorkspaceFolders(() => {
        registerOpenWorkspaceFolders();
        const folders = listVscodeWorkspacePaths(vscode);
        const nextWs =
          (selectedWorkspaceRoot && folders.includes(selectedWorkspaceRoot)
            ? selectedWorkspaceRoot
            : null) ||
          resolveActiveEditorWorkspaceRoot(vscode) ||
          folders[0];
        if (nextWs) {
          syncActiveWorkspace(nextWs, true);
        } else {
          specsTree.refresh();
          catalogTree.refresh();
        }
      })
    );
  }

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
    vscode.commands.registerCommand("flow.openStudio", async (arg) => {
      const targetWs = arg?.workspacePath || resolveActiveEditorWorkspaceRoot(vscode) || resolveWorkspaceRoot(vscode);
      if (targetWs) {
        syncActiveWorkspace(targetWs, Boolean(activePanel));
      }
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
      panel.webview.html = buildWebviewHtml(vscode, panel.webview, resolveWorkspaceRoot(vscode));
      panel.onDidDispose(() => {
        activePanel = null;
      });
      panel.webview.onDidReceiveMessage(async (msg) => {
        if (!msg || typeof msg !== "object" || !activeApiService) return;
        if (msg.type === "apiRequest") {
          try {
            const reqPayload = { ...(msg.payload || {}) };
            const currentWs = resolveWorkspaceRoot(vscode);
            const allFolders = listVscodeWorkspacePaths(vscode);
            if (!reqPayload.activeWorkspaceUris && currentWs) {
              reqPayload.activeWorkspaceUris = [
                currentWs,
                ...allFolders.filter((w) => w !== currentWs),
              ];
            }
            if (
              msg.routePath === "/api/bundle-snapshot" &&
              typeof reqPayload.workspacePath === "string" &&
              reqPayload.workspacePath.trim()
            ) {
              syncActiveWorkspace(reqPayload.workspacePath.trim(), false);
            }
            const result = await activeApiService.handleApi(msg.routePath, reqPayload);
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
          const targetDispatchWs = msg.workspacePath || resolveWorkspaceRoot(vscode);
          if (targetDispatchWs) {
            syncActiveWorkspace(targetDispatchWs, false);
          }
          await routePromptToHostHarness(
            vscode,
            activeApiService,
            targetDispatchWs,
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
      const targetWs = arg?.workspacePath || resolveWorkspaceRoot(vscode);
      if (targetWs) {
        syncActiveWorkspace(targetWs, true);
      }
      await routePromptToHostHarness(vscode, activeApiService, targetWs, prompt);
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
  selectedWorkspaceRoot = null;
}
