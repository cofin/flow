"""Tests for the editor-native multi-harness VS Code and Cursor extension."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.validate import REPO_ROOT

NODE_BIN = shutil.which("node")
EXT_DIR = REPO_ROOT / "vscode-extension"


def _seed_workspace(tmp_path: Path) -> Path:
    """Create a multi-chapter Flow workspace for VS Code extension provider tests."""
    bundles = tmp_path / ".agents" / "bundles"
    ch_dir = bundles / "specs" / "studio-ui" / "chapters" / "ch01-core" / "tasks"
    ch_dir.mkdir(parents=True)
    (bundles / "knowledge" / "architecture").mkdir(parents=True)
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}),
        encoding="utf-8",
    )
    (bundles / "index.md").write_text('---\nokf_version: "0.2"\nbundle: demo\n---\n', encoding="utf-8")
    (bundles / "specs" / "studio-ui" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: studio-ui\n"
        "title: Studio UI\n"
        "state: active\n"
        "has_chapters: true\n"
        "current_chapter: ch01-core\n"
        "---\n\n"
        "## 1. Objective\n\nBuild calm Studio UI.\n\n"
        "## 5. Implementation Plan\n\n"
        "- [~] [ch01-core](chapters/ch01-core/spec.md) — Core slice\n",
        encoding="utf-8",
    )
    (bundles / "specs" / "studio-ui" / "chapters" / "ch01-core" / "spec.md").write_text(
        "---\ntype: Spec\nchapter_id: ch01-core\nstate: active\n---\n\n"
        "## 5. Implementation Plan\n\n- [ ] [t01](tasks/t01-catalog.md) — Catalog\n",
        encoding="utf-8",
    )
    (ch_dir / "t01-catalog.md").write_text(
        "---\ntype: Task\nid: studio-ui:ch01:t01\ntitle: Catalog\nstate: pending\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (bundles / "knowledge" / "architecture" / "catalog.md").write_text(
        "---\ntype: Architecture\ntitle: Bundle Graph\n"
        "description: Zero-Python note search.\nstatus: stable\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n[project.scripts]\ndemo-cli = "demo:main"\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return tmp_path


def test_vscode_extension_manifest_declares_cjs_entry_editor_native_commands_and_no_catalog_bloat() -> None:
    """Verify vscode-extension/package.json uses extension.cjs, drops Knowledge Catalog, and adds native commands."""
    pkg = json.loads((EXT_DIR / "package.json").read_text(encoding="utf-8"))
    root_pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "flow-studio"
    assert pkg["version"] == root_pkg["version"]
    assert pkg["main"] == "./extension.cjs"
    assert "type" not in pkg

    contributes = pkg["contributes"]
    containers = contributes["viewsContainers"]["activitybar"]
    assert any(c["id"] == "flowStudio" for c in containers)

    views = contributes["views"]["flowStudio"]
    view_ids = {v["id"] for v in views}
    assert view_ids == {"flowSpecsTree"}

    cmd_ids = {c["command"] for c in contributes["commands"]}
    assert {
        "flow.openStudio",
        "flow.newSpec",
        "flow.syncSpecs",
        "flow.reviseSpec",
        "flow.searchDocs",
        "flow.dispatchTask",
        "flow.quickActions",
        "flow.addSpecComment",
        "flow.replySpecComment",
        "flow.resolveSpecComment",
        "flow.reopenSpecComment",
        "flow.runEntrypoint",
        "flow.selectTargetHarness",
    } <= cmd_ids
    assert "flow.searchCatalog" not in cmd_ids

    props = contributes["configuration"]["properties"]
    assert "flow.defaultHarness" in props
    assert "flow.executionMode" in props
    assert "flow.catalogDbPath" not in props
    assert set(props["flow.executionMode"]["enum"]) == {
        "direct-workspace",
        "worktree-isolated",
        "read-only",
    }


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_comment_controller_status_bar_codelens_and_csp_webview(tmp_path: Path) -> None:
    """Verify SpecCommentController, status bar, SpecsTreeProvider, CodeLenses, and CSP-hardened queued webview."""
    assert NODE_BIN is not None
    ws = _seed_workspace(tmp_path)
    ext_entry = EXT_DIR / "extension.mjs"

    probe_js = """
import { pathToFileURL } from "node:url";

const extUrl = pathToFileURL(process.argv[1]).href;
const wsPath = process.argv[2];

