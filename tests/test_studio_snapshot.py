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
