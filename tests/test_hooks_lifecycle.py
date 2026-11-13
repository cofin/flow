"""Tests for lifecycle hooks, safety guards, live telemetry, and dynamic workflows."""

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
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute a POSIX sh hook script and return its parsed JSON stdout."""
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_VERSION"}
    if extra_env:
        env.update(extra_env)
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
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute a PowerShell hook script and return its parsed JSON stdout."""
    assert POWERSHELL_BIN is not None
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_VERSION"}
    if extra_env:
        env.update(extra_env)
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
    """Verify pre-invocation skips substeps and emits a notice on turn start when spec.md changes."""
    spec_path = _seed_flow_workspace(tmp_path)
    rt_env = {"FLOW_RUNTIME_DIR": str(tmp_path / "rt")}
    payload_turn = {"invocationNum": 0, "workspacePaths": [str(tmp_path)]}
    first = _run_hook(PRE_INVOCATION_SH, "agy", payload_turn, extra_env=rt_env)
    assert first == {}

    second = _run_hook(PRE_INVOCATION_SH, "agy", payload_turn, extra_env=rt_env)
    assert second == {}

    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("Initial objective.", "Updated objective from Studio UI."),
        encoding="utf-8",
    )
    substep = _run_hook(
        PRE_INVOCATION_SH,
        "agy",
        {"invocationNum": 1, "workspacePaths": [str(tmp_path)]},
        extra_env=rt_env,
    )
    assert substep == {}

    third = _run_hook(PRE_INVOCATION_SH, "agy", payload_turn, extra_env=rt_env)
    msg = third["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "Flow Studio notice" in msg
    assert "spec.md" in msg

    fourth = _run_hook(PRE_INVOCATION_SH, "agy", payload_turn, extra_env=rt_env)
    assert fourth == {}


def test_post_tool_telemetry_and_post_invocation_manage_live_state_cleanly(tmp_path: Path) -> None:
    """Verify post-tool-telemetry and post-invocation write v1 studio-live-state.json into FLOW_RUNTIME_DIR."""
    rt_dir = tmp_path / "rt"
    rt_env = {"FLOW_RUNTIME_DIR": str(rt_dir)}
    non_flow_dir = tmp_path / "plain-repo"
    non_flow_dir.mkdir()
    assert (
        _run_hook(
            POST_TOOL_TELEMETRY_SH,
            "agy",
            {"workspacePaths": [str(non_flow_dir)], "toolCall": {"name": "edit_file", "args": {"Path": "x.py"}}},
            extra_env=rt_env,
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
            "toolCall": {
                "name": "edit_file",
                "args": {"Path": ".agents/bundles/specs/catalog-ui/chapters/ch01-core/tasks/t01-init.md"},
            },
        },
        extra_env=rt_env,
    )
    assert telemetry_out == {}
    assert not (flow_repo / ".agents" / "studio-live-state.json").exists()
    runtime_files = list(rt_dir.glob("*/studio-live-state.json"))
    assert len(runtime_files) == 1
    live_state_path = runtime_files[0]
    live_state = json.loads(live_state_path.read_text(encoding="utf-8"))
    assert live_state["v"] == 1
    assert live_state["activeTurn"] is True
    assert live_state["harness"] == "agy"
    assert live_state["conversationId"] == "conv-abc-123"
    assert live_state["role"] == "coordinator"
    assert live_state["flowId"] == "catalog-ui"
    assert live_state["chapterId"] == "ch01-core"
    assert live_state["taskIds"] == ["t01"]
    assert live_state["worktree"] == flow_repo.as_posix()
    assert "edit_file" in live_state["activity"]
    assert live_state["lastTool"] == "edit_file"
    assert "t01-init.md" in live_state["lastFilePath"]

    pre_inv_out = _run_hook(
        PRE_INVOCATION_SH,
        "agy",
        {"invocationNum": 0, "conversationId": "conv-abc-123", "workspacePaths": [str(flow_repo)]},
        extra_env=rt_env,
    )
    assert pre_inv_out == {}
    after_pre = json.loads(live_state_path.read_text(encoding="utf-8"))
    assert after_pre["v"] == 1
    assert after_pre["flowId"] == "catalog-ui"
    assert after_pre["chapterId"] == "ch01-core"
    assert after_pre["taskIds"] == ["t01"]

    post_inv_out = _run_hook(
        POST_INVOCATION_SH,
        "agy",
        {"conversationId": "conv-abc-123", "workspacePaths": [str(flow_repo)]},
        extra_env=rt_env,
    )
    assert post_inv_out == {}
    cleared_state = json.loads(live_state_path.read_text(encoding="utf-8"))
    assert cleared_state["v"] == 1
    assert cleared_state["activeTurn"] is False
    assert cleared_state["flowId"] == "catalog-ui"
    assert cleared_state["chapterId"] == "ch01-core"
    assert cleared_state["taskIds"] == ["t01"]
    assert cleared_state["worktree"] == flow_repo.as_posix()
    assert cleared_state["activity"] == live_state["activity"]


def test_antigravity_hooks_and_workflows_manifests_are_valid() -> None:
    """Verify hooks.json declares flat lifecycle hooks, Claude omits wildcard PostToolUse, and workflows exist."""
    agy_hooks = json.loads((REPO_ROOT / "hooks.json").read_text(encoding="utf-8"))
    assert set(agy_hooks) == {"flow-session-start", "flow-pre-tool-guard", "flow-stop-check"}
    assert "matcher" not in agy_hooks["flow-session-start"]["SessionStart"][0]
    assert "matcher" not in agy_hooks["flow-stop-check"]["Stop"][0]
    pre_tool_group = agy_hooks["flow-pre-tool-guard"]["PreToolUse"][0]
    assert "matcher" in pre_tool_group
    assert pre_tool_group["matcher"] != "*"
    assert "run_command" in pre_tool_group["matcher"]
    assert "write_file" in pre_tool_group["matcher"]

    claude_hooks = json.loads((REPO_ROOT / "hooks" / "hooks-claude.json").read_text(encoding="utf-8"))
    assert "PostToolUse" not in claude_hooks["hooks"]

    for wf_name in ("flow-scout", "flow-spec-planning", "flow-dual-review", "flow-chapter-pipeline"):
        wf_dir = REPO_ROOT / "workflows" / wf_name
        wf_json = json.loads((wf_dir / "workflow.json").read_text(encoding="utf-8"))
        assert wf_json["name"] == wf_name
        assert isinstance(wf_json["description"], str) and wf_json["description"]
        entry = wf_json.get("entry", "workflow.py")
        assert (wf_dir / entry).is_file()


@pytest.mark.parametrize(
    ("case_id", "flow_completed", "stdin_payload", "expected_agy_decision"),
    (
        (
            "deny-rm-incomplete-spec-dir",
            False,
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf .agents/bundles/specs/catalog-ui"}}},
            "deny",
        ),
        (
            "deny-delete-file-incomplete-spec",
            False,
            {"toolCall": {"name": "delete_file", "args": {"Path": ".agents/bundles/specs/catalog-ui/spec.md"}}},
            "deny",
        ),
        (
            "allow-rm-completed-reviewed-spec",
            True,
            {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf .agents/bundles/specs/catalog-ui"}}},
            "allow",
        ),
    ),
)
def test_pre_tool_guard_blocks_premature_spec_deletion_and_allows_completed(
    tmp_path: Path,
    case_id: str,
    flow_completed: bool,
    stdin_payload: dict[str, Any],
    expected_agy_decision: str,
) -> None:
    """Verify pre-tool-guard blocks deleting incomplete specs/<flow_id> directories while allowing archive cleanup."""
    spec_path = _seed_flow_workspace(tmp_path)
    if flow_completed:
        spec_path.write_text(
            "---\n"
            "type: Spec\n"
            "flow_id: catalog-ui\n"
            "title: Catalog UI\n"
            "state: completed\n"
            "last_reviewed_commit: a1b2c3d\n"
            "---\n\n"
            "## 1. Objective\n\nCompleted.\n",
            encoding="utf-8",
        )
    out = _run_hook(PRE_TOOL_GUARD_SH, "agy", stdin_payload, project_dir=tmp_path)
    assert out["decision"] == expected_agy_decision, f"[{case_id}] unexpected {out}"
    if expected_agy_decision == "deny":
        assert "cannot delete or archive specs/catalog-ui" in out["reason"]
