"""Public-seam tests for Flow Studio snapshot, review comments, spec creation, sidecar SDK, and HTTP server."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT

NODE_BIN = shutil.which("node")
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _free_port() -> int:
    """Bind an ephemeral loopback socket to reserve an unused TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _seed_studio_workspace(base_dir: Path) -> Path:
    """Create a multi-chapter Flow workspace for Studio UI and API verification."""
    ws = base_dir / "payments-service"
    ch01 = ws / ".agents" / "bundles" / "specs" / "idempotent-webhooks" / "chapters" / "ch01-dedup-store"
    tasks_dir = ch01 / "tasks"
    patterns_dir = ws / ".agents" / "bundles" / "knowledge" / "patterns"
    tasks_dir.mkdir(parents=True)
    patterns_dir.mkdir(parents=True)

    (ws / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (ws / "pyproject.toml").write_text(
        '[project]\nname = "payments-service"\n[project.scripts]\npayments-api = "payments.cli:main"\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "setup-state.json").write_text(
        '{"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "index.md").write_text(
        '---\nokf_version: "0.2"\nbundle: payments-service\n---\n\n# Payments Bundle\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "idempotent-webhooks" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: idempotent-webhooks\n"
        "title: Idempotent Webhook Ingestion\n"
        "description: Deduplicates inbound provider events using advisory keys.\n"
        "status: draft\n"
        "state: active\n"
        "has_chapters: true\n"
        "current_chapter: ch01-dedup-store\n"
        "---\n\n"
        "# Idempotent Webhook Ingestion\n\n"
        "## 1. Problem\n\nPrevent duplicate ledger entries on webhook retries.\n",
        encoding="utf-8",
    )
    (ch01 / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "chapter_id: ch01-dedup-store\n"
        "title: Chapter 01 Dedup Store\n"
        "status: draft\n"
        "state: active\n"
        "---\n\n"
        "# Chapter 01 Dedup Store\n\n"
        "- [x] [a1b2c3d] `t01` — Create event receipt table\n"
        "- [ ] `t02` — Enforce unique idempotency key\n",
        encoding="utf-8",
    )
    (tasks_dir / "t01-receipt-table.md").write_text(
        "---\n"
        "id: idempotent-webhooks:t01\n"
        "title: Create event receipt table\n"
        "state: completed\n"
        "commit_sha: a1b2c3d\n"
        "files: [src/webhooks/store.py]\n"
        "---\n\n"
        "# Task t01\n",
        encoding="utf-8",
    )
    (tasks_dir / "t02-unique-key.md").write_text(
        "---\n"
        "id: idempotent-webhooks:t02\n"
        "title: Enforce unique idempotency key\n"
        "state: pending\n"
        "files: [src/webhooks/handler.py]\n"
        "---\n\n"
        "# Task t02\n",
        encoding="utf-8",
    )
    (patterns_dir / "outbox.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Transactional Outbox Delivery\n"
        "description: Publishes domain events atomically alongside state commits.\n"
        "status: stable\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Insert outbox records in the same database transaction as aggregate mutations.\n"
        "<!-- truth: end -->\n",
        encoding="utf-8",
    )
    return ws


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Send a JSON POST request to the loopback server and parse the JSON response."""
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    with _DIRECT_OPENER.open(req, timeout=10) as resp:
        parsed: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        return parsed


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_standalone_studio_server_snapshot_review_and_spec_creation(tmp_path: Path) -> None:
    """Verify server.mjs serves calm Studio assets, bundle snapshots, review comments, and spec scaffolding."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    port = _free_port()
    db_path = tmp_path / "studio-test.duckdb"
    ws_cfg = tmp_path / "workspaces.json"

    env = {
        **os.environ,
        "FLOW_STUDIO_PORT": str(port),
        "FLOW_STUDIO_DEFAULT_WORKSPACE": str(ws),
        "FLOW_CATALOG_DB": str(db_path),
        "FLOW_CATALOG_EMBEDDER": "deterministic",
        "FLOW_WORKSPACES_CONFIG": str(ws_cfg),
    }
    proc = subprocess.Popen(
        [NODE_BIN, str(REPO_ROOT / "sidecars" / "studio" / "server.mjs"), "--no-open"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        ready = False
        for _ in range(40):
            try:
                with _DIRECT_OPENER.open(f"{base_url}/dashboard", timeout=1) as html_resp:
                    html = html_resp.read().decode("utf-8")
                    if "Flow Studio" in html:
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)
        assert ready, "Standalone Flow Studio server failed to start on loopback"

        snap = _post_json(f"{base_url}/api/bundle-snapshot", {"workspacePath": str(ws)})
        assert snap["repoName"] == "payments-service"
        assert snap["python"]["manager"] == "uv"
        assert "payments-api" in snap["python"]["entrypoints"]
        assert len(snap["specs"]) == 1
        spec = snap["specs"][0]
        assert spec["flowId"] == "idempotent-webhooks"
        assert spec["completedTasks"] == 1
        assert spec["totalTasks"] == 2
        assert spec["recommendedAction"]["command"] == "/flow:implement idempotent-webhooks ch01-dedup-store"

        spec_rel = ".agents/bundles/specs/idempotent-webhooks/spec.md"
        doc = _post_json(
            f"{base_url}/api/spec-document",
            {"workspacePath": str(ws), "relPath": spec_rel},
        )
        assert doc["title"] == "Idempotent Webhook Ingestion"
        assert len(doc["lines"]) >= 12

        added = _post_json(
            f"{base_url}/api/review-comments",
            {
                "action": "add",
                "workspacePath": str(ws),
                "relPath": spec_rel,
                "startLine": 12,
                "endLine": 14,
                "quote": "Prevent duplicate ledger entries",
                "body": "Specify a 7-day TTL retention policy for deduplication keys.",
            },
        )
        assert added["comment"]["startLine"] == 12
        assert "Specify a 7-day TTL" in added["revisePrompt"]
        assert "/flow:revise idempotent-webhooks" in added["revisePrompt"]

        created = _post_json(
            f"{base_url}/api/create-spec",
            {
                "workspacePath": str(ws),
                "flowId": "ledger-reconciliation",
                "title": "Daily Ledger Reconciliation",
                "kind": "Spec",
                "hasChapters": True,
                "problem": "Detect settlement discrepancies within 15 minutes.",
            },
        )
        assert created["flowId"] == "ledger-reconciliation"
        assert created["dispatchCommand"].startswith("/flow:spec ledger-reconciliation")
        assert (ws / created["relPath"]).is_file()

        cat_hits = _post_json(
            f"{base_url}/api/catalog-search",
            {"workspacePath": str(ws), "query": "transactional outbox aggregate", "mode": "hybrid"},
        )
        assert len(cat_hits["hits"]) >= 1
        assert cat_hits["hits"][0]["concept_id"] == "knowledge/patterns/outbox"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_antigravity_mcp_app_server_capabilities_resources_and_api_bridge(tmp_path: Path) -> None:
    """Verify mcp-server.mjs negotiates MCP App capabilities, bundles CSP-safe HTML, and bridges StudioApiService."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    mcp_uri = (REPO_ROOT / "sidecars" / "studio" / "mcp-server.mjs").as_uri()

    probe_js = f"""
import {{ createMcpSession }} from {json.dumps(mcp_uri)};

const ws = process.argv[1];
const uiSession = createMcpSession({{ defaultWorkspace: ws }});
const cliSession = createMcpSession({{ defaultWorkspace: ws }});

const uiInit = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {{
    capabilities: {{
      extensions: {{
        "io.modelcontextprotocol/ui": {{}},
        "com.google.antigravity/ui": {{ entrypoints: ["aux_pane", "global"] }},
      }},
    }},
  }},
}});
const uiTools = await uiSession.handle({{ jsonrpc: "2.0", id: 2, method: "tools/list" }});
const uiResources = await uiSession.handle({{ jsonrpc: "2.0", id: 3, method: "resources/list" }});
const studioHtml = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 4,
  method: "resources/read",
  params: {{ uri: "ui://flow/studio.html" }},
}});
const statusCardHtml = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 5,
  method: "resources/read",
  params: {{ uri: "ui://flow/status-card.html" }},
}});
const launchRes = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 6,
  method: "tools/call",
  params: {{ name: "flow_studio", arguments: {{}} }},
}});
const snapRes = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 7,
  method: "tools/call",
  params: {{
    name: "flow_studio_api",
    arguments: {{ route: "/api/bundle-snapshot", payload: {{ workspacePath: ws }} }},
  }},
}});
const badRouteRes = await uiSession.handle({{
  jsonrpc: "2.0",
  id: 8,
  method: "tools/call",
  params: {{ name: "flow_studio_api", arguments: {{ route: "/api/does-not-exist", payload: {{}} }} }},
}});

await cliSession.handle({{ jsonrpc: "2.0", id: 1, method: "initialize", params: {{ capabilities: {{}} }} }});
const cliTools = await cliSession.handle({{ jsonrpc: "2.0", id: 2, method: "tools/list" }});

uiSession.close();
cliSession.close();

