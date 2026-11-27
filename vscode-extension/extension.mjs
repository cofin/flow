/**
 * Editor-native Flow extension for VS Code, Cursor, Windsurf, and Positron.
 *
 * Provides native inline spec review threads (`vscode.comments.createCommentController`)
 * synced to `SpecFeedbackStore` and `/flow:revise`, an active-flow Status Bar item,
 * a cached Specs & Tasks Activity Bar tree, actionable `spec.md` CodeLenses,
 * instant pure-Node bundle search, and an optional CSP-hardened Flow Studio webview.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildEntrypointCommand, detectWorkspacePython } from "../sidecars/studio/bridges/python.mjs";
import { toPosixRelative } from "../sidecars/studio/core/fs-io.mjs";
import { HarnessProfileMaterializer } from "../sidecars/studio/models/profiles.mjs";
import { StudioApiService } from "../sidecars/studio/router.mjs";
import { BundleSnapshotBuilder } from "../sidecars/studio/snapshot.mjs";
import { SpecFeedbackStore } from "../sidecars/studio/spec/feedback.mjs";

const EXT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(EXT_DIR, "..");
const BUNDLED_STUDIO_DIR = path.join(EXT_DIR, "sidecars", "studio");
const STUDIO_ASSETS_DIR = fs.existsSync(BUNDLED_STUDIO_DIR)
  ? BUNDLED_STUDIO_DIR
  : path.join(PLUGIN_ROOT, "sidecars", "studio");
const STUDIO_WEB_DIR = fs.existsSync(path.join(STUDIO_ASSETS_DIR, "web"))
  ? path.join(STUDIO_ASSETS_DIR, "web")
  : STUDIO_ASSETS_DIR;

const REVIEWABLE_MD_RE = /\/\.agents\/bundles\/(specs|knowledge|research)\/.*\.md$/i;

/** @type {StudioApiService | null} */
let activeApiService = null;
/** @type {any} */
let activePanel = null;
/** @type {boolean} */
let webviewReady = false;
/** @type {any[]} */
let pendingWebviewMessages = [];
/** @type {string | null} */
let selectedWorkspaceRoot = null;
/** @type {Map<string, any>} */
const snapshotCache = new Map();

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

function getCachedSnapshot(ws) {
  const key = path.resolve(ws);
  if (!snapshotCache.has(key)) {
    snapshotCache.set(key, BundleSnapshotBuilder.build(key));
  }
  return snapshotCache.get(key);
}

function invalidateSnapshots(ws = null) {
  if (ws) {
    snapshotCache.delete(path.resolve(ws));
  } else {
    snapshotCache.clear();
  }
}

function makeIcon(vscode, id) {
  if (typeof vscode.ThemeIcon === "function") {
    return new vscode.ThemeIcon(id);
  }
  return undefined;
}

function iconForState(vscode, state) {
  const norm = String(state || "").toLowerCase();
  if (norm === "completed" || norm === "closed") return makeIcon(vscode, "pass-filled");
  if (norm === "active" || norm === "in_progress") return makeIcon(vscode, "sync");
  if (norm === "blocked") return makeIcon(vscode, "warning");
  if (norm === "deferred" || norm === "skipped") return makeIcon(vscode, "circle-slash");
  return makeIcon(vscode, "circle-outline");
}

function postToWebview(msg) {
  if (!activePanel?.webview) return;
  if (!webviewReady) {
    pendingWebviewMessages.push(msg);
    return;
  }
  void activePanel.webview.postMessage(msg);
}

function flushWebviewQueue() {
  if (!activePanel?.webview || !webviewReady) return;
  const queued = pendingWebviewMessages;
  pendingWebviewMessages = [];
  for (const msg of queued) {
    void activePanel.webview.postMessage(msg);
  }
}

class SpecsTreeProvider {
  constructor(vscode) {
    this.vscode = vscode;
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.emitter.event;
  }

  refresh() {
    invalidateSnapshots();
    this.emitter.fire(undefined);
  }

  getTreeItem(element) {
    return element;
  }