const registeredCommands = new Map();
const treeProviders = new Map();
const codeLensProviders = [];
const executedHostCommands = [];
let webviewMessageListener = null;
let capturedPanel = null;
const postedWebviewMessages = [];
const createdThreads = [];
const statusBarItems = [];
let commentControllerRef = null;

const specFilePath = `${wsPath}/.agents/bundles/specs/studio-ui/spec.md`;
const specDocMock = {
  uri: { fsPath: specFilePath, scheme: "file", toString: () => `file://${specFilePath}` },
  lineCount: 14,
  lineAt: (i) => ({ text: `Spec line ${i + 1}` }),
  getText: () => [
    "---",
    "flow_id: studio-ui",
    "state: active",
    "current_chapter: ch01-core",
    "---",
    "# Studio UI",
    "## 5. Implementation Plan",
  ].join("\\n"),
};

const vscodeMock = {
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  StatusBarAlignment: { Left: 1, Right: 2 },
  CommentMode: { Editing: 0, Preview: 1 },
  CommentThreadCollapsibleState: { Collapsed: 0, Expanded: 1 },
  ThemeIcon: class ThemeIcon {
    constructor(id) { this.id = id; }
  },
  TreeItem: class TreeItem {
    constructor(label, collapsibleState = 0) {
      this.label = label;
      this.collapsibleState = collapsibleState;
    }
  },
  Range: class Range {
    constructor(sl, sc, el, ec) {
      this.start = { line: sl, character: sc };
      this.end = { line: el, character: ec };
    }
  },
  CodeLens: class CodeLens {
    constructor(range, command) {
      this.range = range;
      this.command = command;
    }
  },
  EventEmitter: class EventEmitter {
    constructor() {
      this.listeners = [];
      this.event = (fn) => { this.listeners.push(fn); return { dispose() {} }; };
    }
    fire(val) { for (const fn of this.listeners) fn(val); }
  },
  Uri: {
    file: (p) => ({ fsPath: p, scheme: "file", toString: () => `file://${p}` }),
  },
  ViewColumn: { One: 1, Beside: 2 },
  comments: {
    createCommentController: (id, label) => {
      commentControllerRef = {
        id,
        label,
        commentingRangeProvider: null,
        createCommentThread: (uri, range, comments) => {
          const thread = { uri, range, comments, disposed: false, dispose() { this.disposed = true; } };
          createdThreads.push(thread);
          return thread;
        },
        dispose() {},
      };
      return commentControllerRef;
    },
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: wsPath } }],
    textDocuments: [specDocMock],
    getConfiguration: () => ({
      get: (key, defVal) => {
        if (key === "defaultHarness") return "copilot";
        if (key === "executionMode") return "direct-workspace";
        return defVal;
      },
      update: async () => {},
    }),
    createFileSystemWatcher: () => ({
      onDidChange: () => ({ dispose() {} }),
      onDidCreate: () => ({ dispose() {} }),
      onDidDelete: () => ({ dispose() {} }),
      dispose() {},
    }),
    openTextDocument: async (uri) => ({ ...specDocMock, uri }),
  },
  window: {
    createStatusBarItem: () => {
      const item = {
        text: "", tooltip: "", command: "", shown: false,
        show() { this.shown = true; }, hide() { this.shown = false; }, dispose() {},
      };
      statusBarItems.push(item);
      return item;
    },
    registerTreeDataProvider: (id, provider) => {
      treeProviders.set(id, provider);
      return { dispose() {} };
    },
    createWebviewPanel: () => {
      capturedPanel = {
        webview: {
          html: "",
          cspSource: "https://test.vscode-cdn.net",
          asWebviewUri: (u) => u.toString(),
          onDidReceiveMessage: (fn) => { webviewMessageListener = fn; return { dispose() {} }; },
          postMessage: async (msg) => { postedWebviewMessages.push(msg); return true; },
        },
        onDidDispose: () => ({ dispose() {} }),
        reveal: () => {},
      };
      return capturedPanel;
    },
    showInformationMessage: async () => undefined,
    showWarningMessage: async () => undefined,
    showQuickPick: async (items) => items[0],
    showInputBox: async () => "Bundle Graph",
    showTextDocument: async () => {},
    createTerminal: () => ({ show() {}, sendText() {} }),
  },
  languages: {
    registerCodeLensProvider: (_sel, provider) => {
      codeLensProviders.push(provider);
      return { dispose() {} };
    },
  },
  commands: {
    registerCommand: (id, fn) => {
      registeredCommands.set(id, fn);
      return { dispose() {} };
    },
    executeCommand: async (id, ...args) => {
      executedHostCommands.push({ id, args });
    },
  },
};