process.stdout.write(JSON.stringify({{
  uiCaps: uiInit.result.capabilities,
  uiToolNames: uiTools.result.tools.map((t) => t.name),
  studioTool: uiTools.result.tools.find((t) => t.name === "flow_studio"),
  statusTool: uiTools.result.tools.find((t) => t.name === "flow_status"),
  apiTool: uiTools.result.tools.find((t) => t.name === "flow_studio_api"),
  cliToolNames: cliTools.result.tools.map((t) => t.name),
  cliStudioTool: cliTools.result.tools.find((t) => t.name === "flow_studio"),
  resourceUris: uiResources.result.resources.map((r) => r.uri),
  studioContent: studioHtml.result.contents[0],
  statusCardContent: statusCardHtml.result.contents[0],
  launchRes: launchRes.result,
  snapRepo: snapRes.result.structuredContent.repoName,
  badRouteError: badRouteRes.error,
}}) + "\\n");
"""
    run_res = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", probe_js, str(ws)],
        env={**os.environ, "FLOW_WORKSPACES_CONFIG": str(tmp_path / "ws.json")},
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(run_res.stdout.strip().splitlines()[-1])

    assert "io.modelcontextprotocol/ui" in out["uiCaps"]["extensions"]
    assert "flow_studio" in out["uiToolNames"]
    assert "flow_studio_api" in out["uiToolNames"]
    assert "flow_studio_api" not in out["cliToolNames"]
    assert "_meta" not in out["cliStudioTool"]

    assert "com.google.antigravity/ui" not in out["studioTool"]["_meta"]
    assert out["studioTool"]["_meta"]["ui"]["resourceUri"] == "ui://flow/studio.html"
    assert out["statusTool"]["_meta"]["ui"]["resourceUri"] == "ui://flow/status-card.html"
    assert out["apiTool"]["_meta"]["ui"]["visibility"] == ["app"]

    html_text = out["studioContent"]["text"]
    assert out["studioContent"]["mimeType"] == "text/html;profile=mcp-app"
    assert len(html_text.encode("utf-8")) < 10 * 1024 * 1024
    assert "<script src=" not in html_text
    assert '<link rel="stylesheet"' not in html_text
    assert "__MCP_EXT_APPS__" in html_text
    assert "__FLOW_MCP_APP__" in html_text

    card_text = out["statusCardContent"]["text"]
    assert out["statusCardContent"]["mimeType"] == "text/html;profile=mcp-app"
    assert "<script src=" not in card_text

    assert len(json.dumps(out["launchRes"]).encode("utf-8")) < 1024 * 1024
    assert out["snapRepo"] == "payments-service"
    assert out["badRouteError"]["code"] == -32602


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_sidecar_host_bridge_uses_get_reads_and_bounded_workspace_timeout() -> None:
    """Verify Antigravity sidecar mode uses GET for read routes and bounds getWorkspaceUris() in Sidebar views."""
    assert NODE_BIN is not None
    sidecar_json = json.loads((REPO_ROOT / "sidecars" / "studio" / "sidecar.json").read_text(encoding="utf-8"))
    assert sidecar_json["has_web_ui"] is True
    view_entrypoints = {v["entrypoint"] for v in sidecar_json["ui_config"]["views"]}
    assert view_entrypoints == {"SIDECAR_UI_ENTRYPOINT_AUX_PANE", "SIDECAR_UI_ENTRYPOINT_SIDEBAR"}

    bridge_path_json = json.dumps(str(REPO_ROOT / "sidecars" / "studio" / "web" / "host-bridge.js"))
    probe_js = f"""
import fs from "node:fs";
import vm from "node:vm";

const bridgeSrc = fs.readFileSync({bridge_path_json}, "utf8");
const calls = [];
const sandbox = {{
  URL,
  URLSearchParams,
  setTimeout,
  clearTimeout,
  queueMicrotask,
  encodeURIComponent,
  fetch: async (url, init = {{}}) => {{
    calls.push({{ url: String(url), method: init.method || "GET", headers: init.headers || {{}} }});
    return {{ ok: true, status: 200, async json() {{ return {{ ok: true }}; }} }};
  }},
  window: {{
    location: {{ pathname: "/dashboard", search: "" }},
    sidecar: {{
      conversationId: "",
      getWorkspaceUris: () => new Promise(() => {{}}),
      onWorkspaceChange: () => () => {{}},
      fetch: async (url, init = {{}}) => {{
        calls.push({{ viaSidecarFetch: true, url: String(url), method: init.method || "GET" }});
        return {{ ok: true, status: 200, async json() {{ return {{ ok: true }}; }} }};
      }},
      ui: {{ toggleAuxPane: () => {{}} }},
    }},
  }},
}};
sandbox.globalThis = sandbox;
vm.runInNewContext(bridgeSrc, sandbox);
const host = sandbox.window.flowHost;
const t0 = Date.now();
const uris = await host.getInitialWorkspaceUris(60);
const elapsed = Date.now() - t0;
await host.api("/api/studio-context", {{ workspacePath: "/tmp/demo" }});
await host.api("/api/review-comments", {{ action: "list", workspacePath: "/tmp/demo" }});
await host.api("/api/pin-workspace", {{ workspacePath: "/tmp/demo", pinned: true }});
process.stdout.write(JSON.stringify({{
  kind: host.kind,
  isCompanionView: host.isCompanionView,
  uris,
  elapsed,
  calls,
}}) + "\\n");
"""
    proc = subprocess.run([NODE_BIN, "--input-type=module", "-e", probe_js], capture_output=True, text=True, check=True)
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["kind"] == "antigravity"
    assert out["isCompanionView"] is False
    assert out["uris"] == []
    assert out["elapsed"] < 1000
    assert out["calls"][0]["method"] == "GET"
    assert out["calls"][0]["url"].startswith("/api/studio-context?payload=")
    assert out["calls"][1]["method"] == "GET"
    assert out["calls"][1]["url"].startswith("/api/review-comments?payload=")
    assert out["calls"][2]["method"] == "POST"
    assert out["calls"][2]["viaSidecarFetch"] is True


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_studio_active_workspace_discovery_and_sidecar_filtering(tmp_path: Path) -> None:
    """Verify StudioApiService filters out sidecars/studio, follows active workspaces, and auto-derives spec slugs."""
    assert NODE_BIN is not None
    ws_one = _seed_studio_workspace(tmp_path / "one")
    ws_two = _seed_studio_workspace(tmp_path / "two")
    cfg_dir = tmp_path / "flow-cfg"
    cfg_dir.mkdir(parents=True)
    ws_cfg = cfg_dir / "workspaces.json"
    recent_file = cfg_dir / "recent-workspaces.tsv"
    polluted_sidecar = str(REPO_ROOT / "sidecars" / "studio")
    ws_cfg.write_text(
        json.dumps(
            {
                "lastActiveWorkspace": polluted_sidecar,
                "workspaces": [polluted_sidecar, "/nonexistent/fake/workspace"],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["sh", str(REPO_ROOT / "hooks" / "session-start.sh"), "--harness", "agy"],
        input=json.dumps({"workspacePaths": [str(ws_one)]}),
        env={**os.environ, "FLOW_CONFIG_DIR": str(cfg_dir)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert recent_file.is_file()
    assert ws_one.as_posix() in recent_file.read_text(encoding="utf-8").replace("\\", "/")

    probe_js = """
import { pathToFileURL } from "node:url";
const routerMod = await import(pathToFileURL(process.argv[1]).href);
const wsOne = process.argv[2];
const wsTwo = process.argv[3];
const cfgDir = process.argv[4];
const wsCfg = process.argv[5];

const service = new routerMod.StudioApiService({
  env: {
    ...process.env,
    ANTIGRAVITY_LS_ADDRESS: "",
    FLOW_CONFIG_DIR: cfgDir,
    FLOW_WORKSPACES_CONFIG: wsCfg,
    FLOW_CATALOG_DB: `${cfgDir}/cat.duckdb`,
  },
});

const ctxFromHook = await service.handleApi("/api/studio-context", {});
const ctxFromHostUris = await service.handleApi("/api/studio-context", {
  activeWorkspaceUris: [pathToFileURL(wsTwo).href, pathToFileURL(wsOne).href],
});
const createdAutoSlug = await service.handleApi("/api/create-spec", {
  title: "Follow Selected Workspace",
  kind: "Spec",
  problem: "Keep Studio synchronized with the active workspace.",
  hasChapters: true,
});

process.stdout.write(JSON.stringify({
  hookDefaultWs: ctxFromHook.defaultWorkspace,
  hookWorkspaces: ctxFromHook.workspaces,
  hostActiveWs: ctxFromHostUris.defaultWorkspace,
  hostWorkspaces: ctxFromHostUris.workspaces,
  createdFlowId: createdAutoSlug.flowId,
  createdAbsPath: createdAutoSlug.absPath,
}) + "\\n");
service.close();
"""
    proc = subprocess.run(
        [
            NODE_BIN,
            "--input-type=module",
            "-e",
            probe_js,
            str(REPO_ROOT / "sidecars" / "studio" / "router.mjs"),
            str(ws_one),
            str(ws_two),
            str(cfg_dir),
            str(ws_cfg),
        ],
        cwd=str(REPO_ROOT / "sidecars" / "studio"),
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["hookDefaultWs"] == str(ws_one)
    assert polluted_sidecar not in out["hookWorkspaces"]
    assert out["hostActiveWs"] == str(ws_two)
    assert out["hostWorkspaces"][0] == str(ws_two)
    assert str(ws_one) in out["hostWorkspaces"]
    assert out["createdFlowId"] == "follow-selected-workspace"
    assert Path(out["createdAbsPath"]).is_file()
    assert ws_two.as_posix() in out["createdAbsPath"].replace("\\", "/")


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_host_bridge_mcp_app_concurrency_queue_dispatch_context_and_open_file(tmp_path: Path) -> None:
    """Verify host-bridge.js MCP App driver throttles tool calls, sends messages, attaches context, and opens files."""
    assert NODE_BIN is not None
    ws_active = tmp_path / "active-repo"
    ws_active.mkdir()

    probe_js = """
import fs from "node:fs";
import vm from "node:vm";

const bridgePath = process.argv[1];
const wsActive = process.argv[2];

let inflight = 0;
let peakInflight = 0;
const serverCalls = [];
const sentMessages = [];
const attachedContexts = [];
const openedFiles = [];
const appliedThemes = [];

class MockMcpApp {
  constructor() {
    this.ontoolinput = null;
    this.ontoolresult = null;
    this.onhostcontextchanged = null;
  }
  async connect() {}
  getHostCapabilities() {
    return { serverTools: {}, message: {}, updateModelContext: {}, openLinks: {} };
  }
  getHostContext() {
    return { theme: "dark", styles: { variables: { "--color-background-primary": "#111" } } };
  }
  async callServerTool({ name, arguments: args }) {
    inflight += 1;
    peakInflight = Math.max(peakInflight, inflight);
    serverCalls.push({ name, route: args.route });
    await new Promise((r) => setTimeout(r, 15));
    inflight -= 1;
    return { content: [{ type: "text", text: "ok" }], structuredContent: { route: args.route, ok: true } };
  }
  async sendMessage(msg) {
    sentMessages.push(msg);
  }
  async updateModelContext(ctx) {
    attachedContexts.push(ctx);
  }
}