  async getChildren(element) {
    const ws = resolveWorkspaceRoot(this.vscode);
    const snap = getCachedSnapshot(ws);
    if (!snap.bundleInitialized) {
      const empty = new this.vscode.TreeItem(
        "No .agents/bundles found — run /flow:setup",
        this.vscode.TreeItemCollapsibleState.None,
      );
      empty.command = {
        command: "flow.dispatchTask",
        title: "Run /flow:setup",
        arguments: [{ prompt: "/flow:setup", workspacePath: ws }],
      };
      return [empty];
    }

    if (!element) {
      if (snap.specs.length === 0) {
        const empty = new this.vscode.TreeItem(
          "No active specs — click + to draft one",
          this.vscode.TreeItemCollapsibleState.None,
        );
        empty.command = { command: "flow.newSpec", title: "New Spec" };
        return [empty];
      }
      return snap.specs.map((spec) => {
        const hasChildren = (spec.chapters?.length || 0) > 0 || (spec.tasks?.length || 0) > 0;
        const item = new this.vscode.TreeItem(
          spec.title || spec.flowId,
          hasChildren ? this.vscode.TreeItemCollapsibleState.Expanded : this.vscode.TreeItemCollapsibleState.None,
        );
        const notesSuffix = spec.unresolvedComments > 0 ? ` · ${spec.unresolvedComments} notes` : "";
        item.description = `${spec.state} · ${spec.completedTasks}/${spec.totalTasks}${notesSuffix}`;
        item.iconPath = iconForState(this.vscode, spec.state);
        item.contextValue = "flowSpec";
        item.flowSpec = spec;
        item.workspacePath = ws;
        const absPath = path.join(ws, spec.relPath);
        item.command = {
          command: "vscode.open",
          title: "Open Spec",
          arguments: [this.vscode.Uri.file(absPath)],
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
            ch.title || ch.chapterId,
            hasTasks ? this.vscode.TreeItemCollapsibleState.Collapsed : this.vscode.TreeItemCollapsibleState.None,
          );
          const notesSuffix = ch.unresolvedComments > 0 ? ` · ${ch.unresolvedComments} notes` : "";
          chItem.description = `${ch.state} · ${ch.completedTasks}/${ch.totalTasks}${notesSuffix}`;
          chItem.iconPath = iconForState(this.vscode, ch.state);
          chItem.contextValue = "flowChapter";
          chItem.flowChapter = ch;
          chItem.flowId = spec.flowId;
          chItem.workspacePath = ws;
          if (ch.relPath) {
            chItem.command = {
              command: "vscode.open",
              title: "Open Chapter Spec",
              arguments: [this.vscode.Uri.file(path.join(ws, ch.relPath))],
            };
          }
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
      this.vscode.TreeItemCollapsibleState.None,
    );
    item.description = task.state;
    item.iconPath = iconForState(this.vscode, task.state);
    item.contextValue = "flowTask";
    const absPath = path.join(ws, task.relPath);
    item.command = {
      command: "vscode.open",
      title: "Open Task Worksheet",
      arguments: [this.vscode.Uri.file(absPath)],
    };
    return item;
  }
}

class SpecCodeLensProvider {
  constructor(vscode) {
    this.vscode = vscode;
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeCodeLenses = this.emitter.event;
  }

  refresh() {
    this.emitter.fire(undefined);
  }

  async provideCodeLenses(document) {
    const fsPath = String(document?.uri?.fsPath || "").replace(/\\/g, "/");
    if (!fsPath.includes("/.agents/bundles/specs/") || !fsPath.endsWith("/spec.md")) {
      return [];
    }
    const docWorkspace = resolveUriWorkspaceRoot(this.vscode, document.uri) || resolveWorkspaceRoot(this.vscode);
    const relPath = docWorkspace ? toPosixRelative(docWorkspace, document.uri.fsPath) : "";
    const text = typeof document.getText === "function" ? document.getText() : "";
    const flowId =
      text.match(/^flow_id:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ||
      relPath.match(/specs\/([^/]+)/)?.[1] ||
      "spec";
    const curChapter = text.match(/^current_chapter:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() || "";
    const topRange = new this.vscode.Range(0, 0, 0, 0);

    const implCmd =
      curChapter && curChapter !== "null"
        ? `/flow:implement ${flowId} ${curChapter}`
        : `/flow:implement ${flowId}`;

    let openNoteCount = 0;
    try {
      const store = new SpecFeedbackStore(docWorkspace);
      const comments = store.listForFlow(flowId);
      openNoteCount = comments.filter(
        (c) => !c.parentCommentId && !c.resolved && c.state !== "addressed",
      ).length;
    } catch {
      openNoteCount = 0;
    }

    const lenses = [
      new this.vscode.CodeLens(topRange, {
        title: curChapter && curChapter !== "null" ? `Implement ${curChapter}` : "Implement Flow",
        command: "flow.dispatchTask",
        arguments: [{ prompt: implCmd, workspacePath: docWorkspace }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: "Review Flow",
        command: "flow.dispatchTask",
        arguments: [{ prompt: `/flow:review ${flowId}`, workspacePath: docWorkspace }],
      }),
      new this.vscode.CodeLens(topRange, {
        title: "Sync",
        command: "flow.syncSpecs",
        arguments: [{ flowId, workspacePath: docWorkspace }],
      }),
    ];

    if (openNoteCount > 0) {
      lenses.push(
        new this.vscode.CodeLens(topRange, {
          title: `Revise (${openNoteCount} open note${openNoteCount === 1 ? "" : "s"})`,
          command: "flow.reviseSpec",
          arguments: [{ flowId, relPath, workspacePath: docWorkspace }],
        }),
      );
    }

    lenses.push(
      new this.vscode.CodeLens(topRange, {
        title: "Open in Flow Studio",
        command: "flow.openStudio",
        arguments: [{ flowId, relPath, workspacePath: docWorkspace }],
      }),
    );

    return lenses;
  }
}

/**
 * Native VS Code inline spec review controller backed by `SpecFeedbackStore`.
 */
class SpecCommentController {
  constructor(vscode, onChanged) {
    this.vscode = vscode;
    this.onChanged = onChanged || (() => {});
    /** @type {Map<string, any[]>} */
    this.threadsByDoc = new Map();
    this.controller = null;

    if (typeof vscode.comments?.createCommentController !== "function") {
      return;
    }

    this.controller = vscode.comments.createCommentController("flowSpecReview", "Flow Spec Review");
    this.controller.commentingRangeProvider = {
      provideCommentingRanges: (document) => {
        const fsPath = String(document?.uri?.fsPath || "").replace(/\\/g, "/");
        if (!REVIEWABLE_MD_RE.test(fsPath)) return [];
        const lastLine = Math.max(0, Number(document.lineCount || 1) - 1);
        return [new vscode.Range(0, 0, lastLine, 0)];
      },
    };
  }

  dispose() {
    for (const threads of this.threadsByDoc.values()) {
      for (const t of threads) {
        try {
          t.dispose?.();
        } catch {
          // Ignore disposal failures.
        }
      }
    }
    this.threadsByDoc.clear();
    this.controller?.dispose?.();
  }

  refreshOpenDocuments() {
    if (!this.controller) return;
    const docs = Array.isArray(this.vscode.workspace?.textDocuments)
      ? this.vscode.workspace.textDocuments
      : [];
    for (const doc of docs) {
      this.refreshDocument(doc);
    }
  }

  refreshDocument(document) {
    if (!this.controller || !document?.uri?.fsPath) return;
    const fsPath = String(document.uri.fsPath).replace(/\\/g, "/");
    if (!REVIEWABLE_MD_RE.test(fsPath)) return;

    const ws = resolveUriWorkspaceRoot(this.vscode, document.uri) || resolveWorkspaceRoot(this.vscode);
    const relPath = toPosixRelative(ws, document.uri.fsPath);
    const docKey = document.uri.toString ? document.uri.toString() : fsPath;

    const existing = this.threadsByDoc.get(docKey) || [];
    for (const t of existing) {
      try {
        t.dispose?.();
      } catch {
        // Ignore stale thread dispose errors.
      }
    }

    const store = new SpecFeedbackStore(ws);
    const comments = store.list(relPath);
    const repliesByParent = new Map();
    const roots = [];
    for (const c of comments) {
      if (c.parentCommentId) {
        const arr = repliesByParent.get(c.parentCommentId) || [];
        arr.push(c);
        repliesByParent.set(c.parentCommentId, arr);
      } else {
        roots.push(c);
      }
    }

    const createdThreads = [];
    for (const root of roots) {
      const startIdx = Math.max(0, Number(root.startLine || 1) - 1);
      const endIdx = Math.max(startIdx, Number(root.endLine || root.startLine || 1) - 1);
      const range = new this.vscode.Range(startIdx, 0, endIdx, 0);
      const items = [root, ...(repliesByParent.get(root.id) || [])].map((entry) => ({
        body: entry.body,
        mode: this.vscode.CommentMode?.Preview ?? 1,
        author: { name: `${entry.authorName || "reviewer"} (${entry.commentKind || "feedback"})` },
        contextValue: entry.resolved ? "flowReviewResolved" : "flowReviewOpen",
        flowCommentId: entry.id,
      }));
      const thread = this.controller.createCommentThread(document.uri, range, items);
      const resolved = Boolean(root.resolved || root.state === "addressed");
      thread.collapsibleState = resolved
        ? (this.vscode.CommentThreadCollapsibleState?.Collapsed ?? 0)
        : (this.vscode.CommentThreadCollapsibleState?.Expanded ?? 1);
      thread.label = resolved ? `Flow Review · Addressed (L${root.startLine})` : `Flow Review · ${root.commentKind || "feedback"} (L${root.startLine})`;
      thread.contextValue = resolved ? "flowReviewResolved" : "flowReviewOpen";
      thread.flowMeta = { workspacePath: ws, relPath, flowId: store.inferFlowId(relPath), commentId: root.id };
      createdThreads.push(thread);
    }
    this.threadsByDoc.set(docKey, createdThreads);
  }

  async addCommentFromReply(reply) {
    const thread = reply?.thread;
    const text = String(reply?.text || "").trim();
    if (!thread?.uri?.fsPath || !text) return;
    const ws = resolveUriWorkspaceRoot(this.vscode, thread.uri) || resolveWorkspaceRoot(this.vscode);
    const relPath = toPosixRelative(ws, thread.uri.fsPath);
    const store = new SpecFeedbackStore(ws);

    if (thread.flowMeta?.commentId) {
      store.replyToComment(relPath, thread.flowMeta.commentId, { body: text, commentKind: "feedback" });
    } else {
      const startLine = Number(thread.range?.start?.line ?? 0) + 1;
      const endLine = Number(thread.range?.end?.line ?? startLine - 1) + 1;
      let quote = "";
      try {
        const doc = await this.vscode.workspace.openTextDocument(thread.uri);
        if (typeof doc?.lineAt === "function") {
          quote = String(doc.lineAt(Math.max(0, startLine - 1))?.text || "").trim();
        }
      } catch {
        quote = "";
      }
      store.add({
        relPath,
        startLine,
        endLine,
        quote: quote || undefined,
        commentKind: "feedback",
        body: text,
      });
      thread.dispose?.();
    }

    const doc = await this.vscode.workspace.openTextDocument(thread.uri);
    this.refreshDocument(doc);
    this.onChanged(ws);
  }

  async setThreadResolved(thread, resolved) {
    if (!thread?.flowMeta?.commentId) return;
    const { workspacePath, relPath, commentId } = thread.flowMeta;
    const store = new SpecFeedbackStore(workspacePath);
    store.setResolvedOrUpdate(relPath, commentId, { resolved: Boolean(resolved) });
    const doc = await this.vscode.workspace.openTextDocument(thread.uri);
    this.refreshDocument(doc);
    this.onChanged(workspacePath);
  }
}

function buildWebviewHtml(vscode, webview, initialWorkspace = "") {
  const nonce = crypto.randomBytes(16).toString("base64");
  const stylesUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_WEB_DIR, "styles.css")));
  const bridgeUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_WEB_DIR, "host-bridge.js")));
  const appUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_WEB_DIR, "app.js")));
  const logoUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_WEB_DIR, "logo.svg")));
  const faviconUri = webview.asWebviewUri(vscode.Uri.file(path.join(STUDIO_WEB_DIR, "favicon.svg")));
  const cspSource = webview.cspSource || "vscode-webview:";
  const cspMeta = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${cspSource} data: blob:; media-src ${cspSource} data: blob:; font-src ${cspSource} data:;">`;
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
  const rawHtml = fs.readFileSync(path.join(STUDIO_WEB_DIR, "index.html"), "utf8");
  const initScript = `<script nonce="${nonce}">window.__FLOW_LOGO_URI__ = ${JSON.stringify(String(logoUri))}; window.__FLOW_INITIAL_WORKSPACE__ = ${JSON.stringify(initialWorkspace || "")};</script>`;
  return rawHtml
    .replace("<head>", `<head>\n  ${cspMeta}`)
    .replace('<script src="/preload.js"></script>', initScript)
    .replace('href="/favicon.svg"', `href="${faviconUri}"`)
    .replace('<link rel="shortcut icon" href="/favicon.ico">', "")
    .replace('href="/styles.css"', `href="${stylesUri}"`)
    .replace("</head>", `${themeBridgeStyle}\n</head>`)
    .replace('<script src="/host-bridge.js"></script>', `<script nonce="${nonce}" src="${bridgeUri}"></script>`)
    .replace('<script src="/app.js"></script>', `<script nonce="${nonce}" src="${appUri}"></script>`);
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

  activeApiService = new StudioApiService({
    pluginRoot: PLUGIN_ROOT,
    env: {
      ...process.env,
      FLOW_STUDIO_DEFAULT_WORKSPACE: wsRoot,
    },
    onEvent: (event) => {
      postToWebview({ type: "studioEvent", event });
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

  const syncVsCodeModels = async () => {
    if (!activeApiService || typeof vscode.lm?.selectChatModels !== "function") return;
    try {
      const models = await vscode.lm.selectChatModels({});
      if (Array.isArray(models) && models.length > 0) {
        const ingested = await activeApiService.ingestVsCodeChatModels(models);
        const currentWs = selectedWorkspaceRoot || wsRoot;
        if (currentWs && fs.existsSync(path.join(currentWs, ".agents"))) {
          HarnessProfileMaterializer.materialize(currentWs, ingested, { harness: "vscode" });
        }
      }
    } catch {
      // Ignore unavailable Copilot LM providers in headless or restricted hosts.
    }
  };
  await syncVsCodeModels();
  if (typeof vscode.lm?.onDidChangeChatModels === "function") {
    context.subscriptions.push(vscode.lm.onDidChangeChatModels(() => void syncVsCodeModels()));
  }

  const specsTree = new SpecsTreeProvider(vscode);
  const codeLensProvider = new SpecCodeLensProvider(vscode);

  const statusBarItem =
    typeof vscode.window?.createStatusBarItem === "function"
      ? vscode.window.createStatusBarItem(vscode.StatusBarAlignment?.Left ?? 1, 50)
      : null;
  if (statusBarItem) {
    statusBarItem.command = "flow.quickActions";
    context.subscriptions.push(statusBarItem);
  }

  const refreshStatusBar = () => {
    if (!statusBarItem) return;
    const ws = resolveWorkspaceRoot(vscode);
    const snap = getCachedSnapshot(ws);
    if (!snap.bundleInitialized) {
      statusBarItem.hide?.();
      return;
    }
    const active = snap.specs.find((s) => s.flowId === snap.activeFlowId) || snap.specs[0] || null;
    if (!active) {
      statusBarItem.text = "$(checklist) Flow";
      statusBarItem.tooltip = "Flow initialized — click for quick actions";
    } else {
      const notesBadge = snap.counts.unresolvedComments > 0 ? ` · $(comment) ${snap.counts.unresolvedComments}` : "";
      statusBarItem.text = `$(checklist) ${active.flowId} ${active.completedTasks}/${active.totalTasks}${notesBadge}`;
      statusBarItem.tooltip = `${active.title} (${active.state}) — click for Flow actions`;
    }
    statusBarItem.show?.();
  };

  const refreshAllViews = (ws = null) => {
    invalidateSnapshots(ws);
    specsTree.refresh();
    codeLensProvider.refresh();
    refreshStatusBar();
  };

  const commentController = new SpecCommentController(vscode, (ws) => {
    refreshAllViews(ws);
    postToWebview({ type: "studioEvent", event: { type: "bundle.changed", workspacePath: ws } });
  });
  context.subscriptions.push(commentController);

  const syncActiveWorkspace = (nextWorkspacePath, notifyWebview = true) => {
    if (!nextWorkspacePath) return;
    const resolved = path.resolve(nextWorkspacePath);
    if (!fs.existsSync(resolved)) return;
    const changed = resolved !== selectedWorkspaceRoot;
    selectedWorkspaceRoot = resolved;
    registerOpenWorkspaceFolders();
    if (changed) {
      refreshAllViews(resolved);
    }
    if (notifyWebview && activePanel?.webview) {
      const allFolders = listVscodeWorkspacePaths(vscode);
      const orderedUris = [resolved, ...allFolders.filter((w) => w !== resolved)];
      postToWebview({
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
    vscode.languages.registerCodeLensProvider({ language: "markdown", scheme: "file" }, codeLensProvider),
  );

  if (typeof vscode.workspace?.onDidOpenTextDocument === "function") {
    context.subscriptions.push(
      vscode.workspace.onDidOpenTextDocument((doc) => commentController.refreshDocument(doc)),
    );
  }
  if (typeof vscode.workspace?.onDidSaveTextDocument === "function") {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument((doc) => commentController.refreshDocument(doc)),
    );
  }

  if (typeof vscode.window?.onDidChangeActiveTextEditor === "function") {
    context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor?.document) {
          commentController.refreshDocument(editor.document);
        }
        const nextWs = resolveUriWorkspaceRoot(vscode, editor?.document?.uri);
        if (nextWs && nextWs !== selectedWorkspaceRoot) {
          syncActiveWorkspace(nextWs, true);
        }
      }),
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
          refreshAllViews();
        }
      }),
    );
  }

  const watcher = vscode.workspace.createFileSystemWatcher("**/.agents/**");
  const onAgentsFsChange = () => {
    refreshAllViews();
    commentController.refreshOpenDocuments();
  };
  watcher.onDidChange(onAgentsFsChange);
  watcher.onDidCreate(onAgentsFsChange);
  watcher.onDidDelete(onAgentsFsChange);
  context.subscriptions.push(watcher);

  refreshStatusBar();
  commentController.refreshOpenDocuments();

  const ensureStudioPanel = (targetWs) => {
    if (targetWs) {
      syncActiveWorkspace(targetWs, Boolean(activePanel));
    }
    if (activePanel) {
      activePanel.reveal(vscode.ViewColumn.One);
      return activePanel;
    }
    webviewReady = false;
    pendingWebviewMessages = [];
    const panel = vscode.window.createWebviewPanel(
      "flowStudio",
      "Flow Studio",
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.file(STUDIO_ASSETS_DIR)],
      },
    );
    activePanel = panel;
    panel.onDidDispose(() => {
      activePanel = null;
      webviewReady = false;
      pendingWebviewMessages = [];
    });
    panel.webview.onDidReceiveMessage(async (msg) => {
      if (!msg || typeof msg !== "object" || !activeApiService) return;
      if (msg.type === "ready") {
        webviewReady = true;
        flushWebviewQueue();
        return;
      }
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
          if (msg.routePath === "/api/review-comments" || msg.routePath === "/api/sync") {
            refreshAllViews();
            commentController.refreshOpenDocuments();
          }
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
          msg.executionMode,
        );
        return;
      }
      if (msg.type === "openFile" && msg.absPath) {
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(msg.absPath));
        await vscode.window.showTextDocument(doc);
      }
    });
    panel.webview.html = buildWebviewHtml(vscode, panel.webview, resolveWorkspaceRoot(vscode));
    return panel;
  };

  context.subscriptions.push(
    vscode.commands.registerCommand("flow.openStudio", async (arg) => {
      const spec = arg?.flowSpec || null;
      const targetWs =
        arg?.workspacePath ||
        resolveActiveEditorWorkspaceRoot(vscode) ||
        resolveWorkspaceRoot(vscode);
      ensureStudioPanel(targetWs);
      const flowId = arg?.flowId || spec?.flowId || null;
      const relPath = arg?.relPath || spec?.relPath || null;
      if (flowId || relPath || arg?.tab) {
        postToWebview({
          type: "navigateTo",
          workspacePath: targetWs,
          flowId,
          relPath,
          tab: arg?.tab || "review",
        });
      }
    }),

    vscode.commands.registerCommand("flow.newSpec", async () => {
      ensureStudioPanel(resolveWorkspaceRoot(vscode));
      postToWebview({ type: "openNewSpec" });
    }),

    vscode.commands.registerCommand("flow.studioHome", async () => {
      ensureStudioPanel(resolveWorkspaceRoot(vscode));
      postToWebview({ type: "navigateHome" });
    }),

    vscode.commands.registerCommand("flow.syncSpecs", async (arg) => {
      if (!activeApiService) return;
      const ws = arg?.workspacePath || resolveWorkspaceRoot(vscode);
      const res = await activeApiService.handleApi("/api/sync", {
        workspacePath: ws,
        flowId: arg?.flowId || arg?.flowSpec?.flowId || null,
      });
      refreshAllViews(ws);
      const changed = (res.specs || []).reduce((acc, s) => acc + (s.updated_files?.length || 0), 0);
      await vscode.window.showInformationMessage(
        changed > 0 ? `Flow synced ${changed} spec file(s).` : "All Flow spec checklists are in sync.",
      );
    }),

    vscode.commands.registerCommand("flow.reviseSpec", async (arg) => {
      if (!activeApiService) return;
      const meta = arg?.flowMeta || arg || {};
      const ws = meta.workspacePath || resolveWorkspaceRoot(vscode);
      const snap = getCachedSnapshot(ws);
      const flowId = meta.flowId || snap.activeFlowId || snap.specs[0]?.flowId;
      if (!flowId) {
        await vscode.window.showInformationMessage("No active Flow spec found in this workspace.");
        return;
      }
      const store = new SpecFeedbackStore(ws);
      const relPath = meta.relPath || `.agents/bundles/specs/${flowId}/spec.md`;
      const prompt = store.buildRevisePrompt(relPath, flowId);
      await routePromptToHostHarness(vscode, activeApiService, ws, prompt);
    }),

    vscode.commands.registerCommand("flow.searchDocs", async () => {
      const query = await vscode.window.showInputBox({
        prompt: "Search local Flow specs and bundle notes (instant BM25)",
      });
      if (!query || !activeApiService) return;
      const ws = resolveWorkspaceRoot(vscode);
      const res = await activeApiService.handleApi("/api/catalog-search", {
        workspacePath: ws,
        query,
        mode: "bm25",
      });
      const hits = res.hits || [];
      if (hits.length === 0) {
        await vscode.window.showInformationMessage(`No bundle notes matched "${query}".`);
        return;
      }
      const picked = await vscode.window.showQuickPick(
        hits.map((h) => ({
          label: h.title,
          description: `${h.concept_type} · ${h.rel_path}`,
          detail: h.description || h.snippet,
          hit: h,
        })),
      );
      if (picked?.hit) {
        const abs = path.join(picked.hit.workspace_root || ws, picked.hit.rel_path);
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(abs));
        await vscode.window.showTextDocument(doc);
      }
    }),

    vscode.commands.registerCommand("flow.dispatchTask", async (arg) => {
      if (!activeApiService) return;
      let prompt = arg?.prompt || "";
      if (!prompt && arg?.flowChapter && arg?.flowId) {
        prompt = `/flow:implement ${arg.flowId} ${arg.flowChapter.chapterId}`;
      } else if (!prompt && arg?.flowSpec?.recommendedAction?.command) {
        prompt = arg.flowSpec.recommendedAction.command;
      }
      if (!prompt) {
        prompt = await vscode.window.showInputBox({ prompt: "Enter Flow command or prompt to dispatch" });
      }
      if (!prompt) return;
      const targetWs = arg?.workspacePath || resolveWorkspaceRoot(vscode);
      if (targetWs) {
        syncActiveWorkspace(targetWs, true);
      }
      await routePromptToHostHarness(vscode, activeApiService, targetWs, prompt);
    }),

    vscode.commands.registerCommand("flow.quickActions", async () => {
      const ws = resolveWorkspaceRoot(vscode);
      const snap = getCachedSnapshot(ws);
      const active = snap.specs.find((s) => s.flowId === snap.activeFlowId) || snap.specs[0] || null;
      const items = [
        { label: "$(sync) Sync Spec Checklists", action: "sync" },
        ...(active?.recommendedAction
          ? [{ label: `$(play) ${active.recommendedAction.label}`, description: active.recommendedAction.command, action: "recommended" }]
          : []),
        ...(active ? [{ label: `$(checklist) Review ${active.flowId}`, description: `/flow:review ${active.flowId}`, action: "review" }] : []),
        ...(active && snap.counts.unresolvedComments > 0
          ? [{ label: `$(comment-discussion) Send ${snap.counts.unresolvedComments} Note(s) to /flow:revise`, action: "revise" }]
          : []),
        { label: "$(search) Search Bundle Notes & Specs", action: "search" },
        { label: "$(layout-panel) Open Flow Studio", action: "studio" },
      ];
      const picked = await vscode.window.showQuickPick(items, { placeHolder: "Flow actions for active workspace" });
      if (!picked) return;
      if (picked.action === "sync") await vscode.commands.executeCommand("flow.syncSpecs", { workspacePath: ws });
      else if (picked.action === "recommended") {
        await vscode.commands.executeCommand("flow.dispatchTask", {
          prompt: active.recommendedAction.command,
          workspacePath: ws,
        });
      } else if (picked.action === "review") {
        await vscode.commands.executeCommand("flow.dispatchTask", {
          prompt: `/flow:review ${active.flowId}`,
          workspacePath: ws,
        });
      } else if (picked.action === "revise") {
        await vscode.commands.executeCommand("flow.reviseSpec", { flowId: active.flowId, workspacePath: ws });
      } else if (picked.action === "search") {
        await vscode.commands.executeCommand("flow.searchDocs");
      } else if (picked.action === "studio") {
        await vscode.commands.executeCommand("flow.openStudio", { workspacePath: ws });
      }
    }),

    vscode.commands.registerCommand("flow.addSpecComment", async (reply) => {
      await commentController.addCommentFromReply(reply);
    }),

    vscode.commands.registerCommand("flow.replySpecComment", async (reply) => {
      await commentController.addCommentFromReply(reply);
    }),

    vscode.commands.registerCommand("flow.resolveSpecComment", async (thread) => {
      await commentController.setThreadResolved(thread, true);
    }),

    vscode.commands.registerCommand("flow.reopenSpecComment", async (thread) => {
      await commentController.setThreadResolved(thread, false);
    }),

    vscode.commands.registerCommand("flow.runEntrypoint", async () => {
      const ws = resolveWorkspaceRoot(vscode);
      const py = detectWorkspacePython(ws);
      const scripts = Object.keys(py.entrypointTargets || {});
      if (scripts.length === 0) {
        await vscode.window.showInformationMessage(
          `Detected Python runner: ${py.manager} (no [project.scripts] declared).`,
        );
        return;
      }
      const picked = await vscode.window.showQuickPick(
        scripts.map((s) => ({ label: s, description: `Run via ${py.manager}` })),
      );
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
    }),
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
  webviewReady = false;
  pendingWebviewMessages = [];
  selectedWorkspaceRoot = null;
  snapshotCache.clear();
}