const mod = await import(extUrl);
const extUri = vscodeMock.Uri.file(process.argv[3]);
const context = { extensionPath: process.argv[3], extensionUri: extUri, subscriptions: [] };
await mod.activateWithVscode(context, vscodeMock);

const ranges = commentControllerRef.commentingRangeProvider.provideCommentingRanges(specDocMock);
const draftThread = {
  uri: specDocMock.uri,
  range: new vscodeMock.Range(5, 0, 5, 0),
  dispose() {},
};
await registeredCommands.get("flow.addSpecComment")({ thread: draftThread, text: "Clarify retry backoff." });
const openThread = createdThreads.find((t) => !t.disposed && t.flowMeta?.commentId);
await registeredCommands.get("flow.replySpecComment")({ thread: openThread, text: "Use exponential backoff." });

const lensesWithNotes = await codeLensProviders[0].provideCodeLenses(specDocMock);
await registeredCommands.get("flow.reviseSpec")({ flowId: "studio-ui", workspacePath: wsPath });

const latestOpenThread = [...createdThreads].reverse().find((t) => !t.disposed && t.flowMeta?.commentId);
await registeredCommands.get("flow.resolveSpecComment")(latestOpenThread);
const resolvedThread = [...createdThreads].reverse().find((t) => !t.disposed && t.flowMeta?.commentId);

const specsTree = treeProviders.get("flowSpecsTree");
const rootSpecs = await specsTree.getChildren();
const childChapters = await specsTree.getChildren(rootSpecs[0]);

await registeredCommands.get("flow.openStudio")({
  flowId: "studio-ui",
  relPath: ".agents/bundles/specs/studio-ui/spec.md",
});
const queuedBeforeReady = postedWebviewMessages.length;
await webviewMessageListener({ type: "ready" });
const navAfterReady = postedWebviewMessages.find((m) => m.type === "navigateTo");

await webviewMessageListener({
  type: "apiRequest",
  id: 42,
  routePath: "/api/bundle-snapshot",
  payload: { workspacePath: wsPath },
});

await mod.deactivate();

process.stdout.write(JSON.stringify({
  rangeCount: ranges.length,
  openThreadCount: latestOpenThread.comments.length,
  resolvedContextValue: resolvedThread.contextValue,
  lensTitles: lensesWithNotes.map((l) => l.command.title),
  statusBarText: statusBarItems[0]?.text || "",
  specLabels: rootSpecs.map((item) => item.label),
  chapterLabels: childChapters.map((item) => item.label),
  webviewHtml: capturedPanel ? capturedPanel.webview.html : "",
  queuedBeforeReady,
  navAfterReady,
  postedWebviewMessages,
  executedHostCommands,
}) + "\\n");
"""
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", probe_js, str(ext_entry), str(ws), str(EXT_DIR)],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    out = json.loads(proc.stdout)
    assert out["rangeCount"] == 1
    assert out["openThreadCount"] == 2
    assert out["resolvedContextValue"] == "flowReviewResolved"
    assert any("Revise (1 open note)" in t for t in out["lensTitles"])
    assert any("Sync" in t for t in out["lensTitles"])
    assert "studio-ui" in out["statusBarText"]
    assert any("Studio UI" in lbl for lbl in out["specLabels"])
    assert any("ch01-core" in lbl for lbl in out["chapterLabels"])
    assert "Content-Security-Policy" in out["webviewHtml"]
    assert "nonce-" in out["webviewHtml"]
    assert "flow-vscode-theme-bridge" in out["webviewHtml"]
    assert out["queuedBeforeReady"] == 0
    assert out["navAfterReady"]["flowId"] == "studio-ui"
    api_resp = next(m for m in out["postedWebviewMessages"] if m.get("type") == "apiResponse" and m.get("id") == 42)
    assert api_resp["result"]["specs"][0]["flowId"] == "studio-ui"
    assert any(
        cmd["id"] == "workbench.action.chat.open" and "/flow:revise studio-ui" in cmd["args"][0]["query"]
        for cmd in out["executedHostCommands"]
    )


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_follows_active_editor_workspace_and_syncs_webview(tmp_path: Path) -> None:
    """Verify VS Code extension tracks activeTextEditor across multi-root workspaces and syncs with the webview."""
    assert NODE_BIN is not None
    ws_alpha = _seed_workspace(tmp_path / "alpha")
    ws_beta = _seed_workspace(tmp_path / "beta")
    beta_spec = ws_beta / ".agents" / "bundles" / "specs" / "studio-ui" / "spec.md"
    beta_spec.write_text(
        beta_spec.read_text(encoding="utf-8")
        .replace("flow_id: studio-ui", "flow_id: beta-plan")
        .replace("title: Studio UI", "title: Beta Workspace Plan"),
        encoding="utf-8",
    )
    ext_entry = EXT_DIR / "extension.mjs"

    probe_js = """
