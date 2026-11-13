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
            str(REPO_ROOT / "sidecars" / "studio" / "host-bridge.js"),
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
