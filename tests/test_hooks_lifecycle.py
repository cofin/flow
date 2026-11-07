"""Tests for 6-stage lifecycle hooks, safety guards, live telemetry, and dynamic workflows."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT

PRE_INVOCATION_SH = REPO_ROOT / "hooks" / "pre-invocation.sh"
PRE_INVOCATION_PS1 = REPO_ROOT / "hooks" / "pre-invocation.ps1"
PRE_TOOL_GUARD_SH = REPO_ROOT / "hooks" / "pre-tool-guard.sh"
PRE_TOOL_GUARD_PS1 = REPO_ROOT / "hooks" / "pre-tool-guard.ps1"
POST_TOOL_TELEMETRY_SH = REPO_ROOT / "hooks" / "post-tool-telemetry.sh"
POST_TOOL_TELEMETRY_PS1 = REPO_ROOT / "hooks" / "post-tool-telemetry.ps1"
POST_INVOCATION_SH = REPO_ROOT / "hooks" / "post-invocation.sh"
POST_INVOCATION_PS1 = REPO_ROOT / "hooks" / "post-invocation.ps1"
POWERSHELL_BIN = shutil.which("pwsh") or shutil.which("powershell")


def _seed_flow_workspace(tmp_path: Path) -> Path:
    """Create a minimal Flow workspace with an active spec in ``tmp_path``."""
    spec_dir = tmp_path / ".agents" / "bundles" / "specs" / "catalog-ui"
    spec_dir.mkdir(parents=True)
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}),
        encoding="utf-8",
    )
    spec_path = spec_dir / "spec.md"
    spec_path.write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: catalog-ui\n"
        "title: Catalog UI\n"
        "state: active\n"
        "current_chapter: ch01-core\n"
        "current_task: catalog-ui:ch01:t01\n"
        "---\n\n"
        "## 1. Objective\n\nInitial objective.\n",
        encoding="utf-8",
    )
    return spec_path


def _run_hook(
    sh_script: Path,
    harness: str,
    stdin_payload: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute a POSIX sh hook script and return its parsed JSON stdout."""
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_VERSION"}
    cmd = ["sh", str(sh_script), "--harness", harness]
    if project_dir is not None:
        cmd.extend(["--project", str(project_dir)])
    proc = subprocess.run(
        cmd,
        input=json.dumps(stdin_payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
    )
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


def _run_ps1(
    ps1_script: Path,
    harness: str,
    stdin_payload: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute a PowerShell hook script and return its parsed JSON stdout."""
    assert POWERSHELL_BIN is not None
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_VERSION"}
    cmd = [
        POWERSHELL_BIN,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1_script),
        "--harness",
        harness,
    ]
    if project_dir is not None:
        cmd.extend(["--project", str(project_dir)])
    proc = subprocess.run(
        cmd,
        input=json.dumps(stdin_payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
    )
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


@pytest.mark.parametrize(
    ("case_id", "harness", "stdin_payload", "expected_decision", "expected_substring"),
    (
        (
            "agy-deny-git-tag-create",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "git tag v0.27.0"}}},
            "deny",
            "Git tags",
        ),
        (
            "agy-deny-git-tag-annotated",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "git tag -a v1.0.0 -m rel"}}},
            "deny",
            "Git tags",
        ),
        (
            "agy-deny-git-push-tags",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "git push origin --tags"}}},
            "deny",
            "Git tags",
        ),
        (
            "agy-allow-git-tag-list",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "git tag --list"}}},
            "allow",
            "",
        ),
        (
            "agy-force-ask-force-push",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "git push --force origin feat/x"}}},
            "force_ask",
            "force-push",
        ),
        (
            "agy-deny-readonly-reviewer-edit",
            "agy",
            {
                "agentName": "code-reviewer",
                "toolCall": {"name": "edit_file", "args": {"Path": "tools/validate.py"}},
            },
            "deny",
            "read-only",
        ),
        (
            "agy-allow-safe-pytest",
            "agy",
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "uv run pytest -q"}}},
            "allow",
            "",
        ),
        (
            "claude-deny-git-tag",
            "claude",
            {"tool_name": "Bash", "tool_input": {"command": "git tag v2.0.0"}},
            "deny",
            "Git tags",
        ),
        (
            "claude-ask-reset-hard",
            "claude",
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~1"}},
            "ask",
            "destructive",
        ),
        (
            "claude-deny-readonly-agent-write",
            "claude",
            {"agent_type": "quality-reviewer", "tool_name": "Write", "tool_input": {"file_path": "a.py"}},
            "deny",
            "read-only",
        ),
        (
            "claude-allow-normal-bash",
            "claude",
            {"tool_name": "Bash", "tool_input": {"command": "git status"}},
            "allow",
            "",
        ),
    ),
)
def test_pre_tool_guard_enforces_git_and_readonly_agent_rules(
    tmp_path: Path,
    case_id: str,
    harness: str,
    stdin_payload: dict[str, Any],
    expected_decision: str,
    expected_substring: str,
) -> None:
    """Verify pre-tool-guard blocks Git tag mutations and read-only agent writes while allowing safe calls."""
    payload = _run_hook(PRE_TOOL_GUARD_SH, harness, stdin_payload, project_dir=tmp_path)
    if harness == "agy":
        assert payload.get("decision") == expected_decision, f"[{case_id}] unexpected payload: {payload}"
        if expected_substring:
            assert expected_substring.lower() in payload.get("reason", "").lower()
    else:
        if expected_decision == "allow":
            assert payload == {}
        else:
            hook_out = payload["hookSpecificOutput"]
            assert hook_out["permissionDecision"] == expected_decision
            assert expected_substring.lower() in hook_out["permissionDecisionReason"].lower()

    if POWERSHELL_BIN is not None:
        ps_payload = _run_ps1(PRE_TOOL_GUARD_PS1, harness, stdin_payload, project_dir=tmp_path)
        if harness == "agy":
            assert ps_payload.get("decision") == expected_decision


def test_pre_invocation_detects_external_spec_and_comment_changes(tmp_path: Path) -> None:
    """Verify pre-invocation stays silent initially and emits a notice when spec.md or comments change."""
    spec_path = _seed_flow_workspace(tmp_path)
    first = _run_hook(PRE_INVOCATION_SH, "agy", {"workspacePaths": [str(tmp_path)]})
    assert first == {}

    second = _run_hook(PRE_INVOCATION_SH, "agy", {"workspacePaths": [str(tmp_path)]})
    assert second == {}

    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("Initial objective.", "Updated objective from Studio UI."),
        encoding="utf-8",
    )
    third = _run_hook(PRE_INVOCATION_SH, "agy", {"workspacePaths": [str(tmp_path)]})
    msg = third["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "Flow Studio notice" in msg
    assert "spec.md" in msg

    fourth = _run_hook(PRE_INVOCATION_SH, "agy", {"workspacePaths": [str(tmp_path)]})
    assert fourth == {}


def test_post_tool_telemetry_and_post_invocation_manage_live_state_cleanly(tmp_path: Path) -> None:
    """Verify post-tool-telemetry and post-invocation update studio-live-state.json only in .agents repos."""
    non_flow_dir = tmp_path / "plain-repo"
    non_flow_dir.mkdir()
    assert (
        _run_hook(
            POST_TOOL_TELEMETRY_SH,
            "agy",
            {"workspacePaths": [str(non_flow_dir)], "toolCall": {"name": "edit_file", "args": {"Path": "x.py"}}},
        )
        == {}
    )
    assert not (non_flow_dir / ".agents").exists()

    flow_repo = tmp_path / "flow-repo"
    _seed_flow_workspace(flow_repo)
    telemetry_out = _run_hook(
        POST_TOOL_TELEMETRY_SH,
        "agy",
        {
            "conversationId": "conv-abc-123",
            "workspacePaths": [str(flow_repo)],
            "toolCall": {"name": "edit_file", "args": {"Path": "tools/catalog/service.py"}},
        },
    )
    assert telemetry_out == {}
    live_state_path = flow_repo / ".agents" / "studio-live-state.json"
    assert live_state_path.is_file()
    live_state = json.loads(live_state_path.read_text(encoding="utf-8"))
    assert live_state["activeTurn"] is True
    assert live_state["harness"] == "agy"
    assert live_state["lastTool"] == "edit_file"
    assert "tools/catalog/service.py" in live_state["lastFilePath"]

    post_inv_out = _run_hook(
        POST_INVOCATION_SH,
        "agy",
        {"conversationId": "conv-abc-123", "workspacePaths": [str(flow_repo)]},
    )
    assert post_inv_out == {}
    cleared_state = json.loads(live_state_path.read_text(encoding="utf-8"))
    assert cleared_state["activeTurn"] is False


def test_six_stage_hooks_and_workflows_manifests_are_valid() -> None:
    """Verify hooks.json declares flat lifecycle hooks, nested tool hooks, and valid workflow manifests."""
    agy_hooks = json.loads((REPO_ROOT / "hooks.json").read_text(encoding="utf-8"))
    assert "matcher" not in agy_hooks["flow-session-start"]["SessionStart"][0]
    assert "matcher" not in agy_hooks["flow-pre-invocation"]["PreInvocation"][0]
    assert "matcher" not in agy_hooks["flow-post-invocation"]["PostInvocation"][0]
    assert "matcher" not in agy_hooks["flow-stop-check"]["Stop"][0]
    assert "matcher" in agy_hooks["flow-pre-tool-guard"]["PreToolUse"][0]
    assert "matcher" in agy_hooks["flow-post-tool-telemetry"]["PostToolUse"][0]

    for wf_name in ("flow-dual-review", "flow-chapter-pipeline"):
        wf_dir = REPO_ROOT / "workflows" / wf_name
        wf_json = json.loads((wf_dir / "workflow.json").read_text(encoding="utf-8"))
        assert wf_json["name"] == wf_name
        assert isinstance(wf_json["description"], str) and wf_json["description"]
        entry = wf_json.get("entry", "workflow.py")
        assert (wf_dir / entry).is_file()