let mockAppInstance = null;
const docAttrs = {};
const sandboxWindow = {
  __FLOW_MCP_APP__: true,
  __MCP_EXT_APPS__: {
    App: class extends MockMcpApp {
      constructor(...a) {
        super(...a);
        mockAppInstance = this;
      }
    },
    applyDocumentTheme: (t) => appliedThemes.push(t),
    applyHostStyleVariables: () => {},
    toggleAuxPaneFile: async (_app, uri) => {
      openedFiles.push(uri);
      return { isError: false };
    },
  },
  document: {
    documentElement: {
      setAttribute: (k, v) => { docAttrs[k] = v; },
    },
  },
  location: { pathname: "/", search: "" },
  navigator: { clipboard: { writeText: async () => {} } },
  URL,
  URLSearchParams,
  setTimeout,
  clearTimeout,
  queueMicrotask,
};
sandboxWindow.window = sandboxWindow;

const code = fs.readFileSync(bridgePath, "utf8");
vm.runInNewContext(code, sandboxWindow);

const host = sandboxWindow.flowHost;
const toolResults = [];
host.onToolResult((p) => toolResults.push(p));
mockAppInstance.ontoolresult({ structuredContent: { workspace: wsActive, initialTab: "review" } });

const parallelResults = await Promise.all([
  host.api("/api/studio-context", {}),
  host.api("/api/bundle-snapshot", { workspacePath: wsActive }),
  host.api("/api/activity", { workspacePath: wsActive }),
  host.api("/api/harnesses", { workspacePath: wsActive }),
  host.api("/api/permissions", { workspacePath: wsActive }),
  host.api("/api/catalog-status", { workspacePath: wsActive }),
]);

const dispatchRes = await host.dispatchPrompt({ workspacePath: wsActive, message: "/flow:spec demo" });
const newConvRes = await host.dispatchPrompt({ workspacePath: wsActive, message: "/flow:review demo", startNew: true });
const ctxRes = await host.attachContext("Open notes for demo");
const opened = await host.openFile(wsActive, ".agents/bundles/specs/demo/spec.md");

