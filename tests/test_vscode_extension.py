"""Tests for the shared-core multi-harness VS Code and Cursor extension."""

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
        "---\ntype: Architecture\ntitle: DuckDB Catalog\ndescription: Hybrid index.\nstatus: stable\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n[project.scripts]\ndemo-cli = "demo:main"\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return tmp_path


def test_vscode_extension_manifest_declares_views_commands_and_multi_harness_settings() -> None:
    """Verify vscode-extension/package.json declares Activity Bar views, commands, and harness settings."""
    pkg = json.loads((EXT_DIR / "package.json").read_text(encoding="utf-8"))
    root_pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "flow-studio"
    assert pkg["version"] == root_pkg["version"]
    assert pkg["type"] == "module"
    assert pkg["main"] == "./extension.mjs"

    contributes = pkg["contributes"]
    containers = contributes["viewsContainers"]["activitybar"]
    assert any(c["id"] == "flowStudio" for c in containers)

    views = contributes["views"]["flowStudio"]
    view_ids = {v["id"] for v in views}
    assert {"flowSpecsTree", "flowCatalogTree"} <= view_ids

    cmd_ids = {c["command"] for c in contributes["commands"]}
    assert {
        "flow.openStudio",
        "flow.newSpec",
        "flow.searchCatalog",
        "flow.dispatchTask",
        "flow.runEntrypoint",
        "flow.selectTargetHarness",
    } <= cmd_ids

    props = contributes["configuration"]["properties"]
    assert "flow.defaultHarness" in props
    assert "flow.executionMode" in props
    assert set(props["flow.executionMode"]["enum"]) == {
        "direct-workspace",
        "worktree-isolated",
        "read-only",
    }


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_providers_codelens_and_webview_bridge(tmp_path: Path) -> None:
    """Verify SpecsTreeProvider, CatalogTreeProvider, SpecCodeLensProvider, and Webview API routing."""
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
    joinPath: (base, ...parts) => ({
      fsPath: [base.fsPath, ...parts].join("/"),
      toString: () => `vscode-webview://${[base.fsPath, ...parts].join("/")}`,
    }),
  },
  ViewColumn: { One: 1, Beside: 2 },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: wsPath } }],
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
    openTextDocument: async (uri) => ({ uri }),
  },
  window: {
    registerTreeDataProvider: (id, provider) => {
      treeProviders.set(id, provider);
      return { dispose() {} };
    },
    createWebviewPanel: () => {
      capturedPanel = {
        webview: {
          html: "",
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
    showInputBox: async () => "DuckDB",
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

const specsTree = treeProviders.get("flowSpecsTree");
const rootSpecs = await specsTree.getChildren();
const childChapters = await specsTree.getChildren(rootSpecs[0]);

const catalogTree = treeProviders.get("flowCatalogTree");
const rootCatalog = await catalogTree.getChildren();

const specLines = [
  "---",
  "flow_id: studio-ui",
  "state: active",
  "current_chapter: ch01-core",
  "---",
  "# Studio UI",
  "## 5. Implementation Plan",
].join("\\n");
const lenses = await codeLensProviders[0].provideCodeLenses({
  uri: { fsPath: `${wsPath}/.agents/bundles/specs/studio-ui/spec.md` },
  getText: () => specLines,
});

await registeredCommands.get("flow.openStudio")();
await webviewMessageListener({
  type: "apiRequest",
  id: 42,
  routePath: "/api/bundle-snapshot",
  payload: { workspacePath: wsPath },
});
await webviewMessageListener({
  type: "dispatchPrompt",
  workspacePath: wsPath,
  message: "/flow:implement studio-ui ch01-core",
});

await mod.deactivate();

process.stdout.write(JSON.stringify({
  specLabels: rootSpecs.map((item) => item.label),
  chapterLabels: childChapters.map((item) => item.label),
  catalogLabels: rootCatalog.map((item) => item.label),
  lensTitles: lenses.map((l) => l.command.title),
  webviewHtml: capturedPanel ? capturedPanel.webview.html : "",
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
    assert any("Studio UI" in lbl for lbl in out["specLabels"])
    assert any("ch01-core" in lbl for lbl in out["chapterLabels"])
    assert any("DuckDB Catalog" in lbl or "architecture" in lbl.lower() for lbl in out["catalogLabels"])
    assert any("Flow Studio" in t for t in out["lensTitles"])
    assert "flow-vscode-theme-bridge" in out["webviewHtml"]
    assert "--vscode-editor-background" in out["webviewHtml"]
    api_resp = next(m for m in out["postedWebviewMessages"] if m.get("type") == "apiResponse" and m.get("id") == 42)
    assert api_resp["result"]["specs"][0]["flowId"] == "studio-ui"
    assert any(cmd["id"] == "workbench.action.chat.open" for cmd in out["executedHostCommands"])


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
};

const mod = await import(extUrl);
const extUri = vscodeMock.Uri.file(process.argv[4]);
const context = { extensionPath: process.argv[4], extensionUri: extUri, subscriptions: [] };
await mod.activateWithVscode(context, vscodeMock);

const specsTree = treeProviders.get("flowSpecsTree");
const initialSpecs = await specsTree.getChildren();

await registeredCommands.get("flow.openStudio")();
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
    assert str(ws_beta) in out["webviewHtml"]
    ctx_resp = next(m for m in out["postedWebviewMessages"] if m.get("type") == "apiResponse" and m.get("id") == 1)
    assert ctx_resp["result"]["defaultWorkspace"] == str(ws_beta)
    assert str(ws_alpha) in ctx_resp["result"]["workspaces"]
    ws_events = [
        m["event"]
        for m in out["postedWebviewMessages"]
        if m.get("type") == "studioEvent" and m.get("event", {}).get("type") == "workspace.changed"
    ]
    assert any(ev["workspacePath"] == str(ws_alpha) for ev in ws_events)


@pytest.mark.skipif(NODE_BIN is None, reason="node is required")
def test_vscode_extension_installer_creates_self_contained_bundle(tmp_path: Path) -> None:
    """Verify vscode-extension/install.mjs bundles extension.mjs and sidecars/studio/ into an extensions dir."""
    assert NODE_BIN is not None
    ext_dir = tmp_path / "extensions"
    installer = EXT_DIR / "install.mjs"
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
    assert (bundle_dir / "package.json").is_file()
    assert (bundle_dir / "README.md").is_file()
    assert (bundle_dir / "extension.mjs").is_file()
    assert (bundle_dir / "sidecars" / "studio" / "router.mjs").is_file()
    assert "./sidecars/studio/" in (bundle_dir / "extension.mjs").read_text(encoding="utf-8")
