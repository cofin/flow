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
def test_antigravity_sidecar_main_mounts_pages_and_apis_via_stub_sdk(tmp_path: Path) -> None:
    """Verify main.mjs registers `/` and `/dashboard` pages and API routes with `sidecar_sdk`."""
    assert NODE_BIN is not None
    ws = _seed_studio_workspace(tmp_path)
    stub_sdk = tmp_path / "stub_sidecar_sdk.mjs"
    loader_js = tmp_path / "register_loader.mjs"

    stub_sdk.write_text(
        "export class Response {\n"
        "  constructor(body, init = {}) {\n"
        "    this.body = body;\n"
        "    this.status = init.status || 200;\n"
        "    this.contentType = init.contentType || 'text/plain';\n"
        "    this.headers = init.headers || {};\n"
        "  }\n"
        "}\n"
        "export class SidecarApp {\n"
        "  constructor() { this.pages = new Map(); this.apis = new Map(); }\n"
        "  page(p, fn) { this.pages.set(p, fn); }\n"
        "  api(p, fn, method = 'POST') { this.apis.set(`${method}:${p}`, fn); }\n"
        "  async run() {\n"
        "    const home = await this.pages.get('/')();\n"
        "    const dash = await this.pages.get('/dashboard')();\n"
        "    const snap = await this.apis.get('POST:/api/bundle-snapshot')({ workspacePath: process.env.TEST_WS });\n"
        "    process.stdout.write(JSON.stringify({\n"
        "      hasHome: home.status === 200 && home.body.includes('/preload.js'),\n"
        "      hasDash: dash.status === 200,\n"
        "      snapStatus: snap.status,\n"
        "      snapRepo: JSON.parse(snap.body).repoName,\n"
        "      registeredApis: Array.from(this.apis.keys()).sort()\n"
        "    }) + '\\n');\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    loader_js.write_text(
        "import { register } from 'node:module';\n"
        f"const stubUrl = {json.dumps(stub_sdk.as_uri())};\n"
        "const hookSrc = `export async function resolve(specifier, context, nextResolve) {\n"
        "  if (specifier === 'sidecar_sdk') return { shortCircuit: true, url: ${JSON.stringify(stubUrl)} };\n"
        "  return nextResolve(specifier, context);\n"
        "}`;\n"
        "register('data:text/javascript,' + encodeURIComponent(hookSrc));\n",
        encoding="utf-8",
    )

    run_res = subprocess.run(
        [NODE_BIN, "--import", loader_js.as_uri(), str(REPO_ROOT / "sidecars" / "studio" / "main.mjs")],
        env={
            **os.environ,
            "TEST_WS": str(ws),
            "FLOW_CATALOG_DB": str(tmp_path / "stub.duckdb"),
            "FLOW_WORKSPACES_CONFIG": str(tmp_path / "ws.json"),
        },
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(run_res.stdout.strip().splitlines()[-1])
    assert out["hasHome"] is True
    assert out["hasDash"] is True
    assert out["snapStatus"] == 200
    assert out["snapRepo"] == "payments-service"
    assert "POST:/api/start-workspace-conversation" in out["registeredApis"]
    assert "POST:/api/harness-dispatch" in out["registeredApis"]


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
def test_host_bridge_awaits_async_workspace_uris_and_dispatches_to_selected_workspace(tmp_path: Path) -> None:
    """Verify host-bridge.js awaits async getWorkspaceUris() and routes planning to the selected workspace."""
    assert NODE_BIN is not None
    ws_active = tmp_path / "active-repo"
    ws_other = tmp_path / "other-repo"
    ws_active.mkdir()
    ws_other.mkdir()

    probe_js = """
import fs from "node:fs";
import vm from "node:vm";
import { pathToFileURL } from "node:url";

const bridgePath = process.argv[1];
const wsActive = process.argv[2];
const wsOther = process.argv[3];
const activeUri = pathToFileURL(wsActive).href;
const otherUri = pathToFileURL(wsOther).href;

let workspaceChangeCallback = null;
const sentToActiveChat = [];
const apiCalls = [];
const toggledConversations = [];

const sandboxWindow = {
  location: { pathname: "/", search: "" },
  navigator: { clipboard: { writeText: async () => {} } },
  sidecar: {
    conversationId: "conv-active-1",
    getWorkspaceUris: async () => {
      await new Promise((r) => setTimeout(r, 25));
      return [activeUri];
    },
    onWorkspaceChange: (cb) => {
      workspaceChangeCallback = cb;
      return () => {};
    },
    fetch: async (routePath, init) => {
      const body = JSON.parse(init.body || "{}");
      apiCalls.push({ routePath, body });
      if (routePath === "/api/start-workspace-conversation") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            conversation_id: "conv-other-2",
            workspace_bound: true,
            workspace: body.workspacePath,
            prompt_sent: true,
          }),
        };
      }
      return { ok: true, status: 200, json: async () => ({ ok: true }) };
    },
    agent: {
      sendMessage: async (msg, convId) => {
        sentToActiveChat.push({ msg, convId });
      },
    },
    ui: {
      toggleConversation: (convId) => {
        toggledConversations.push(convId);
      },
      toggleAuxPane: () => {},
    },
  },
};
sandboxWindow.window = sandboxWindow;
sandboxWindow.fetch = sandboxWindow.sidecar.fetch;
sandboxWindow.URL = URL;
sandboxWindow.URLSearchParams = URLSearchParams;
sandboxWindow.setTimeout = setTimeout;
sandboxWindow.clearTimeout = clearTimeout;

const code = fs.readFileSync(bridgePath, "utf8");
vm.runInNewContext(code, sandboxWindow);

const host = sandboxWindow.flowHost;
const events = [];
host.onEvent((evt) => events.push(evt));

const initialUri = await host.getInitialWorkspaceUri();
const dispatchActive = await host.dispatchPrompt({
  workspacePath: wsActive,
  message: "/flow:spec active-feature",
  title: "Spec Active",
});
const dispatchOther = await host.dispatchPrompt({
  workspacePath: wsOther,
  message: "/flow:spec other-feature",
  title: "Spec Other",
});

workspaceChangeCallback([otherUri, "file:///C:/Users/dev/win-repo"]);
const dispatchWin = await host.dispatchPrompt({
  workspacePath: "c:\\\\Users\\\\dev\\\\win-repo",
  message: "/flow:spec win-feature",
  title: "Spec Win",
});

process.stdout.write(JSON.stringify({
  initialUri,
  activeUrisAfterChange: host.getActiveWorkspaceUris(),
  events,
  dispatchActive,
  dispatchOther,
  dispatchWin,
  sentToActiveChat,
  apiCalls,
  toggledConversations,
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
            str(ws_other),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["initialUri"] == ws_active.as_uri()
    assert out["dispatchActive"]["mode"] == "active-conversation"
    assert out["dispatchWin"]["mode"] == "active-conversation"
    assert len(out["sentToActiveChat"]) == 2
    assert out["sentToActiveChat"][0] == {"msg": "/flow:spec active-feature", "convId": "conv-active-1"}
    assert out["sentToActiveChat"][1] == {"msg": "/flow:spec win-feature", "convId": "conv-active-1"}
    assert out["dispatchOther"]["mode"] == "workspace-cascade"
    assert out["dispatchOther"]["conversationId"] == "conv-other-2"
    assert out["toggledConversations"] == ["conv-other-2"]
    assert out["activeUrisAfterChange"] == [ws_other.as_uri(), "file:///C:/Users/dev/win-repo"]
    assert out["events"][0]["type"] == "workspace.changed"
    assert out["events"][0]["uris"] == [ws_other.as_uri(), "file:///C:/Users/dev/win-repo"]


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
    (ws / "assets" / "sample.txt").write_text("asset payload\n", encoding="utf-8")
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
    assert (ws / ".agents" / "bundles" / "specs" / "branch-feature" / "spec.md").is_file()
    assert len(scan_out["pulled"]["written_files"]) >= 2
    assert scan_out["shared"]["branch"] == "flow-specs"
    assert len(scan_out["shared"]["synced_specs"]) >= 1


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