process.stdout.write(JSON.stringify({
  kind: host.kind,
  peakInflight,
  parallelCount: parallelResults.length,
  serverCallsCount: serverCalls.length,
  dispatchRes,
  newConvRes,
  sentMessages,
  ctxRes,
  attachedContexts,
  opened,
  openedFiles,
  appliedThemes,
  docAttrs,
  toolResults,
}) + "\\n");
"""
    proc = subprocess.run(
        [
            NODE_BIN,
            "--input-type=module",
            "-e",
            probe_js,
            str(REPO_ROOT / "sidecars" / "studio" / "web" / "host-bridge.js"),
            str(ws_active),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["kind"] == "mcp-app"
    assert out["peakInflight"] <= 3
    assert out["parallelCount"] == 6
    assert out["serverCallsCount"] == 6
    assert out["dispatchRes"]["mode"] == "mcp-message"
    assert out["newConvRes"]["mode"] == "new-conversation"
    assert out["sentMessages"][1]["_meta"]["com.google.antigravity/message"]["target"] == "new"
    assert out["ctxRes"]["attached"] is True
    assert out["opened"] is True
    assert out["openedFiles"][0].endswith("/.agents/bundles/specs/demo/spec.md")
    assert out["appliedThemes"] == ["dark"]
    assert out["toolResults"][0]["workspace"] == str(ws_active)


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_bundle_snapshot_surfaces_degraded_planning_and_resolves_linked_worktree(tmp_path: Path) -> None:
    """Verify BundleSnapshotBuilder resolves local-only Git worktrees to main .agents and surfaces degraded plans."""
    assert NODE_BIN is not None
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Flow Test",
        "GIT_AUTHOR_EMAIL": "flow@example.com",
        "GIT_COMMITTER_NAME": "Flow Test",
        "GIT_COMMITTER_EMAIL": "flow@example.com",
    }
    ws = _seed_studio_workspace(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "add", "pyproject.toml", "uv.lock"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: init"], cwd=ws, env=git_env, check=True)

    (ws / ".agents" / "setup-state.json").write_text(
        json.dumps(
            {
                "setup_status": "complete",
                "bundle_root": ".agents/bundles",
                "okf_version": "0.2",
                "workflow_preferences": {"ignore_policy": "local-only"},
            }
        ),
        encoding="utf-8",
    )
    spec_file = ws / ".agents" / "bundles" / "specs" / "idempotent-webhooks" / "spec.md"
    spec_file.write_text(
        spec_file.read_text(encoding="utf-8").replace(
            "state: active",
            (
                "state: active\n"
                "planning_quality: degraded\n"
                'planning_degraded_reason: "429 quota fallback"\n'
                "planned_with_model: flash"
            ),
        ),
        encoding="utf-8",
    )

    wt_dir = tmp_path / "wt-payments"
    subprocess.run(["git", "worktree", "add", "-q", "-b", "feat/wt", str(wt_dir)], cwd=ws, env=git_env, check=True)

    snap_uri = (REPO_ROOT / "sidecars" / "studio" / "snapshot.mjs").as_uri()
    spec_rel = ".agents/bundles/specs/idempotent-webhooks/spec.md"
    js = (
        f"import {{ BundleSnapshotBuilder, SpecMarkdownReader }} from {json.dumps(snap_uri)};"
        f"const snap = BundleSnapshotBuilder.build({json.dumps(str(wt_dir))});"
        f"const doc = SpecMarkdownReader.read({json.dumps(str(wt_dir))}, {json.dumps(spec_rel)});"
        "process.stdout.write(JSON.stringify({ snap, docTitle: doc.title }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    snap = payload["snap"]
    assert snap["worktree"]["isLinkedWorktree"] is True
    assert snap["worktree"]["ignorePolicy"] == "local-only"
    assert snap["bundleInitialized"] is True
    assert snap["counts"]["degradedSpecs"] == 1
    assert snap["specs"][0]["planningQuality"] == "degraded"
    assert snap["specs"][0]["planningDegradedReason"] == "429 quota fallback"
    assert snap["specs"][0]["plannedWithModel"] == "flash"
    assert payload["docTitle"] == "Idempotent Webhook Ingestion"


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_studio_snapshot_reads_runtime_heartbeat_ttl_and_claim_identity(tmp_path: Path) -> None:
    """Verify readStudioLiveState enforces 10-minute expiration with runtime/legacy fallback and parses claims."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    t02_path = (
        ws
        / ".agents"
        / "bundles"
        / "specs"
        / "idempotent-webhooks"
        / "chapters"
        / "ch01-dedup-store"
        / "tasks"
        / "t02-idempotency.md"
    )
    t02_path.write_text(
        "---\n"
        "type: Task\n"
        "id: idempotent-webhooks:ch01:t02\n"
        "state: in_progress\n"
        "claimed_by: agy:conv-coord-99:executor\n"
        "claimed_at: 2026-11-13T16:55:00Z\n"
        "---\n\n"
        "# Enforce unique idempotency key\n",
        encoding="utf-8",
    )

    rt_dir = tmp_path / "rt"
    snap_uri = (REPO_ROOT / "sidecars" / "studio" / "snapshot.mjs").as_uri()
    js = (
        "import fs from 'node:fs';"
        "import path from 'node:path';"
        f"import {{ BundleSnapshotBuilder, readStudioLiveState, workspaceRuntimeId }} from {json.dumps(snap_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        f"const rt = {json.dumps(str(rt_dir))};"
        "const wsId = workspaceRuntimeId(ws);"
        "const rtFile = path.join(rt, wsId, 'studio-live-state.json');"
        "fs.mkdirSync(path.dirname(rtFile), { recursive: true });"
        "const now = Date.now();"
        "const freshPayload = {"
        "  v: 1,"
        "  updatedAt: new Date(now - 2 * 60 * 1000).toISOString(),"
        "  activeTurn: true,"
        "  harness: 'agy',"
        "  conversationId: 'conv-1',"
        "  role: 'coordinator',"
        "  flowId: 'idempotent-webhooks',"
        "  chapterId: 'ch01-dedup-store',"
        "  taskIds: ['t02'],"
        "  worktree: ws,"
        "  activity: 'edit_file t02',"
        "};"
        "fs.writeFileSync(rtFile, JSON.stringify(freshPayload));"
        "const readOpts = { agentsDir: path.join(ws, '.agents'), env: { FLOW_RUNTIME_DIR: rt }, nowMs: now };"
        "const freshState = readStudioLiveState(ws, readOpts);"
        "const expiredPayload = {"
        "  v: 1,"
        "  updatedAt: new Date(now - 11 * 60 * 1000).toISOString(),"
        "  activeTurn: true,"
        "  harness: 'agy',"
        "  conversationId: 'conv-1',"
        "};"
        "fs.writeFileSync(rtFile, JSON.stringify(expiredPayload));"
        "const expiredState = readStudioLiveState(ws, readOpts);"
        "fs.unlinkSync(rtFile);"
        "const legacyPayload = {"
        "  updatedAt: new Date(now - 30 * 1000).toISOString(),"
        "  activeTurn: true,"
        "  harness: 'claude',"
        "  conversationId: 'conv-legacy',"
        "};"
        "fs.writeFileSync(path.join(ws, '.agents', 'studio-live-state.json'), JSON.stringify(legacyPayload));"
        "const legacyState = readStudioLiveState(ws, readOpts);"
        "const snap = BundleSnapshotBuilder.build(ws);"
        "process.stdout.write(JSON.stringify({ freshState, expiredState, legacyState, snap }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    assert data["freshState"]["fresh"] is True
    assert data["freshState"]["activeTurn"] is True
    assert data["freshState"]["flowId"] == "idempotent-webhooks"
    assert data["expiredState"]["fresh"] is False
    assert data["expiredState"]["activeTurn"] is False
    assert data["legacyState"]["fresh"] is True
    assert data["legacyState"]["conversationId"] == "conv-legacy"

    tasks = data["snap"]["specs"][0]["chapters"][0]["tasks"]
    t02 = next(t for t in tasks if t["shortId"] == "t02")
    assert t02["claimedBy"] == "agy:conv-coord-99:executor"
    assert t02["claimedAt"] == "2026-11-13T16:55:00Z"
    assert t02["claimIdentity"] == {
        "raw": "agy:conv-coord-99:executor",
        "structured": True,
        "harness": "agy",
        "sessionId": "conv-coord-99",
        "role": "executor",
    }


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_spec_engine_preflight_dangling_dep_cross_chapter_collision_and_import_urls(tmp_path: Path) -> None:
    """Verify SpecEngine preflight catches dangling deps, isolates short_ids, and strips file:// URLs."""
    assert NODE_BIN is not None
    ws = tmp_path / "engine-ws"
    ch1 = ws / ".agents" / "bundles" / "specs" / "multi-ch" / "chapters" / "ch01-alpha" / "tasks"
    ch2 = ws / ".agents" / "bundles" / "specs" / "multi-ch" / "chapters" / "ch02-beta" / "tasks"
    ch1.mkdir(parents=True)
    ch2.mkdir(parents=True)
    (ws / "src").mkdir()
    (ws / "src" / "app.py").write_text("def handle():\n    return True\n", encoding="utf-8")
    (ws / ".agents" / "setup-state.json").write_text(
        '{"setup_status":"complete","bundle_root":".agents/bundles","okf_version":"0.2"}\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# Index\n", encoding="utf-8")
    (ws / ".agents" / "bundles" / "specs" / "multi-ch" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-ch\ntitle: Multi\nstate: active\nhas_chapters: true\n"
        "current_chapter: ch02-beta\nplan_revision: 1\n---\n\n- [x] ch01-alpha\n- [ ] ch02-beta\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "multi-ch" / "chapters" / "ch01-alpha" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-ch\nchapter_id: ch01-alpha\nstate: completed\n"
        "last_reviewed_commit: abc1234\nplan_revision: 1\n---\n\n- [x] [abc1234] t01\n",
        encoding="utf-8",
    )
    (ch1 / "t01-done.md").write_text(
        "---\ntype: Task\nid: multi-ch:ch01-alpha:t01\ntitle: Done\nstate: completed\ncommit: abc1234\n"
        "worksheet_format: compact\nverification_strategy: unit\ndepends_on: []\n"
        "read_set: [src/app.py]\nfiles: [src/generated.py]\ntests: []\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nDone.\n## Bounded Read Manifest\n- src/app.py\n"
        "## Contracts & Edge Cases\nNone.\n## Test Matrix\nUnit.\n## Verification\npytest\n"
        "## Acceptance Criteria\nDone.\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "multi-ch" / "chapters" / "ch02-beta" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-ch\nchapter_id: ch02-beta\nstate: active\nplan_revision: 1\n---\n\n"
        "- [ ] t01\n- [ ] t02\n",
        encoding="utf-8",
    )
    (ch2 / "t01-dep.md").write_text(
        "---\ntype: Task\nid: multi-ch:ch02-beta:t01\ntitle: Second Ch Open\nstate: pending\n"
        "worksheet_format: compact\nverification_strategy: unit\ndepends_on: [multi-ch:ch01-alpha:t01]\n"
        "read_set: [src/generated.py]\nfiles: [src/beta.py]\ntests: []\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nDep.\n## Bounded Read Manifest\n- src/generated.py\n"
        "## Contracts & Edge Cases\nNone.\n## Test Matrix\nUnit.\n## Verification\npytest\n"
        "## Acceptance Criteria\nDone.\n",
        encoding="utf-8",
    )
    (ch2 / "t02-dangling.md").write_text(
        "---\ntype: Task\nid: multi-ch:ch02-beta:t02\ntitle: Dangling\nstate: pending\n"
        "worksheet_format: compact\nverification_strategy: unit\ndepends_on: [t01, nonexistent-task]\n"
        "read_set: [src/app.py]\nfiles: [src/gamma.py]\ntests: []\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nDangle.\n## Bounded Read Manifest\n- src/app.py\n"
        "## Contracts & Edge Cases\nNone.\n## Test Matrix\nUnit.\n## Verification\npytest\n"
        "## Acceptance Criteria\nDone.\n",
        encoding="utf-8",
    )

    engine_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "spec-engine.mjs").as_uri()
    plan_md = (
        "# Imported API Plan\n\n"
        "## 1. Implement Handler\n\n"
        f"- Update [app.py](file://{(ws / 'src' / 'app.py').as_posix()}#L1-L2)\n"
    )
    js = (
        f"import {{ SpecEngine }} from {json.dumps(engine_uri)};"
        f"const engine = new SpecEngine({json.dumps(str(ws))});"
        "const pre = engine.preflight('multi-ch', { chapterId: 'ch02-beta' });"
        "const dag = engine.buildDag('multi-ch');"
        "const imp = engine.importPlan({"
        f"  markdownText: {json.dumps(plan_md)}, flowId: 'imported-api', sourcePath: 'implementation_plan.md'"
        "});"
        "process.stdout.write(JSON.stringify({ pre, dag, imp }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    codes = {f["code"] for f in out["pre"]["findings"]}
    assert "DANGLING_TASK_DEP" in codes
    assert "TARGET_PATH_MISSING" not in codes
    ready_ids = [t["id"] for t in out["pre"]["ready_tasks"]]
    assert "multi-ch:ch02-beta:t01" in ready_ids
    assert "multi-ch:ch02-beta:t02" not in ready_ids
    t02_edges = [e for e in out["dag"]["edges"] if e["target"] == "multi-ch:ch02-beta:t02"]
    assert all(e["source"] == "multi-ch:ch02-beta:t01" for e in t02_edges)

    task_files = [ws / p for p in out["imp"]["written_files"] if "/tasks/" in p]
    assert len(task_files) == 1
    imp_task = task_files[0].read_text(encoding="utf-8")
    assert "file://" not in imp_task
    assert "src/app.py" in imp_task


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_spec_feedback_store_collaborative_authors_upvotes_and_state(tmp_path: Path) -> None:
    """Verify SpecFeedbackStore stores per-author JSON files, upvotes, and state transitions cleanly."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    fb_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "feedback.mjs").as_uri()
    js = (
        f"import {{ SpecFeedbackStore }} from {json.dumps(fb_uri)};"
        f"const store = new SpecFeedbackStore({json.dumps(str(ws))});"
        "const rel = '.agents/bundles/specs/idempotent-webhooks/spec.md';"
        "const c1 = store.add({"
        "  flowId: 'idempotent-webhooks', relPath: rel, authorEmail: 'alice@example.com',"
        "  authorName: 'Alice', commentKind: 'change_request', body: 'Add retry backoff contract',"
        "  lineStart: 12, lineEnd: 14"
        "});"
        "const c2 = store.add({"
        "  flowId: 'idempotent-webhooks', relPath: rel, authorEmail: 'bob@example.com',"
        "  authorName: 'Bob', commentKind: 'approval'"
        "});"
        "const up = store.setResolvedOrUpdate("
        "  'idempotent-webhooks', c1.id, { toggleUpvote: true, actorEmail: 'bob@example.com' });"
        "const addr = store.setResolvedOrUpdate('idempotent-webhooks', c1.id, { state: 'addressed' });"
        "const listed = store.listForFlow('idempotent-webhooks', { viewerEmail: 'bob@example.com' });"
        "process.stdout.write(JSON.stringify({ c1, c2, up, addr, listed }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    fb_dir = ws / ".agents" / "bundles" / "specs" / "idempotent-webhooks" / "feedback"
    assert (fb_dir / "alice-example-com.json").is_file()
    assert (fb_dir / "bob-example-com.json").is_file()
    assert out["c2"]["body"] == "Approved."
    assert out["up"]["upvoteCount"] == 1
    assert out["addr"]["state"] == "addressed"
    alice_entry = next(item for item in out["listed"] if item["id"] == out["c1"]["id"])
    assert alice_entry["viewerHasUpvoted"] is True


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_mcp_server_and_claude_mod_hooks(tmp_path: Path) -> None:
    """Verify Flow MCP server tool/resource handlers and Claude Mod Agent tier/pack injection."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    mcp_uri = (REPO_ROOT / "sidecars" / "studio" / "mcp-server.mjs").as_uri()
    mod_uri = (REPO_ROOT / "mods" / "claude-flow" / "hooks" / "register.mjs").as_uri()
    js = (
        f"import {{ handleMcpRequest }} from {json.dumps(mcp_uri)};"
        f"import {{ register }} from {json.dumps(mod_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const initRes = await handleMcpRequest({ jsonrpc: '2.0', id: 1, method: 'initialize' },"
        "  { defaultWorkspace: ws });"
        "const toolsRes = await handleMcpRequest({ jsonrpc: '2.0', id: 2, method: 'tools/list' },"
        "  { defaultWorkspace: ws });"
        "const resRead = await handleMcpRequest({"
        "  jsonrpc: '2.0', id: 3, method: 'resources/read', params: { uri: 'ui://flow/studio' }"
        "}, { defaultWorkspace: ws });"
        "const tasksRes = await handleMcpRequest({"
        "  jsonrpc: '2.0', id: 4, method: 'tools/call',"
        "  params: { name: 'flow_tasks', arguments: { workspace: ws, flow_id: 'idempotent-webhooks' } }"
        "}, { defaultWorkspace: ws });"
        "const handlers = [];"
        "const on = (evt, filter, fn) => handlers.push({ evt, filter, fn });"
        "register(on, { workspaceRoot: ws });"
        "const toolHandler = handlers.find((h) => h.evt === 'tool.call').fn;"
        "const ev = { input: { subagent_type: 'executor', prompt: 'Implement webhook key uniqueness' } };"
        "await toolHandler({}, ev, async (arg) => arg);"
        "const aboveFn = handlers.find("
        "  (h) => h.evt === 'ui.render' && h.filter.component === 'AbovePrompt').fn;"
        "const banner = aboveFn("
        "  { ui: { resolve: () => ({ Box: (p, ...c) => ({ p, c }), Text: (p, t) => t }) } }, {});"
        "process.stdout.write(JSON.stringify({"
        "  initRes, toolsRes, resRead, tasksRes, modInput: ev.input, banner"
        "}) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env={**os.environ, "FLOW_RUNTIME_DIR": str(tmp_path / "rt")},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    assert out["initRes"]["result"]["serverInfo"]["name"] == "flow"
    tool_names = [t["name"] for t in out["toolsRes"]["result"]["tools"]]
    assert all(len(name) <= 20 for name in tool_names)
    assert "flow_tasks" in tool_names
    assert "<!doctype html>" in out["resRead"]["result"]["contents"][0]["text"].lower()
    assert out["tasksRes"]["result"]["structuredContent"]["steps"]
    assert out["modInput"]["subagent_type"].startswith("flow-model-")
    assert "FLOW TASK BRIEF" in out["modInput"]["prompt"]
    assert (ws / ".claude" / "agents" / "flow-model-strong.md").is_file()
    assert "idempotent-webhooks" in out["banner"]["c"][0]


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_spec_engine_sync_transitions_custom_columns_and_list_item_text(tmp_path: Path) -> None:
    """Verify colon YAML list items, completed transitions, header column lookup, and no-release-stale."""
    assert NODE_BIN is not None
    ws = tmp_path / "sync-ws"
    ch1 = ws / ".agents" / "bundles" / "specs" / "sync-flow" / "chapters" / "ch01-core" / "tasks"
    ch2 = ws / ".agents" / "bundles" / "specs" / "sync-flow" / "chapters" / "ch02-next" / "tasks"
    ch1.mkdir(parents=True)
    ch2.mkdir(parents=True)
    (ws / "src").mkdir()
    (ws / "src" / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    (ws / ".agents" / "setup-state.json").write_text(
        '{"setup_status":"complete","bundle_root":".agents/bundles","okf_version":"0.2"}\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# Index\n", encoding="utf-8")
    (ws / ".agents" / "bundles" / "specs" / "sync-flow" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: sync-flow\ntitle: Sync Flow\nstate: active\nhas_chapters: true\n"
        "current_chapter: ch01-core\ncurrent_task: null\nchapters: [ch01-core, ch02-next]\nplan_revision: 1\n---\n\n"
        "- [ ] ch01-core — Core work\n- [ ] ch02-next — Followup work\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "sync-flow" / "chapters" / "index.md").write_text(
        "# Chapters\n\n"
        "| Chapter | Depends on | State | Notes |\n"
        "| --- | --- | --- | --- |\n"
        "| ch01-core | none | active | core |\n"
        "| ch02-next | ch01-core | pending | followup ch01-core |\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "sync-flow" / "chapters" / "ch01-core" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: sync-flow\nchapter_id: ch01-core\nstate: active\nplan_revision: 1\n---\n\n"
        "- [ ] [t01](tasks/t01-base.md) — Base slice\n"
        "- [ ] [t02](tasks/t02-dep.md) — Downstream slice (depends on t01)\n",
        encoding="utf-8",
    )
    (ch1 / "t01-base.md").write_text(
        "---\ntype: Task\nid: sync-flow:ch01-core:t01\ntitle: Base\nstate: completed\ncommit: abc1234\n"
        "files: [src/mod.py]\ntests: []\ndepends_on: []\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nBase.\n",
        encoding="utf-8",
    )
    (ch1 / "t02-dep.md").write_text(
        "---\ntype: Task\nid: sync-flow:ch01-core:t02\ntitle: Downstream\nstate: pending\n"
        "files: [src/mod2.py]\ntests: []\ndepends_on:\n  - ch01-core: t01\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nDep.\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "sync-flow" / "chapters" / "ch02-next" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: sync-flow\nchapter_id: ch02-next\nstate: pending\nplan_revision: 1\n---\n\n"
        "- [ ] [t01](tasks/t01-sib.md) — Sibling slice\n",
        encoding="utf-8",
    )
    (ch2 / "t01-sib.md").write_text(
        "---\ntype: Task\nid: sync-flow:ch02-next:t01\ntitle: Sibling\nstate: in_progress\n"
        "claimed_by: slot-1\nclaimed_at: 2020-01-01T00:00:00.000Z\n"
        "files: [src/sib.py]\ntests: []\ndepends_on: []\nplan_revision: 1\n---\n\n"
        "## Objective & Scope Boundary\nSib.\n",
        encoding="utf-8",
    )

    fm_uri = (REPO_ROOT / "sidecars" / "studio" / "core" / "frontmatter.mjs").as_uri()
    engine_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "spec-engine.mjs").as_uri()
    js = (
        f"import {{ FrontmatterDocument }} from {json.dumps(fm_uri)};"
        f"import {{ SpecEngine }} from {json.dumps(engine_uri)};"
        f"const engine = new SpecEngine({json.dumps(str(ws))});"
        "const parsedDepList = FrontmatterDocument.parse("
        "  '---\\ndepends_on:\\n  - ch01-core: t01\\n---\\n\\nBody\\n'"
        ").textList('depends_on');"
        "const firstSync = engine.syncChecklists({ flowId: 'sync-flow', releaseStaleClaims: false });"
        f"const ch1SpecPath = {json.dumps(str(ws / '.agents/bundles/specs/sync-flow/chapters/ch01-core/spec.md'))};"
        "const ch1AfterFirstSync = fs.readFileSync(ch1SpecPath, 'utf8');"
        "const sibAfterSync1 = engine.status('sync-flow').spec.chapters"
        "  .flatMap((c) => c.tasks).find((t) => t.id === 'sync-flow:ch02-next:t01');"
        "const compRes = engine.completeTasks({"
        "  flowId: 'sync-flow',"
        "  completions: [{"
        "    taskId: 'sync-flow:ch01-core:t02',"
        "    status: 'completed',"
        "    commit_deferred_to_coordinator: true,"
        "  }],"
        "  releaseStaleClaims: false,"
        "});"
        "const statusDoneCh1 = engine.status('sync-flow');"
        "const ch1TextAfter = fs.readFileSync(ch1SpecPath, 'utf8');"
        "const rootTextAfter = fs.readFileSync("
        f"  {json.dumps(str(ws / '.agents' / 'bundles' / 'specs' / 'sync-flow' / 'spec.md'))}, 'utf8'"
        ");"
        "const idxTextAfter = fs.readFileSync("
        f"  {json.dumps(str(ws / '.agents' / 'bundles' / 'specs' / 'sync-flow' / 'chapters' / 'index.md'))}, 'utf8'"
        ");"
        "const claimReopen = engine.claimTasks({"
        "  flowId: 'sync-flow',"
        "  taskIds: ['sync-flow:ch01-core:t02'],"
        "  claimedBy: 'slot-2',"
        "});"
        "const rootAfterReopen = fs.readFileSync("
        f"  {json.dumps(str(ws / '.agents' / 'bundles' / 'specs' / 'sync-flow' / 'spec.md'))}, 'utf8'"
        ");"
        "process.stdout.write(JSON.stringify({"
        "  parsedDepList, firstSync, ch1AfterFirstSync,"
        "  sibState: sibAfterSync1.state, sibClaim: sibAfterSync1.claimed_by,"
        "  compRes, ch1State: statusDoneCh1.spec.chapters[0].state, rootState: statusDoneCh1.spec.state,"
        "  ch1TextAfter, rootTextAfter, idxTextAfter, claimReopen, rootAfterReopen"
        "}) + '\\n');"
    )
    js_with_fs = "import fs from 'node:fs';\n" + js
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js_with_fs],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    assert out["parsedDepList"] == ["ch01-core:t01"]
    assert out["sibState"] == "in_progress"
    assert out["sibClaim"] == "slot-1"
    assert "- [x] [abc1234] [t01](tasks/t01-base.md)" in out["ch1AfterFirstSync"]
    assert "- [ ] [t02](tasks/t02-dep.md)" in out["ch1AfterFirstSync"]
    assert "- [x] [t02](tasks/t02-dep.md)" in out["ch1TextAfter"]
    assert out["ch1State"] == "completed"
    assert "- [x] ch01-core" in out["rootTextAfter"]
    assert "ch01-core | none | completed | core" in out["idxTextAfter"]
    assert "ch02-next | ch01-core | active | followup ch01-core" in out["idxTextAfter"]
    assert out["compRes"]["completed"] == ["sync-flow:ch01-core:t02"]
    assert out["claimReopen"]["skipped"][0]["reason"] == "already_completed"


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_task_planner_and_spec_engine_cross_chapter_scheduling(tmp_path: Path) -> None:
    """Verify workers > 4, task grouping, test overlap conflicts, allReadyChapters, and excludes."""
    assert NODE_BIN is not None
    ws = tmp_path / "pack-ws"
    ch1 = ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch01-fast" / "tasks"
    ch2 = ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch02-parallel" / "tasks"
    ch3 = ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch03-emp" / "tasks"
    ch1.mkdir(parents=True)
    ch2.mkdir(parents=True)
    ch3.mkdir(parents=True)
    (ws / "Makefile").write_text("lint:\n\techo lint\ntest:\n\techo test\n", encoding="utf-8")
    (ws / "src").mkdir()
    for fname in ("a.py", "b.py", "c.py", "d.py", "e.py", "f.py"):
        (ws / "src" / fname).write_text("X = 1\n", encoding="utf-8")
    (ws / ".agents" / "setup-state.json").write_text(
        '{"setup_status":"complete","bundle_root":".agents/bundles","okf_version":"0.2"}\n',
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# Index\n", encoding="utf-8")
    (ws / ".agents" / "bundles" / "specs" / "multi-sched" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-sched\ntitle: Multi Scheduler\nstate: active\nhas_chapters: true\n"
        "current_chapter: ch01-fast\nchapters: [ch01-fast, ch02-parallel, ch03-emp]\nplan_revision: 1\n---\n\n"
        "- [ ] ch01-fast\n- [ ] ch02-parallel\n- [ ] ch03-emp\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch01-fast" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-sched\nchapter_id: ch01-fast\nstate: active\n"
        "planning_status: complete\n---\n\n- [ ] t01\n- [ ] t02\n- [ ] t03\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch02-parallel" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-sched\nchapter_id: ch02-parallel\nstate: pending\n"
        "planning_status: complete\n---\n\n- [ ] t01\n- [ ] t02\n",
        encoding="utf-8",
    )
    (ws / ".agents" / "bundles" / "specs" / "multi-sched" / "chapters" / "ch03-emp" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: multi-sched\nchapter_id: ch03-emp\nstate: pending\n"
        "planning_status: empirical_dependent\nreplan_trigger: after ch01 benchmarks\n---\n\n- [ ] t01\n",
        encoding="utf-8",
    )
    tasks_spec = [
        (ch1, "t01-a.md", "multi-sched:ch01-fast:t01", "src/a.py", "tests/test_shared.py", 30),
        (ch1, "t02-b.md", "multi-sched:ch01-fast:t02", "src/b.py", "tests/test_shared.py", 30),
        (ch1, "t03-a2.md", "multi-sched:ch01-fast:t03", "src/a.py", "tests/test_a2.py", 30),
        (ch2, "t01-c.md", "multi-sched:ch02-parallel:t01", "src/c.py", "tests/test_c.py", 20),
        (ch2, "t02-d.md", "multi-sched:ch02-parallel:t02", "src/d.py", "tests/test_d.py", 20),
        (ch3, "t01-e.md", "multi-sched:ch03-emp:t01", "src/e.py", "tests/test_e.py", 20),
    ]
    for folder, fname, tid, code_f, test_f, loc in tasks_spec:
        (folder / fname).write_text(
            f"---\ntype: Task\nid: {tid}\ntitle: {fname}\nstate: pending\n"
            f"files: [{code_f}]\ntests: [{test_f}]\nread_set: [{code_f}]\ndepends_on: []\n"
            f"estimated_loc: {loc}\n---\n\n## Objective & Scope Boundary\nWork.\n## Verification\nmake test\n",
            encoding="utf-8",
        )

    engine_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "spec-engine.mjs").as_uri()
    planner_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "task-planner.mjs").as_uri()
    js = (
        f"import {{ SpecEngine }} from {json.dumps(engine_uri)};"
        f"import {{ TaskPlanner }} from {json.dumps(planner_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const engine = new SpecEngine(ws);"
        "const preAll = engine.preflight('multi-sched', { allReadyChapters: true });"
        "const statusRes = engine.status('multi-sched');"
        "const imp = engine.importPlan({"
        "  markdownText: '# Demo Plan\\n\\n## 1. Item\\n\\n- Update src/a.py\\n',"
        "  flowId: 'auto-verify',"
        "  sourcePath: 'plan.md',"
        "});"
        "const planner = new TaskPlanner(ws);"
        "const crossPlan = planner.plan({"
        "  flowId: 'multi-sched', allReadyChapters: true, workers: 6,"
        "});"
        "const cappedPlan = planner.plan({"
        "  flowId: 'multi-sched', allReadyChapters: true, workers: 1,"
        "});"
        "const exclPlan = planner.plan({"
        "  flowId: 'multi-sched', allReadyChapters: true, workers: 6,"
        "  excludeTaskIds: ['multi-sched:ch01-fast:t01'],"
        "  excludePaths: ['tests/test_shared.py'],"
        "});"
        "process.stdout.write(JSON.stringify({"
        "  preAll, statusRes, imp, crossPlan, cappedPlan, exclPlan"
        "}) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    ready_ids = {t["id"] for t in out["preAll"]["ready_tasks"]}
    assert "multi-sched:ch01-fast:t01" in ready_ids
    assert "multi-sched:ch02-parallel:t01" in ready_ids
    assert "multi-sched:ch03-emp:t01" not in ready_ids
    assert out["statusRes"]["next_runnable"]["chapter_id"] != "ch03-emp"

    cross_steps = out["crossPlan"]["steps"]
    step0_tests = [t for grp in cross_steps[0]["tasks"] for t in grp.get("tests", [])]
    assert step0_tests.count("tests/test_shared.py") <= 1
    group_task_lists = [grp["task_ids"] for st in cross_steps for grp in st["tasks"]]
    expected_coalesced = {"multi-sched:ch01-fast:t01", "multi-sched:ch01-fast:t03"}
    assert any(len(ts) >= 2 and expected_coalesced.issubset(set(ts)) for ts in group_task_lists)

    assert len(out["cappedPlan"]["steps"][0]["tasks"]) == 1
    assert any(len(grp["task_ids"]) >= 2 for grp in out["cappedPlan"]["steps"][0]["tasks"])

    disp_task_ids = {tid for grp in out["exclPlan"]["ready_tasks"] for tid in grp["task_ids"]}
    assert "multi-sched:ch01-fast:t02" not in disp_task_ids
    assert "multi-sched:ch02-parallel:t01" in disp_task_ids
    assert any("tests/test_shared.py" in grp.get("tests", []) for st in out["exclPlan"]["steps"] for grp in st["tasks"])
    assert out["exclPlan"]["steps"][-1]["tasks"]

    imp_task_path = ws / next(p for p in out["imp"]["written_files"] if "/tasks/" in p)
    imp_text = imp_task_path.read_text(encoding="utf-8")
    assert "make lint" in imp_text or "make test" in imp_text


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_task_planner_atomic_groups_and_lock_scopes(tmp_path: Path) -> None:
    """Verify multi-file tasks stay indivisible and overlapping lock_scopes serialize across steps."""
    assert NODE_BIN is not None
    ws = tmp_path / "ws"
    (ws / ".agents").mkdir(parents=True)
    (ws / ".agents" / "setup-state.json").write_text(
        json.dumps({"schema_version": 1, "ignore_policy": "tracked", "sha_tracking": True}),
        encoding="utf-8",
    )
    flow_dir = ws / ".agents" / "bundles" / "specs" / "locks-demo"
    tasks_dir = flow_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (flow_dir / "spec.md").write_text(
        "---\nid: locks-demo\ntitle: Locks Demo\nstate: active\nplanning_status: complete\n---\n\n# Locks Demo\n",
        encoding="utf-8",
    )
    (tasks_dir / "t01-wide.md").write_text(
        "---\n"
        "type: Task\nid: locks-demo:t01\ntitle: Wide Task\nstate: pending\n"
        "files: [src/a.py, src/b.py, src/c.py, src/d.py]\ntests: [tests/test_wide.py]\n"
        "lock_scopes: [db/migrations]\ndepends_on: []\nestimated_loc: 320\n"
        "---\n\n## Objective & Scope Boundary\nWide change.\n## Verification\nmake test\n",
        encoding="utf-8",
    )
    (tasks_dir / "t02-lock.md").write_text(
        "---\n"
        "type: Task\nid: locks-demo:t02\ntitle: Lock Peer\nstate: pending\n"
        "files: [src/e.py]\ntests: [tests/test_e.py]\n"
        "lock_scopes: [db/migrations]\ndepends_on: []\nestimated_loc: 40\n"
        "---\n\n## Objective & Scope Boundary\nPeer change.\n## Verification\nmake test\n",
        encoding="utf-8",
    )

    planner_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "task-planner.mjs").as_uri()
    js = (
        f"import {{ TaskPlanner }} from {json.dumps(planner_uri)};"
        f"const planner = new TaskPlanner({json.dumps(str(ws))});"
        "process.stdout.write(JSON.stringify(planner.plan({ flowId: 'locks-demo', workers: 4 })) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    plan = json.loads(proc.stdout.strip().splitlines()[-1])

    assert plan["group_count"] == 2
    assert len(plan["steps"]) == 2
    first_group = plan["steps"][0]["tasks"][0]
    second_group = plan["steps"][1]["tasks"][0]
    assert first_group["group_id"] == "locks-demo:t01"
    assert len(first_group["files"]) == 4
    assert first_group["lock_scopes"] == ["db/migrations"]
    assert second_group["group_id"] == "locks-demo:t02"
    assert second_group["lock_scopes"] == ["db/migrations"]


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_flow_cli_entrypoint_and_shim_installer(tmp_path: Path) -> None:
    """Verify bin/flow.mjs, symlinked CliShimInstaller execution, and legacy wrapper delegation."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    bin_dir = tmp_path / "local-bin"
    env = {**os.environ, "FLOW_CLI_BIN_DIR": str(bin_dir), "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}

    flow_bin = REPO_ROOT / "bin" / "flow.mjs"
    install_proc = subprocess.run(
        [NODE_BIN, str(flow_bin), "install-cli", "--json"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    install_out = json.loads(install_proc.stdout)
    assert install_out["installed"] is True
    shim_path = Path(install_out["shim_path"])
    assert shim_path.exists()

    symlink_status = subprocess.run(
        [str(shim_path), "status", "--ws", str(ws), "--json"],
        cwd=str(ws),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    status_out = json.loads(symlink_status.stdout)
    assert status_out["specs"][0]["flow_id"] == "idempotent-webhooks"

    wrapper_proc = subprocess.run(
        [NODE_BIN, str(REPO_ROOT / "sidecars" / "studio" / "flow-cli.mjs"), "spec", "status", "--ws", str(ws)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    wrapper_out = json.loads(wrapper_proc.stdout)
    assert wrapper_out["specs"][0]["flow_id"] == "idempotent-webhooks"


def _init_git_repo(repo_dir: Path) -> None:
    """Initialize a local Git repository with signing disabled for fixture commits."""
    git_kw: dict[str, Any] = {"cwd": repo_dir, "check": True, "capture_output": True, "text": True, "encoding": "utf-8"}
    subprocess.run(["git", "init"], **git_kw)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], **git_kw)
    subprocess.run(["git", "config", "user.name", "Dev User"], **git_kw)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], **git_kw)


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize(
    ("sibling_dir_name", "expect_clean_tree"),
    (
        ("partner-feedback", True),
        ("review-feedback", True),
    ),
)
def test_out_of_tree_feedback_store_sibling_discovery_and_replies(
    tmp_path: Path,
    sibling_dir_name: str,
    expect_clean_tree: bool,
) -> None:
    """Verify out-of-tree <git-common-dir>/spec-feedback/, sibling merges, replies, edits, and asset confinement."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    _init_git_repo(ws)
    (ws / "assets").mkdir(parents=True, exist_ok=True)
    (ws / "assets" / "sample.txt").write_text("asset payload\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=ws, check=True, capture_output=True)

    sibling_file = ws / ".git" / sibling_dir_name / "idempotent-webhooks" / "peer-example-com.json"
    sibling_file.parent.mkdir(parents=True, exist_ok=True)
    sibling_file.write_text(
        json.dumps(
            [
                {
                    "id": "sibling-note-1",
                    "flowId": "idempotent-webhooks",
                    "relPath": ".agents/bundles/specs/idempotent-webhooks/spec.md",
                    "startLine": 5,
                    "endLine": 5,
                    "body": "Imported from sibling store.",
                    "commentKind": "question",
                    "authorEmail": "peer@example.com",
                    "authorName": "Peer",
                    "state": "open",
                }
            ]
        ),
        encoding="utf-8",
    )

    fb_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "feedback.mjs").as_uri()
    router_uri = (REPO_ROOT / "sidecars" / "studio" / "router.mjs").as_uri()
    js = (
        f"import {{ SpecFeedbackStore }} from {json.dumps(fb_uri)};"
        f"import {{ StudioApiService }} from {json.dumps(router_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const store = new SpecFeedbackStore(ws);"
        "const rootNote = store.add({"
        "  flowId: 'idempotent-webhooks', relPath: '.agents/bundles/specs/idempotent-webhooks/spec.md',"
        "  startLine: 8, endLine: 9, commentKind: 'change_request', body: 'Need idempotency TTL',"
        "  authorEmail: 'dev@example.com', authorName: 'Dev User'"
        "});"
        "const reply = store.replyToComment('idempotent-webhooks', rootNote.id, {"
        "  body: 'Set 7d default', authorEmail: 'dev@example.com', authorName: 'Dev User'"
        "});"
        "const edited = store.setResolvedOrUpdate('idempotent-webhooks', rootNote.id, { body: 'Updated TTL note' });"
        "const merged = store.listForFlow('idempotent-webhooks');"
        "const svc = new StudioApiService({ env: process.env });"
        "const asset = await svc.handleApi('/api/workspace-asset',"
        " { workspacePath: ws, relPath: 'assets/sample.txt' });"
        "let escaped = false;"
        "try { await svc.handleApi('/api/workspace-asset',"
        " { workspacePath: ws, relPath: '../escape.txt' }); } catch { escaped = true; }"
        "svc.close();"
        "process.stdout.write(JSON.stringify({ rootNote, reply, edited, merged, asset, escaped,"
        " dir: store.feedbackDirForFlow('idempotent-webhooks') }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])

    assert ".git/spec-feedback/idempotent-webhooks" in out["dir"].replace("\\", "/")
    assert len(out["merged"]) == 3
    assert any(c["id"] == "sibling-note-1" for c in out["merged"])
    assert out["reply"]["parentCommentId"] == out["rootNote"]["id"]
    assert out["edited"]["body"] == "Updated TTL note"
    assert out["asset"]["sizeBytes"] == len("asset payload\n")
    assert out["escaped"] is True
    if expect_clean_tree:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=ws, capture_output=True, text=True, check=True)
        assert st.stdout.strip() == ""


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_multi_branch_spec_scanner_puller_orphan_and_index_free_writer(tmp_path: Path) -> None:
    """Verify IndexFreeBranchWriter, GitBranchSpecScanner, OrphanSpecBranchSync, and SpecBranchPuller."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    _init_git_repo(ws)
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "main seed"], cwd=ws, check=True, capture_output=True)

    feat_spec_dir = ws / ".agents" / "bundles" / "specs" / "branch-feature"
    (feat_spec_dir / "tasks").mkdir(parents=True)
    (feat_spec_dir / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: branch-feature\ntitle: Feature Side\nstate: active\n---\n\n# Branch Feature\n",
        encoding="utf-8",
    )
    (feat_spec_dir / "tasks" / "t01-side.md").write_text(
        "---\ntype: Task\nid: branch-feature:t01\ntitle: Side task\nstate: pending\n---\n",
        encoding="utf-8",
    )

    git_uri = (REPO_ROOT / "sidecars" / "studio" / "core" / "git.mjs").as_uri()
    branch_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "git-spec-branch.mjs").as_uri()
    js_commit = (
        f"import {{ GitRunner, IndexFreeBranchWriter }} from {json.dumps(git_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const git = await GitRunner.forWorkspace(ws);"
        "const cur = await git.revParseVerify('HEAD', { abbrevRef: true });"
        "const commitRes = await IndexFreeBranchWriter.commitWorkspacePaths({"
        "  git, effectiveRoot: ws, targetBranch: 'feat/side-spec', baseBranch: cur,"
        "  relPaths: ['.agents/bundles/specs/branch-feature/spec.md',"
        " '.agents/bundles/specs/branch-feature/tasks/t01-side.md'],"
        "  message: 'spec(branch-feature): add feature spec on side branch'"
        "});"
        "process.stdout.write(JSON.stringify(commitRes) + '\\n');"
    )
    commit_proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js_commit],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    commit_out = json.loads(commit_proc.stdout.strip().splitlines()[-1])
    assert isinstance(commit_out, str) and len(commit_out) >= 7

    shutil.rmtree(feat_spec_dir)
    js_scan = (
        f"import {{ GitBranchSpecScanner, OrphanSpecBranchSync, SpecBranchPuller }} from {json.dumps(branch_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const scanner = new GitBranchSpecScanner(ws);"
        "const list = await scanner.listAllBranchSpecs();"
        "const doc = await scanner.readDocumentFromRef("
        "'.agents/bundles/specs/branch-feature/spec.md', 'feat/side-spec');"
        "const puller = new SpecBranchPuller(ws);"
        "const pulled = await puller.pullSpec('branch-feature', { fromRef: 'feat/side-spec' });"
        "const orphan = new OrphanSpecBranchSync(ws);"
        "const shared = await orphan.sync({ push: false });"
        "process.stdout.write(JSON.stringify({ list, doc, pulled, shared }) + '\\n');"
    )
    scan_proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js_scan],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    scan_out = json.loads(scan_proc.stdout.strip().splitlines()[-1])
    assert any(s["flow_id"] == "branch-feature" and s["on_current_branch"] is False for s in scan_out["list"])
    assert scan_out["doc"]["title"] == "Feature Side"
    assert len(scan_out["doc"].get("siblings", [])) >= 1
    assert (ws / ".agents" / "bundles" / "specs" / "branch-feature" / "spec.md").is_file()
    assert len(scan_out["pulled"]["written_files"]) >= 2
    assert scan_out["shared"]["branch"] == "flow-specs"
    assert len(scan_out["shared"]["synced_specs"]) >= 1

    router_uri = (REPO_ROOT / "sidecars" / "studio" / "router.mjs").as_uri()
    js_dag = (
        f"import {{ StudioApiService }} from {json.dumps(router_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const svc = new StudioApiService({ env: { ...process.env, ANTIGRAVITY_LS_ADDRESS: '' } });"
        "const dag = await svc.handleApi('/api/spec-dag', {"
        " workspacePath: ws, flowId: 'branch-feature', gitRef: 'feat/side-spec' });"
        "svc.close();"
        "process.stdout.write(JSON.stringify(dag) + '\\n');"
    )
    dag_proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js_dag],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    dag_out = json.loads(dag_proc.stdout.strip().splitlines()[-1])
    assert dag_out["ok"] is True
    assert dag_out["flow_id"] == "branch-feature"
    assert "dag" not in dag_out
    assert isinstance(dag_out.get("tasks"), list) and len(dag_out["tasks"]) == 1
    assert dag_out["steps"] == []


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize(
    ("case_id", "force_json"),
    (
        ("sqlite-wal-or-json", "0"),
        ("forced-json-fallback", "1"),
    ),
)
def test_studio_cache_store_sqlite_and_json_fallback(tmp_path: Path, case_id: str, force_json: str) -> None:
    """Verify StudioCacheStore computes, serves cache hits, and invalidates cleanly in both modes."""
    assert NODE_BIN is not None
    sample_file = tmp_path / "doc.md"
    sample_file.write_text("# V1\n", encoding="utf-8")
    cache_uri = (REPO_ROOT / "sidecars" / "studio" / "core" / "cache-store.mjs").as_uri()
    cache_dir_json = json.dumps(str(tmp_path / "cache"))
    sample_json = json.dumps(str(sample_file))
    force_json_js = json.dumps(force_json)
    js = (
        f"import {{ StudioCacheStore }} from {json.dumps(cache_uri)};"
        f"const store = new StudioCacheStore({{ dataDir: {cache_dir_json},"
        f" env: {{ FLOW_FORCE_JSON_CACHE: {force_json_js} }} }});"
        "store.setKv('ns', 'k1', { hello: 'world' });"
        "const kv = store.getKv('ns', 'k1');"
        "let computeCount = 0;"
        "const computeFn = () => { computeCount += 1; return { rev: computeCount }; };"
        f"const f1 = store.getOrComputeFile({sample_json}, 'doc', computeFn);"
        f"const f2 = store.getOrComputeFile({sample_json}, 'doc', computeFn);"
        "const diag = store.diagnostics();"
        "store.close();"
        "process.stdout.write(JSON.stringify({ kv, f1, f2, computeCount, diag }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["kv"] == {"hello": "world"}, f"[{case_id}]"
    assert out["f1"]["rev"] == 1
    assert out["f2"]["rev"] == 1
    assert out["computeCount"] == 1
    if force_json == "1":
        assert out["diag"]["backend"] == "json"


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_antigravity_bridge_model_filtering_and_catalog_opt_in_default(tmp_path: Path) -> None:
    """Verify AntigravityBridge model picker filtering and CatalogBridge pure-Node BM25 default."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    bridge_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "antigravity.mjs").as_uri()
    catalog_uri = (REPO_ROOT / "sidecars" / "studio" / "knowledge" / "catalog.mjs").as_uri()
    js = (
        f"import {{ AntigravityBridge }} from {json.dumps(bridge_uri)};"
        f"import {{ CatalogBridge }} from {json.dumps(catalog_uri)};"
        "const b = new AntigravityBridge({ ANTIGRAVITY_LS_ADDRESS: 'http://127.0.0.1:49999' });"
        "b.call = async (method) => {"
        "  if (method === 'GetCascadeModelConfigData') return {"
        "    ok: true, value: { clientModelConfigs: [{ modelId: 'm-pro', label: 'Pro Model',"
        "      modelOrAlias: { alias: 'pro-alias' }, quotaInfo: { remainingFraction: 0.75 } }] }"
        "  };"
        "  if (method === 'GetAvailableModels') return {"
        "    ok: true, value: { models: {"
        "      'tab_complete': { model: 'tab_complete', displayName: 'Tab Complete' },"
        "      'extra-hidden': { model: 'extra-hidden', displayName: 'Hidden Non-Picker' },"
        "      'custom-local': { model: 'custom-local', displayName: 'Custom Model', isCustom: true }"
        "    } }"
        "  };"
        "  return { ok: true, value: {} };"
        "};"
        "const mq = await b.getModelsAndQuota();"
        "b.call = async (method) => {"
        "  if (method === 'GetAvailableModels') return {"
        "    ok: true, value: { deprecatedModelIds: ['old-model'], models: {"
        "      'old-model': { model: 'old-model', displayName: 'Old' },"
        "      'off-model': { model: 'off-model', disabled: true },"
        "      'tab_inline': { model: 'tab_inline', displayName: 'Tab Inline' },"
        "      'main-image': { model: 'main-image', displayName: 'Image Gen' },"
        "      'model-chat': { model: 'model-chat', displayName: 'Chat Model' }"
        "    } }"
        "  };"
        "  return { ok: true, value: {} };"
        "};"
        "const mqRaw = await b.getModelsAndQuota();"
        f"const cat = new CatalogBridge({{ workspaceRoot: {json.dumps(str(ws))}, env: {{}} }});"
        f"await cat.index([{json.dumps(str(ws))}]);"
        "const catStatus = await cat.status();"
        "cat.close();"
        "process.stdout.write(JSON.stringify({ mq, mqRaw, catStatus }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    picker_ids = sorted(m["model"] for m in out["mq"]["models"])
    assert picker_ids == ["custom-local", "pro-alias"]
    assert [m["model"] for m in out["mqRaw"]["models"]] == ["model-chat"]
    assert out["catStatus"]["strategy"] == "node-bm25"
    assert out["catStatus"]["fts_enabled"] is False
    assert out["catStatus"]["vss_enabled"] is False


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_spec_engine_working_tree_ref_read_document_and_router_fallbacks(tmp_path: Path) -> None:
    """Verify SpecEngine.isWorkingTreeRef, readDocument normalization/siblings, and router fallbacks."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    _init_git_repo(ws)
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=ws, check=True, capture_output=True)

    uncommitted_dir = ws / ".agents" / "bundles" / "specs" / "local-draft"
    uncommitted_dir.mkdir(parents=True)
    (uncommitted_dir / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: local-draft\ntitle: Local Draft\nstate: draft\n---\n\n# Local Draft\n\nLive edit.\n",
        encoding="utf-8",
    )

    branch_name = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=ws,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()

    engine_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "spec-engine.mjs").as_uri()
    router_uri = (REPO_ROOT / "sidecars" / "studio" / "router.mjs").as_uri()
    js = (
        f"import {{ SpecEngine }} from {json.dumps(engine_uri)};"
        f"import {{ StudioApiService }} from {json.dumps(router_uri)};"
        f"const ws = {json.dumps(str(ws))};"
        "const eng = new SpecEngine({ workspacePath: ws });"
        f"const refs = {{"
        "  nil: eng.isWorkingTreeRef(null),"
        "  head: eng.isWorkingTreeRef('HEAD'),"
        f"  cur: eng.isWorkingTreeRef({json.dumps(branch_name)}),"
        f"  full: eng.isWorkingTreeRef({json.dumps(f'refs/heads/{branch_name}')}),"
        "  other: eng.isWorkingTreeRef('feat/missing-branch')"
        "};"
        "const dirDoc = eng.readDocument('.agents/bundles/specs/idempotent-webhooks');"
        "const movedDoc = eng.readDocument('specs/idempotent-webhooks/spec.md');"
        "const svc = new StudioApiService({ env: { ...process.env, ANTIGRAVITY_LS_ADDRESS: '' } });"
        "const draftViaHead = await svc.handleApi('/api/spec-document', {"
        "  workspacePath: ws, relPath: '.agents/bundles/specs/local-draft/spec.md', gitRef: 'HEAD'"
        "});"
        "const fallbackReview = await svc.handleApi('/api/spec-review', {"
        "  workspacePath: ws, flowId: 'idempotent-webhooks', gitRef: 'refs/heads/nonexistent-branch'"
        "});"
        "svc.close();"
        "process.stdout.write(JSON.stringify({ refs, dirDoc, movedDoc, draftViaHead, fallbackReview }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["refs"] == {"nil": True, "head": True, "cur": True, "full": True, "other": False}
    assert out["dirDoc"]["relPath"] == ".agents/bundles/specs/idempotent-webhooks/spec.md"
    assert len(out["dirDoc"]["siblings"]) >= 2
    assert out["movedDoc"]["relPath"] == ".agents/bundles/specs/idempotent-webhooks/spec.md"
    assert out["draftViaHead"]["title"] == "Local Draft"
    assert out["fallbackReview"]["ok"] is True
    assert out["fallbackReview"]["source"] == "local"
    assert out["fallbackReview"]["syncWarning"]


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_bundle_graph_no_export_marker_and_ambiguous_links(tmp_path: Path) -> None:
    """Verify BundleGraph ignores .kc-no-export subtrees and reports ambiguous bare-stem wikilinks."""
    assert NODE_BIN is not None
    bundle = tmp_path / ".agents" / "bundles"
    (bundle / "knowledge" / "a").mkdir(parents=True)
    (bundle / "knowledge" / "b").mkdir(parents=True)
    (bundle / "knowledge" / "private").mkdir(parents=True)
    (bundle / "knowledge" / "private" / ".kc-no-export").write_text("", encoding="utf-8")
    (bundle / "knowledge" / "private" / "secret.md").write_text("# Private\n", encoding="utf-8")
    (bundle / "knowledge" / "a" / "shared.md").write_text("---\ntitle: Shared A\n---\n# Shared A\n", encoding="utf-8")
    (bundle / "knowledge" / "b" / "shared.md").write_text("---\ntitle: Shared B\n---\n# Shared B\n", encoding="utf-8")
    (bundle / "index.md").write_text("Link to [[shared]] and [[knowledge/a/shared]].\n", encoding="utf-8")

    graph_uri = (REPO_ROOT / "sidecars" / "studio" / "knowledge" / "bundle-graph.mjs").as_uri()
    js = (
        f"import {{ BundleGraph, BundleGraphLinter }} from {json.dumps(graph_uri)};"
        f"const g = BundleGraph.load({json.dumps(str(bundle))}, {{ workspaceRoot: {json.dumps(str(tmp_path))} }});"
        "const lint = BundleGraphLinter.lint(g);"
        "process.stdout.write(JSON.stringify({ paths: g.notes.map((n) => n.path).sort(), lint }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert "knowledge/private/secret.md" not in out["paths"]
    assert len(out["lint"]["ambiguous_links"]) == 1
    assert out["lint"]["ambiguous_links"][0]["target"] == "shared"
    assert len(out["lint"]["ambiguous_links"][0]["candidates"]) == 2

    (bundle / ".kc-no-export").write_text("", encoding="utf-8")
    proc_root = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(proc_root.stdout.strip().splitlines()[-1])["paths"] == []


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_rebuild_specs_index_preserves_curated_links_and_feedback_prompt_links(tmp_path: Path) -> None:
    """Verify fence-aware specs/index.md preservation and externalSource Markdown links in buildRevisePrompt."""
    assert NODE_BIN is not None
    specs_dir = tmp_path / ".agents" / "bundles" / "specs"
    (specs_dir / "alpha").mkdir(parents=True)
    (specs_dir / "alpha" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: alpha\ntitle: Alpha Spec\nstate: active\n---\n\n# Alpha\n",
        encoding="utf-8",
    )
    curated = (
        "# Team Specs\n\nCustom curated intro.\n\n"
        "- [Alpha](alpha/spec.md)\n\n"
        "```markdown\n- [Example Stale](fake-ignored/spec.md)\n```\n"
    )
    index_path = specs_dir / "index.md"
    index_path.write_text(curated, encoding="utf-8")

    branch_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "git-spec-branch.mjs").as_uri()
    fb_uri = (REPO_ROOT / "sidecars" / "studio" / "spec" / "feedback.mjs").as_uri()
    js = (
        f"import {{ AgentsBranchSync }} from {json.dumps(branch_uri)};"
        f"import {{ SpecFeedbackStore }} from {json.dumps(fb_uri)};"
        f"const dir = {json.dumps(str(specs_dir))};"
        "const changedCurated = AgentsBranchSync.rebuildSpecsIndex(dir, { dryRun: false });"
        f"const store = new SpecFeedbackStore({json.dumps(str(tmp_path))});"
        "const prompt = store.buildRevisePrompt('alpha', 'alpha', [{"
        "  id: 'c1', flowId: 'alpha', relPath: '.agents/bundles/specs/alpha/spec.md',"
        "  startLine: 3, endLine: 3, commentKind: 'feedback', state: 'open',"
        "  authorName: 'Reviewer', body: 'Check architecture slide.',"
        "  externalSource: { label: 'Doc', title: 'RFC 42', url: 'https://example.com/rfc-42' }"
        "}]);"
        "process.stdout.write(JSON.stringify({ changedCurated, prompt }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["changedCurated"] is False
    assert index_path.read_text(encoding="utf-8") == curated
    assert "[Doc: RFC 42](https://example.com/rfc-42)" in out["prompt"]

    (specs_dir / "beta").mkdir(parents=True)
    (specs_dir / "beta" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: beta\ntitle: Beta Spec\nstate: planned\n---\n\n# Beta\n",
        encoding="utf-8",
    )
    js_rebuild = (
        f"import {{ AgentsBranchSync }} from {json.dumps(branch_uri)};"
        f"const changed = AgentsBranchSync.rebuildSpecsIndex({json.dumps(str(specs_dir))}, {{ dryRun: false }});"
        "process.stdout.write(JSON.stringify({ changed }) + '\\n');"
    )
    proc_rebuild = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js_rebuild],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(proc_rebuild.stdout.strip().splitlines()[-1])["changed"] is True
    rebuilt_text = index_path.read_text(encoding="utf-8")
    assert "alpha/spec.md" in rebuilt_text
    assert "beta/spec.md" in rebuilt_text


def test_studio_web_app_renders_external_source_pills_and_compact_reader_chrome() -> None:
    """Verify Flow Studio web app safely renders externalSource pill links and reader toolbar controls."""
    app_src = (REPO_ROOT / "sidecars" / "studio" / "web" / "app.js").read_text(encoding="utf-8")
    assert "function renderExternalSourcePill(src)" in app_src
    assert app_src.count("renderExternalSourcePill(c.externalSource)") == 2
    assert "doc-topbar" in app_src
    assert "doc-siblings-strip" in app_src
    assert "md-outline-bar" in app_src
    assert "dag-view-header-compact" in app_src
    assert 'c.externalSource ? el("span"' not in app_src