import { pathToFileURL } from "node:url";

const extUrl = pathToFileURL(process.argv[1]).href;
const wsAlpha = process.argv[2];
const wsBeta = process.argv[3];

const registeredCommands = new Map();
const treeProviders = new Map();
const postedWebviewMessages = [];
let activeEditorChangeHandler = null;
let webviewMessageListener = null;
let capturedPanel = null;

const vscodeMock = {
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  TreeItem: class TreeItem {
    constructor(label, collapsibleState = 0) {
      this.label = label;
      this.collapsibleState = collapsibleState;
    }
  },
  Range: class Range {
    constructor(sl, sc, el, ec) {
      this.start = { line: sl, character: sc };
      this.end = { line: el, character: ec };
    }
  },
  CodeLens: class CodeLens {
    constructor(range, command) {
      this.range = range;
      this.command = command;
    }
  },
  EventEmitter: class EventEmitter {
    constructor() {
      this.listeners = [];
      this.event = (fn) => { this.listeners.push(fn); return { dispose() {} }; };
    }
    fire(val) { for (const fn of this.listeners) fn(val); }
  },
  Uri: {
    file: (p) => ({ fsPath: p, scheme: "file", toString: () => `file://${p}` }),
  },
  ViewColumn: { One: 1 },
  workspace: {
    workspaceFolders: [
      { uri: { fsPath: wsAlpha } },
      { uri: { fsPath: wsBeta } },
    ],
    getWorkspaceFolder: (uri) => {
      if (!uri?.fsPath) return undefined;
      if (uri.fsPath.startsWith(wsBeta)) return { uri: { fsPath: wsBeta } };
      if (uri.fsPath.startsWith(wsAlpha)) return { uri: { fsPath: wsAlpha } };
      return undefined;
    },
    getConfiguration: () => ({
      get: (key, defVal) => defVal,
      update: async () => {},
    }),
    createFileSystemWatcher: () => ({
      onDidChange: () => ({ dispose() {} }),
      onDidCreate: () => ({ dispose() {} }),
      onDidDelete: () => ({ dispose() {} }),
      dispose() {},
    }),
    onDidChangeWorkspaceFolders: () => ({ dispose() {} }),
    openTextDocument: async (uri) => ({ uri }),
  },
  window: {
    activeTextEditor: { document: { uri: { fsPath: `${wsBeta}/pyproject.toml` } } },
    onDidChangeActiveTextEditor: (fn) => {
      activeEditorChangeHandler = fn;
      return { dispose() {} };
    },
    registerTreeDataProvider: (id, provider) => {
      treeProviders.set(id, provider);
      return { dispose() {} };
    },
    createWebviewPanel: () => {
      capturedPanel = {
        webview: {
          html: "",
          cspSource: "https://test.vscode-cdn.net",
          asWebviewUri: (u) => u.toString(),
          onDidReceiveMessage: (fn) => { webviewMessageListener = fn; return { dispose() {} }; },
          postMessage: async (msg) => { postedWebviewMessages.push(msg); return true; },
        },
        onDidDispose: () => ({ dispose() {} }),
        reveal: () => {},
      };
      return capturedPanel;
    },
    showInformationMessage: async () => undefined,
    showQuickPick: async (items) => items[0],
    showInputBox: async () => undefined,
    showTextDocument: async () => {},
    createTerminal: () => ({ show() {}, sendText() {} }),
  },
  languages: {
    registerCodeLensProvider: () => ({ dispose() {} }),
  },
  commands: {
    registerCommand: (id, fn) => {
      registeredCommands.set(id, fn);
      return { dispose() {} };
    },
    executeCommand: async () => {},
  },
  lm: {
    selectChatModels: async () => [
      {
        id: "gpt-5.4",
        vendor: "openai",
        family: "gpt-5",
        maxInputTokens: 200000,
        capabilities: { toolCalling: true, reasoning: true, efforts: ["medium", "high", "xhigh"] },
      },
      {
        id: "claude-opus-4-6",
        vendor: "anthropic",
        family: "claude",
        maxInputTokens: 200000,
        capabilities: { toolCalling: true, reasoning: true, efforts: ["high", "xhigh"] },
      },
    ],
    onDidChangeChatModels: () => ({ dispose() {} }),
  },
};

