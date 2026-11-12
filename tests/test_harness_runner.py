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

from tools.validate import REPO_ROOT

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
    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "harness-runner.mjs").as_uri()

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

    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "harness-runner.mjs").as_uri()
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
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env={**os.environ, "FLOW_HARNESS_BIN_DIR": str(mock_bin)},
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

    runner_uri = (REPO_ROOT / "sidecars" / "studio" / "harness-runner.mjs").as_uri()
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
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", js],
        env={**os.environ, "FLOW_HARNESS_BIN_DIR": str(mock_bin)},
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    wt_cwd = Path(out["effectiveCwd"])
    assert (wt_cwd / ".venv").is_symlink()
    assert (wt_cwd / ".agents").is_symlink()
    if sys.platform != "win32":
        assert out["status"] == "completed"
        assert out["requestedModel"] == "opus"
        assert out["effectiveModel"] == "sonnet"
        assert out["modelFallbackUsed"] is True
