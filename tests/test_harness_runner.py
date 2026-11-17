"""Public-seam tests for toggleable cross-harness execution modes and the local A2A v1 endpoint."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT, is_link_or_junction

NODE_BIN = shutil.which("node")


def _seed_git_repo_with_mock_harnesses(base_dir: Path) -> tuple[Path, Path]:
    """Create an initialized Git workspace and mock CLI binaries for claude, codex, and opencode."""
    ws = base_dir / "repo"
    bin_dir = base_dir / "mock-bin"
    ws.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=ws, check=True)
    (ws / "README.md").write_text("# Demo Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: init"], cwd=ws, check=True)

    for cli_name in ("claude", "codex", "opencode"):
        if sys.platform == "win32":
            script_path = bin_dir / f"{cli_name}.cmd"
            script_path.write_text(
                f'@echo off\r\necho {{"type":"assistant","harness":"{cli_name}"}}\r\n',
                encoding="utf-8",
            )
        else:
            script_path = bin_dir / cli_name
            script_path.write_text(
                "#!/usr/bin/env sh\n"
                f'printf \'{{"type":"assistant","harness":"{cli_name}","cwd":"%s","args":"%s"}}\\n\' "$(pwd)" "$*"\n',
                encoding="utf-8",
            )
            script_path.chmod(0o755)
    return ws, bin_dir


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
@pytest.mark.parametrize("execution_mode", ["direct-workspace", "worktree-isolated", "read-only"])
def test_cross_harness_runner_execution_modes(tmp_path: Path, execution_mode: str) -> None:
    """Verify CrossHarnessRunner supports direct-workspace, worktree-isolated, and read-only modes."""
    assert NODE_BIN is not None
    ws, mock_bin = _seed_git_repo_with_mock_harnesses(tmp_path)
    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "cli.mjs").as_uri()

    js = (
        f"import {{ CrossHarnessRunner }} from {json.dumps(runner_uri)};"
        f"const runner = new CrossHarnessRunner({{ defaultWorkspace: {json.dumps(str(ws))} }});"
        "const detected = runner.detectHarnesses();"
        "const res = await runner.dispatch({"
        f"  workspacePath: {json.dumps(str(ws))},"
        "  harness: 'codex',"
        f"  executionMode: {json.dumps(execution_mode)},"
        "  prompt: '/flow:review demo-spec',"
        "  wait: true"
        "});"
        "process.stdout.write(JSON.stringify({ detected, res }) + '\\n');"
    )
    env = {
        **os.environ,
        "FLOW_HARNESS_BIN_DIR": str(mock_bin),
    }
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
    available = {h["id"]: h["installed"] for h in payload["detected"]}
    assert available["codex"] is True
    assert available["claude"] is True

    run_result = payload["res"]
    assert run_result["status"] == "completed"
    assert run_result["executionMode"] == execution_mode
    if execution_mode == "worktree-isolated":
        assert ".agents/worktrees/" in run_result["effectiveCwd"].replace("\\", "/")
    else:
        assert Path(run_result["effectiveCwd"]).resolve() == ws.resolve()
    if execution_mode == "read-only":
        assert "read-only" in " ".join(run_result["argv"])


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_active_writer_advisory_detection_and_a2a_jsonrpc(tmp_path: Path) -> None:
    """Verify active-writer guard reports concurrent writers and A2A v1 handles message/send and agent card."""
    assert NODE_BIN is not None
    ws, mock_bin = _seed_git_repo_with_mock_harnesses(tmp_path)
    (ws / ".git" / "index.lock").write_text("locked\n", encoding="utf-8")

    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "cli.mjs").as_uri()
    a2a_uri = (REPO_ROOT / "sidecars" / "studio" / "a2a.mjs").as_uri()
    js = (
        f"import {{ CrossHarnessRunner }} from {json.dumps(runner_uri)};"
        f"import {{ A2AFacade }} from {json.dumps(a2a_uri)};"
        f"const runner = new CrossHarnessRunner({{ defaultWorkspace: {json.dumps(str(ws))} }});"
        f"const guard = runner.checkActiveWriter({json.dumps(str(ws))});"
        "const a2a = new A2AFacade(runner);"
        "const card = a2a.buildAgentCard('http://127.0.0.1:4319');"
        "const rpc = await a2a.handleJsonRpc({"
        "  jsonrpc: '2.0',"
        "  id: 'req-1',"
        "  method: 'message/send',"
        "  params: {"
        "    message: { role: 'user', parts: [{ kind: 'text', text: '/flow:status' }] },"
        f"    metadata: {{ harness: 'claude', executionMode: 'read-only', workspacePath: {json.dumps(str(ws))} }}"
        "  }"
        "});"
        "process.stdout.write(JSON.stringify({ guard, card, rpc }) + '\\n');"
    )
    env = {**os.environ, "FLOW_HARNESS_BIN_DIR": str(mock_bin), "FLOW_CONFIG_DIR": str(tmp_path / "cfg")}
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["guard"]["activeWriter"] is True
    assert "index.lock" in out["guard"]["reason"]
    assert out["card"]["name"] == "Flow Studio Cross-Harness Bridge"
    assert out["rpc"]["id"] == "req-1"
    assert out["rpc"]["result"]["status"]["state"] == "completed"


@pytest.mark.skipif(NODE_BIN is None, reason="node binary required")
def test_cross_harness_runner_worktree_symlinking_and_quota_model_fallback(tmp_path: Path) -> None:
    """Verify CrossHarnessRunner symlinks .venv/.agents in isolated worktrees and retries opus -> sonnet on 429."""
    assert NODE_BIN is not None
    ws, mock_bin = _seed_git_repo_with_mock_harnesses(tmp_path)
    (ws / ".venv" / "bin").mkdir(parents=True)
    (ws / ".agents" / "bundles").mkdir(parents=True)
    (ws / ".agents" / "setup-state.json").write_text(
        json.dumps({"workflow_preferences": {"ignore_policy": "local-only"}}),
        encoding="utf-8",
    )

    if sys.platform != "win32":
        claude_bin = mock_bin / "claude"
        claude_bin.write_text(
            "#!/usr/bin/env sh\n"
            'case "$*" in\n'
            '  *"--model opus"*)\n'
            '    printf "429 rate_limit_error: opus quota exceeded\\n" >&2\n'
            "    exit 1\n"
            "    ;;\n"
            "  *)\n"
            '    printf \'{"type":"assistant","harness":"claude","args":"%s"}\\n\' "$*"\n'
            "    exit 0\n"
            "    ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        claude_bin.chmod(0o755)

    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "cli.mjs").as_uri()
    js = (
        f"import {{ CrossHarnessRunner }} from {json.dumps(runner_uri)};"
        f"const runner = new CrossHarnessRunner({{ defaultWorkspace: {json.dumps(str(ws))} }});"
        "const res = await runner.dispatch({"
        f"  workspacePath: {json.dumps(str(ws))},"
        "  harness: 'claude',"
        "  executionMode: 'worktree-isolated',"
        "  model: 'opus',"
        "  prompt: '/flow:review demo-spec',"
        "  wait: true"
        "});"
        "process.stdout.write(JSON.stringify(res) + '\\n');"
    )
    env = {**os.environ, "FLOW_HARNESS_BIN_DIR": str(mock_bin), "FLOW_CONFIG_DIR": str(tmp_path / "cfg")}
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    wt_cwd = Path(out["effectiveCwd"])
    assert is_link_or_junction(wt_cwd / ".venv")
    assert is_link_or_junction(wt_cwd / ".agents")
    assert (wt_cwd / ".venv").resolve() == (ws / ".venv").resolve()
    assert (wt_cwd / ".agents").resolve() == (ws / ".agents").resolve()
    if sys.platform != "win32":
        assert out["status"] == "completed"
        assert out["requestedModel"] == "opus"
        assert out["effectiveModel"] == "sonnet"
        assert out["modelFallbackUsed"] is True


@pytest.mark.skipif(NODE_BIN is None or sys.platform == "win32", reason="node and POSIX sh required")
def test_codex_app_server_bridge_jsonrpc_and_isolated_codex_home(tmp_path: Path) -> None:
    """Verify CodexAppServerBridge speaks JSON-RPC lifecycle methods and isolates CODEX_HOME."""
    assert NODE_BIN is not None
    src_codex_home = tmp_path / "src-codex"
    src_codex_home.mkdir()
    (src_codex_home / "auth.json").write_text('{"token":"demo"}\n', encoding="utf-8")
    (src_codex_home / "models_cache.json").write_text(
        '{"models":[{"slug":"gpt-5.4","supported_reasoning_levels":[{"effort":"xhigh"}]}]}\n',
        encoding="utf-8",
    )

    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    codex_script = mock_bin / "codex"
    codex_script.write_text(
        "#!/usr/bin/env node\n"
        "import readline from 'node:readline';\n"
        "const rl = readline.createInterface({ input: process.stdin });\n"
        "rl.on('line', (line) => {\n"
        "  if (!line.trim()) return;\n"
        "  const msg = JSON.parse(line);\n"
        "  const send = (obj) => process.stdout.write(JSON.stringify(obj) + '\\n');\n"
        "  if (msg.method === 'initialize') {\n"
        "    send({ jsonrpc: '2.0', id: msg.id, result: { ok: true } });\n"
        "  } else if (msg.method === 'model/list') {\n"
        "    send({ jsonrpc: '2.0', id: msg.id, result: {\n"
        "      data: [{ model: 'gpt-5.4', supportedReasoningEfforts: ['high', 'xhigh'] }]\n"
        "    } });\n"
        "  } else if (msg.method === 'thread/start') {\n"
        "    send({ jsonrpc: '2.0', id: msg.id, result: { thread: { id: 'thr-1' } } });\n"
        "  } else if (msg.method === 'thread/fork') {\n"
        "    send({ jsonrpc: '2.0', id: msg.id, result: { thread: { id: 'thr-fork-1' } } });\n"
        "  } else if (msg.method === 'turn/start') {\n"
        "    const tid = msg.params.threadId;\n"
        "    send({ jsonrpc: '2.0', id: msg.id, result: { turn: { id: 'turn-1', status: 'inProgress' } } });\n"
        "    send({ jsonrpc: '2.0', method: 'item/agentMessage/delta',\n"
        "      params: { threadId: tid, delta: 'verified via ' + (process.env.CODEX_HOME || '') } });\n"
        "    send({ jsonrpc: '2.0', method: 'turn/completed',\n"
        "      params: { threadId: tid, turn: { id: 'turn-1', status: 'completed' } } });\n"
        "  }\n"
        "});\n",
        encoding="utf-8",
    )
    codex_script.chmod(0o755)

    codex_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "codex.mjs").as_uri()
    iso_root = tmp_path / "iso-root"
    iso_root.mkdir()
    js = (
        f"import {{ CodexAppServerBridge }} from {json.dumps(codex_uri)};"
        "const bridge = new CodexAppServerBridge({ env: {"
        "  ...process.env,"
        f"  PATH: {json.dumps(str(mock_bin))} + ':' + (process.env.PATH || ''),"
        f"  CODEX_HOME: {json.dumps(str(src_codex_home))}"
        "} });"
        f"await bridge.connect({{ cwd: {json.dumps(str(tmp_path))}, isolatedHomeRoot: {json.dumps(str(iso_root))} }});"
        "const models = await bridge.listModels();"
        "const thr = await bridge.startThread({ sandbox: 'read-only' });"
        "const forked = await bridge.forkThread(thr.id);"
        "const turn = await bridge.runTurn({"
        "  threadId: thr.id, prompt: 'Check contract', model: 'gpt-5.4', effort: 'xhigh'"
        "});"
        "bridge.close();"
        "process.stdout.write(JSON.stringify({ models, thr, forked, turn }) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["models"][0]["model"] == "gpt-5.4"
    assert out["thr"]["id"] == "thr-1"
    assert out["forked"]["thread"]["id"] == "thr-fork-1"
    assert out["turn"]["status"] == "completed"
    assert "verified via" in out["turn"]["output"]
    iso_dirs = list(iso_root.glob(".codex-home-*"))
    assert len(iso_dirs) == 1
    assert is_link_or_junction(iso_dirs[0] / "auth.json")
    assert (iso_dirs[0] / "models_cache.json").is_file()


@pytest.mark.skipif(NODE_BIN is None or sys.platform == "win32", reason="node and POSIX sh required")
def test_cross_harness_runner_upward_delegate_selects_frontier_tier(tmp_path: Path) -> None:
    """Verify CrossHarnessRunner.delegate routes semantic_validation upward with effort flags."""
    assert NODE_BIN is not None
    ws, mock_bin = _seed_git_repo_with_mock_harnesses(tmp_path)
    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "bridges" / "cli.mjs").as_uri()
    js = (
        f"import {{ CrossHarnessRunner }} from {json.dumps(runner_uri)};"
        "const runner = new CrossHarnessRunner({"
        f"  defaultWorkspace: {json.dumps(str(ws))},"
        f"  env: {{ PATH: process.env.PATH || '', FLOW_HARNESS_BIN_DIR: {json.dumps(str(mock_bin))},"
        f"    CLAUDE_CONFIG_DIR: {json.dumps(str(tmp_path / 'cdir'))},"
        f"    FLOW_CONFIG_DIR: {json.dumps(str(tmp_path / 'cfg'))},"
        f"    FLOW_RUNTIME_DIR: {json.dumps(str(tmp_path / 'rt'))} }}"
        "});"
        "const res = await runner.delegate({"
        f"  workspacePath: {json.dumps(str(ws))},"
        "  harness: 'claude', taskKind: 'semantic_validation', prompt: 'Audit schema invariance'"
        "});"
        "process.stdout.write(JSON.stringify(res) + '\\n');"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["status"] == "completed"
    assert "--model" in out["argv"]
    assert "opus" in out["argv"]
    assert "--effort" in out["argv"]