const mod = await import(extUrl);
const extUri = vscodeMock.Uri.file(process.argv[4]);
const context = { extensionPath: process.argv[4], extensionUri: extUri, subscriptions: [] };
await mod.activateWithVscode(context, vscodeMock);

const specsTree = treeProviders.get("flowSpecsTree");
const initialSpecs = await specsTree.getChildren();

await registeredCommands.get("flow.openStudio")();
await webviewMessageListener({ type: "ready" });
await webviewMessageListener({
  type: "apiRequest",
  id: 3,
  routePath: "/api/models-and-quota",
  payload: { workspacePath: wsBeta, harness: "vscode" },
});
await webviewMessageListener({
  type: "apiRequest",
  id: 1,
  routePath: "/api/studio-context",
  payload: {},
});

vscodeMock.window.activeTextEditor = { document: { uri: { fsPath: `${wsAlpha}/pyproject.toml` } } };
activeEditorChangeHandler(vscodeMock.window.activeTextEditor);
const specsAfterEditorSwitch = await specsTree.getChildren();

await webviewMessageListener({
  type: "apiRequest",
  id: 2,
  routePath: "/api/bundle-snapshot",
  payload: { workspacePath: wsBeta, registerWorkspace: true },
});
const specsAfterWebviewSwitch = await specsTree.getChildren();

await mod.deactivate();

process.stdout.write(JSON.stringify({
  initialSpecLabels: initialSpecs.map((i) => i.label),
  specsAfterEditorSwitch: specsAfterEditorSwitch.map((i) => i.label),
  specsAfterWebviewSwitch: specsAfterWebviewSwitch.map((i) => i.label),
  webviewHtml: capturedPanel ? capturedPanel.webview.html : "",
  postedWebviewMessages,
}) + "\\n");
"""
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", probe_js, str(ext_entry), str(ws_alpha), str(ws_beta), str(EXT_DIR)],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    out = json.loads(proc.stdout)
    assert any("Beta Workspace Plan" in lbl for lbl in out["initialSpecLabels"])
    assert any("Studio UI" in lbl for lbl in out["specsAfterEditorSwitch"])
    assert any("Beta Workspace Plan" in lbl for lbl in out["specsAfterWebviewSwitch"])
    assert json.dumps(str(ws_beta)) in out["webviewHtml"]
    ctx_resp = next(m for m in out["postedWebviewMessages"] if m.get("type") == "apiResponse" and m.get("id") == 1)
    assert ctx_resp["result"]["defaultWorkspace"] == str(ws_beta)
    assert str(ws_alpha) in ctx_resp["result"]["workspaces"]
    models_resp = next(m for m in out["postedWebviewMessages"] if m.get("type") == "apiResponse" and m.get("id") == 3)
    vs_candidates = models_resp["result"].get("dynamicByHarness", {}).get("vscode", {}).get("candidates", [])
    discovered_ids = {c["model"] for c in vs_candidates}
    assert "gpt-5.4" in discovered_ids
    assert (ws_beta / ".github" / "agents" / "flow-model-strong.agent.md").is_file()
    ws_events = [
        m["event"]
        for m in out["postedWebviewMessages"]
        if m.get("type") == "studioEvent" and m.get("event", {}).get("type") == "workspace.changed"
    ]
    assert any(ev["workspacePath"] == str(ws_alpha) for ev in ws_events)


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_installer_creates_runnable_recursive_bundle(tmp_path: Path) -> None:
    """Verify install.mjs recursively bundles sidecars/studio/ and the installed CJS entrypoint activates cleanly."""
    assert NODE_BIN is not None
    ext_dir = tmp_path / "extensions"
    ws = _seed_workspace(tmp_path / "ws")
    installer = EXT_DIR / "install.mjs"

    proc_update_only_empty = subprocess.run(
        [NODE_BIN, str(installer), "--extensions-dir", str(ext_dir), "--update-only"],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert not list(ext_dir.glob("cofin.flow-studio-*"))
    assert "No VS Code-compatible editor updated" in proc_update_only_empty.stdout

    proc = subprocess.run(
        [NODE_BIN, str(installer), "--extensions-dir", str(ext_dir)],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert "Installed cofin.flow-studio@" in proc.stdout
    installed_dirs = list(ext_dir.glob("cofin.flow-studio-*"))
    assert len(installed_dirs) == 1
    bundle_dir = installed_dirs[0]

    for rel in (
        "package.json",
        "extension.cjs",
        "extension.mjs",
        "README.md",
        "sidecars/studio/router.mjs",
        "sidecars/studio/bridges/python.mjs",
        "sidecars/studio/core/fs-io.mjs",
        "sidecars/studio/spec/feedback.mjs",
        "sidecars/studio/web/app.js",
        "sidecars/studio/web/host-bridge.js",
        "sidecars/studio/web/index.html",
        "sidecars/studio/web/styles.css",
    ):
        assert (bundle_dir / rel).is_file(), f"Missing bundled asset: {rel}"

    assert "./sidecars/studio/" in (bundle_dir / "extension.mjs").read_text(encoding="utf-8")

    # Actually load the installed bundle via CJS require() from outside the repo tree.
    cjs_probe = """
const path = require("node:path");
const bundleDir = process.argv[1];
const wsPath = process.argv[2];
const cjsEntry = require(path.join(bundleDir, "extension.cjs"));
if (typeof cjsEntry.activate !== "function" || typeof cjsEntry.deactivate !== "function") {
  throw new Error("extension.cjs missing activate/deactivate exports");
}
import(require("node:url").pathToFileURL(path.join(bundleDir, "extension.mjs")).href).then(async (mod) => {
  const cmds = new Set();
  const vscodeMock = {
    TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
    TreeItem: class { constructor(l, s) { this.label = l; this.collapsibleState = s; } },
    EventEmitter: class { constructor() { this.event = () => ({ dispose() {} }); } fire() {} },
    Uri: { file: (p) => ({ fsPath: p, toString: () => `file://${p}` }) },
    ViewColumn: { One: 1 },
    workspace: {
      workspaceFolders: [{ uri: { fsPath: wsPath } }],
      getConfiguration: () => ({ get: (_k, d) => d, update: async () => {} }),
      createFileSystemWatcher: () => ({ onDidChange() {}, onDidCreate() {}, onDidDelete() {}, dispose() {} }),
    },
    window: { registerTreeDataProvider: () => ({ dispose() {} }) },
    languages: { registerCodeLensProvider: () => ({ dispose() {} }) },
    commands: { registerCommand: (id) => { cmds.add(id); return { dispose() {} }; } },
  };
  await mod.activateWithVscode({ subscriptions: [] }, vscodeMock);
  await mod.deactivate();
  process.stdout.write(JSON.stringify({ ok: true, count: cmds.size }) + "\\n");
});
"""
    load_proc = subprocess.run(
        [NODE_BIN, "-e", cjs_probe, str(bundle_dir), str(ws)],
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    loaded = json.loads(load_proc.stdout.strip().splitlines()[-1])
    assert loaded["ok"] is True
    assert loaded["count"] >= 10

    proc_if_needed = subprocess.run(
        [NODE_BIN, str(installer), "--extensions-dir", str(ext_dir), "--if-needed", "--update-only"],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert "(up-to-date)" in proc_if_needed.stdout


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_installer_runs_through_npm_bin_symlink(tmp_path: Path) -> None:
    """Verify the installer runs when launched through a node_modules/.bin symlink, as npx does."""
    assert NODE_BIN is not None
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    bin_link = bin_dir / "flow-studio-vscode"
    bin_link.symlink_to(EXT_DIR / "install.mjs")
    ext_dir = tmp_path / "extensions"
    proc = subprocess.run(
        [NODE_BIN, str(bin_link), "--extensions-dir", str(ext_dir)],
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    assert "Installed cofin.flow-studio@" in proc.stdout
    assert len(list(ext_dir.glob("cofin.flow-studio-*"))) == 1


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
@pytest.mark.parametrize("flag", ("--help", "-h"))
def test_vscode_extension_installer_help_prints_usage_without_installing(tmp_path: Path, flag: str) -> None:
    """Verify --help prints usage and leaves the target extensions directory untouched."""
    assert NODE_BIN is not None
    ext_dir = tmp_path / "extensions"
    proc = subprocess.run(
        [NODE_BIN, str(EXT_DIR / "install.mjs"), flag, "--extensions-dir", str(ext_dir)],
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    assert proc.stdout.startswith("Usage: flow-studio-vscode")
    assert "--target <name>" in proc.stdout
    assert "--update-only" in proc.stdout
    assert not ext_dir.exists()
