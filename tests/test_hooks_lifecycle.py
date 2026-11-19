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
STOP_CHECK_SH = REPO_ROOT / "hooks" / "stop-check.sh"
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
    assert set(agy_hooks) == {
        "flow-session-start",
        "flow-pre-invocation",
        "flow-pre-tool-guard",
        "flow-post-tool-telemetry",
        "flow-post-invocation",
        "flow-stop-check",
    }
    assert "matcher" not in agy_hooks["flow-session-start"]["SessionStart"][0]
    assert "matcher" not in agy_hooks["flow-stop-check"]["Stop"][0]
    pre_tool_group = agy_hooks["flow-pre-tool-guard"]["PreToolUse"][0]
    assert "matcher" in pre_tool_group
    assert pre_tool_group["matcher"] != "*"
    assert "run_command" in pre_tool_group["matcher"]
    assert "write_file" in pre_tool_group["matcher"]

    claude_hooks = json.loads((REPO_ROOT / "hooks" / "hooks-claude.json").read_text(encoding="utf-8"))
    claude_post_tool = claude_hooks["hooks"].get("PostToolUse", [])
    assert claude_post_tool and all(entry.get("matcher") != "*" for entry in claude_post_tool)

    for wf_name in ("flow-scout", "flow-spec-planning", "flow-dual-review", "flow-chapter-pipeline"):
        wf_dir = REPO_ROOT / "workflows" / wf_name
        wf_json = json.loads((wf_dir / "workflow.json").read_text(encoding="utf-8"))
        assert wf_json["name"] == wf_name
        assert isinstance(wf_json["description"], str) and wf_json["description"]
        entry = wf_json.get("entry", "workflow.py")
        assert (wf_dir / entry).is_file()
        props = wf_json["args"]["properties"]
        assert any(key.endswith("_agent") for key in props)


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


def _write_flow_spec(workspace: Path, flow_id: str, *, state: str, last_reviewed_commit: str = "") -> Path:
    """Seed a spec file with explicit lifecycle state inside ``workspace``."""
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    setup_path = agents_dir / "setup-state.json"
    if not setup_path.exists():
        setup_path.write_text(
            json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}),
            encoding="utf-8",
        )
    spec_dir = agents_dir / "bundles" / "specs" / flow_id
    spec_dir.mkdir(parents=True, exist_ok=True)
    lrc_line = f"last_reviewed_commit: {last_reviewed_commit}\n" if last_reviewed_commit else ""
    spec_path = spec_dir / "spec.md"
    spec_path.write_text(
        "---\n"
        "type: Spec\n"
        f"flow_id: {flow_id}\n"
        f"title: {flow_id}\n"
        f"state: {state}\n"
        f"{lrc_line}"
        "---\n\n"
        "## 1. Objective\n\nScoped spec.\n",
        encoding="utf-8",
    )
    return spec_path


def _init_git_worktree_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a main Git checkout, a shared linked worktree, and a stealth linked worktree."""
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Flow Test",
        "GIT_AUTHOR_EMAIL": "flow@example.com",
        "GIT_COMMITTER_NAME": "Flow Test",
        "GIT_COMMITTER_EMAIL": "flow@example.com",
    }
    main_repo = tmp_path / "main-repo"
    wt_feature = tmp_path / "wt-feature"
    wt_stealth = tmp_path / "wt-stealth"
    main_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=main_repo, env=git_env, check=True)
    (main_repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: init"], cwd=main_repo, env=git_env, check=True)
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feat/worktree", str(wt_feature)],
        cwd=main_repo,
        env=git_env,
        check=True,
    )
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feat/stealth", str(wt_stealth)],
        cwd=main_repo,
        env=git_env,
        check=True,
    )
    return main_repo, wt_feature, wt_stealth


def _assert_guard_verdict(
    sh_payload: dict[str, Any],
    *,
    case_id: str,
    expected_decision: str,
    expected_spec_fragment: str = "",
    ps_payload: dict[str, Any] | None = None,
) -> None:
    """Assert expected Antigravity verdict and optional denied spec ID across shell and PowerShell hooks."""
    for label, payload in [("sh", sh_payload), *([("ps1", ps_payload)] if ps_payload is not None else [])]:
        assert payload.get("decision") == expected_decision, f"[{case_id}:{label}] unexpected {payload}"
        if expected_spec_fragment:
            assert expected_spec_fragment in payload.get("reason", ""), f"[{case_id}:{label}] {payload}"


@pytest.mark.parametrize(
    ("case_id", "mode", "expected_decision", "expected_spec"),
    (
        ("delete-file-target-path-wt-complete", "delete-targetpath-wt-a", "allow", ""),
        ("delete-file-path-wt-complete", "delete-path-wt-a", "allow", ""),
        ("explicit-prefix-rm-wt-complete", "rm-prefix-wt-a", "allow", ""),
        ("cd-prefix-rm-wt-complete", "cd-rm-wt-a", "allow", ""),
        ("set-location-remove-item-wt-complete", "set-location-wt-a", "allow", ""),
        ("git-dash-c-rm-wt-complete", "git-c-wt-a", "allow", ""),
        ("payload-cwd-overrides-workspace-paths", "payload-cwd-wt-a", "allow", ""),
        ("shared-wt-missing-spec-no-main-leak", "shared-wt-missing-x", "allow", ""),
        ("wt-incomplete-delete-file-target-path", "delete-targetpath-wt-open", "deny", "specs/flow-open"),
        ("wt-incomplete-explicit-prefix-rm", "rm-prefix-wt-open", "deny", "specs/flow-open"),
        ("wt-incomplete-cd-rm", "cd-rm-wt-open", "deny", "specs/flow-open"),
        ("wt-incomplete-git-c-rm", "git-c-wt-open", "deny", "specs/flow-open"),
        ("stealth-wt-without-agents-falls-back-to-main", "rm-stealth-wt-a", "deny", "specs/flow-a"),
    ),
)
def test_pre_tool_guard_resolves_target_worktree_and_command_dirs(
    tmp_path: Path,
    case_id: str,
    mode: str,
    expected_decision: str,
    expected_spec: str,
) -> None:
    """Verify pre-tool-guard resolves deleted spec roots from target paths, cd, git -C, and cwd."""
    main_repo, wt_feature, wt_stealth = _init_git_worktree_pair(tmp_path)
    _write_flow_spec(main_repo, "flow-a", state="planned")
    _write_flow_spec(main_repo, "flow-x", state="planned")
    _write_flow_spec(main_repo, "flow-open", state="completed", last_reviewed_commit="abc1234")
    _write_flow_spec(wt_feature, "flow-a", state="completed", last_reviewed_commit="abc1234")
    _write_flow_spec(wt_feature, "flow-open", state="planned")

    payload_by_mode: dict[str, dict[str, Any]] = {
        "delete-targetpath-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "delete_file",
                "args": {"TargetPath": str(wt_feature / ".agents" / "bundles" / "specs" / "flow-a" / "spec.md")},
            },
        },
        "delete-path-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "delete_file",
                "args": {"Path": str(wt_feature / ".agents" / "bundles" / "specs" / "flow-a" / "spec.md")},
            },
        },
        "rm-prefix-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"rm -rf {wt_feature}/.agents/bundles/specs/flow-a"},
            },
        },
        "cd-rm-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"cd {wt_feature} && rm -rf .agents/bundles/specs/flow-a"},
            },
        },
        "set-location-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": f"Set-Location {wt_feature}; Remove-Item "
                    "-Recurse -Force .agents/bundles/specs/flow-a"
                },
            },
        },
        "git-c-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"git -C {wt_feature} rm -r .agents/bundles/specs/flow-a"},
            },
        },
        "payload-cwd-wt-a": {
            "workspacePaths": [str(main_repo)],
            "cwd": str(wt_feature),
            "toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf .agents/bundles/specs/flow-a"}},
        },
        "shared-wt-missing-x": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"cd {wt_feature} && rm -rf .agents/bundles/specs/flow-x"},
            },
        },
        "delete-targetpath-wt-open": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "delete_file",
                "args": {"TargetPath": str(wt_feature / ".agents" / "bundles" / "specs" / "flow-open" / "spec.md")},
            },
        },
        "rm-prefix-wt-open": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"rm -rf {wt_feature}/.agents/bundles/specs/flow-open"},
            },
        },
        "cd-rm-wt-open": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"cd {wt_feature} && rm -rf .agents/bundles/specs/flow-open"},
            },
        },
        "git-c-wt-open": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"git -C {wt_feature} rm -r .agents/bundles/specs/flow-open"},
            },
        },
        "rm-stealth-wt-a": {
            "workspacePaths": [str(main_repo)],
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": f"cd {wt_stealth} && rm -rf .agents/bundles/specs/flow-a"},
            },
        },
    }
    stdin_payload = payload_by_mode[mode]
    sh_out = _run_hook(PRE_TOOL_GUARD_SH, "agy", stdin_payload)
    ps_out = _run_ps1(PRE_TOOL_GUARD_PS1, "agy", stdin_payload) if POWERSHELL_BIN is not None else None
    _assert_guard_verdict(
        sh_out,
        case_id=case_id,
        expected_decision=expected_decision,
        expected_spec_fragment=expected_spec,
        ps_payload=ps_out,
    )


@pytest.mark.parametrize(
    ("case_id", "cmd_template", "expected_decision", "expected_spec"),
    (
        (
            "multi-arg-second-incomplete",
            "rm -rf .agents/bundles/specs/flow-done .agents/bundles/specs/flow-open",
            "deny",
            "specs/flow-open",
        ),
        (
            "brace-expansion-second-incomplete",
            "rm -rf .agents/bundles/specs/{flow-done,flow-open}",
            "deny",
            "specs/flow-open",
        ),
        (
            "brace-expansion-spec-md",
            "rm -rf .agents/bundles/specs/{flow-done,flow-open}/spec.md",
            "deny",
            "specs/flow-open",
        ),
        ("brace-expansion-all-complete", "rm -rf .agents/bundles/specs/{flow-done,flow-done-2}", "allow", ""),
        (
            "mixed-roots-second-incomplete",
            "rm -rf __WT_DONE__/.agents/bundles/specs/flow-done-wt __MAIN_REPO__/.agents/bundles/specs/flow-open",
            "deny",
            "specs/flow-open",
        ),
        (
            "chained-cd-second-incomplete",
            "cd __WT_DONE__ && rm -rf .agents/bundles/specs/flow-done-wt"
            " && cd __MAIN_REPO__ && rm -rf .agents/bundles/specs/flow-open",
            "deny",
            "specs/flow-open",
        ),
        ("subshell-parens-completed-wt", "(cd __WT_DONE__ && rm -rf .agents/bundles/specs/flow-done-wt)", "allow", ""),
        (
            "subshell-sh-c-completed-wt",
            "sh -c 'cd __WT_DONE__ && rm -rf .agents/bundles/specs/flow-done-wt'",
            "allow",
            "",
        ),
        (
            "subshell-sh-c-incomplete-second",
            "sh -c 'cd __MAIN_REPO__ && rm -rf .agents/bundles/specs/{flow-done,flow-open}'",
            "deny",
            "specs/flow-open",
        ),
    ),
)
def test_pre_tool_guard_checks_all_spec_targets_and_braces(
    tmp_path: Path,
    case_id: str,
    cmd_template: str,
    expected_decision: str,
    expected_spec: str,
) -> None:
    """Verify pre-tool-guard inspects every spec argument and brace expansion across directories."""
    main_repo = tmp_path / "main-repo"
    wt_done = tmp_path / "wt-done"
    main_repo.mkdir()
    wt_done.mkdir()
    _write_flow_spec(main_repo, "flow-done", state="completed", last_reviewed_commit="abc1234")
    _write_flow_spec(main_repo, "flow-done-2", state="completed", last_reviewed_commit="def5678")
    _write_flow_spec(main_repo, "flow-open", state="planned")
    _write_flow_spec(wt_done, "flow-done-wt", state="completed", last_reviewed_commit="999aaaa")

    cmd_line = cmd_template.replace("__MAIN_REPO__", str(main_repo)).replace("__WT_DONE__", str(wt_done))
    stdin_payload = {
        "workspacePaths": [str(main_repo)],
        "toolCall": {"name": "run_command", "args": {"CommandLine": cmd_line}},
    }
    sh_out = _run_hook(PRE_TOOL_GUARD_SH, "agy", stdin_payload)
    ps_out = _run_ps1(PRE_TOOL_GUARD_PS1, "agy", stdin_payload) if POWERSHELL_BIN is not None else None
    _assert_guard_verdict(
        sh_out,
        case_id=case_id,
        expected_decision=expected_decision,
        expected_spec_fragment=expected_spec,
        ps_payload=ps_out,
    )


@pytest.mark.parametrize(
    ("harness", "use_complete_wt", "expected_decision"),
    (
        ("claude", True, "allow"),
        ("claude", False, "deny"),
        ("cursor", True, "allow"),
        ("cursor", False, "deny"),
    ),
)
def test_pre_tool_guard_worktree_resolution_for_claude_and_cursor(
    tmp_path: Path,
    harness: str,
    use_complete_wt: bool,
    expected_decision: str,
) -> None:
    """Verify Claude and Cursor hook payload schemas respect worktree-resolved spec targets."""
    main_repo, wt_feature, _ = _init_git_worktree_pair(tmp_path)
    _write_flow_spec(main_repo, "flow-open", state="planned")
    _write_flow_spec(wt_feature, "flow-done", state="completed", last_reviewed_commit="abc1234")

    cmd = (
        f"rm -rf {wt_feature}/.agents/bundles/specs/flow-done"
        if use_complete_wt
        else "rm -rf .agents/bundles/specs/flow-open"
    )
    payload: dict[str, Any] = (
        {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(main_repo)}
        if harness == "claude"
        else {"command": cmd, "workspace_roots": [str(main_repo)]}
    )
    sh_out = _run_hook(PRE_TOOL_GUARD_SH, harness, payload)
    ps_out = _run_ps1(PRE_TOOL_GUARD_PS1, harness, payload) if POWERSHELL_BIN is not None else None
    for verdict in [sh_out, *([ps_out] if ps_out is not None else [])]:
        if harness == "claude":
            if expected_decision == "allow":
                assert verdict == {}
            else:
                assert verdict["hookSpecificOutput"]["permissionDecision"] == "deny"
        else:
            assert verdict["permission"] == expected_decision


@pytest.mark.parametrize(
    ("sibling_present", "expect_handoff"),
    (
        ("0", True),
        ("1", False),
    ),
)
def test_pre_invocation_turn0_plan_handoff_transcript_fallback_and_sibling_suppression(
    tmp_path: Path,
    sibling_present: str,
    expect_handoff: bool,
) -> None:
    """Verify PreInvocation resolves /plan from transcriptPath when empty and suppresses with sibling."""
    _seed_flow_workspace(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"step_index": 1, "type": "USER_INPUT", "content": "Please create /plan for auth"}) + "\n",
        encoding="utf-8",
    )
    out = _run_hook(
        PRE_INVOCATION_SH,
        "agy",
        {"invocationNum": 0, "transcriptPath": str(transcript)},
        project_dir=tmp_path,
        extra_env={
            "FLOW_RUNTIME_DIR": str(tmp_path / "rt"),
            "FLOW_SIBLING_PLUGIN_PRESENT": sibling_present,
        },
    )
    if expect_handoff:
        msg = out["injectSteps"][0]["systemMessage"]["systemMessage"]
        assert "Flow Turn-0 handoff:" in msg
        assert "flow-cli.mjs spec import" in msg
    else:
        assert out == {}


@pytest.mark.parametrize(
    ("case_id", "extra_env", "agent_id", "expect_updated_model"),
    (
        (
            "claude-unloaded-mod-rewrites-strong",
            {"CLAUDECODE": "1", "FLOW_MOD_LOADED": "0"},
            "flow:plan-generator",
            "claude-opus-4-6",
        ),
        (
            "claude-mod-loaded-skips-fallback",
            {"CLAUDECODE": "1", "FLOW_MOD_LOADED": "1"},
            "flow:plan-generator",
            None,
        ),
        (
            "codex-session-ignores-claude-agent-fallback",
            {"CLAUDECODE": "1", "CODEX_THREAD_ID": "thread-1", "FLOW_MOD_LOADED": "0"},
            "flow:plan-generator",
            None,
        ),
    ),
)
def test_pre_tool_guard_claude_agent_updated_input_vs_codex_omission(
    tmp_path: Path,
    case_id: str,
    extra_env: dict[str, str],
    agent_id: str,
    expect_updated_model: str | None,
) -> None:
    """Verify PreToolUse emits Agent updatedInput only in native Claude sessions when the Claude Mod is unloaded."""
    _seed_flow_workspace(tmp_path)
    tier_dir = tmp_path / ".claude" / "agents"
    tier_dir.mkdir(parents=True)
    (tier_dir / "flow-model-strong.md").write_text(
        "---\nname: flow-model-strong\nmodel: claude-opus-4-6\n---\n\nStrong model.\n",
        encoding="utf-8",
    )
    payload = {
        "tool_name": "Agent",
        "tool_input": {"subagent_type": agent_id, "prompt": "Plan the implementation"},
        "cwd": str(tmp_path),
    }
    clean_env = {"FLOW_RUNTIME_DIR": str(tmp_path / "rt"), **extra_env}
    if "CODEX_THREAD_ID" not in clean_env:
        clean_env["CODEX_THREAD_ID"] = ""
    clean_env["CODEX_CI"] = ""
    out = _run_hook(PRE_TOOL_GUARD_SH, "claude", payload, extra_env=clean_env)
    if expect_updated_model:
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow", f"[{case_id}] {out}"
        assert out["hookSpecificOutput"]["updatedInput"]["model"] == expect_updated_model
    else:
        assert out == {}, f"[{case_id}] {out}"


def test_post_tool_telemetry_step_idx_fallback_and_proceed_metadata_guard(tmp_path: Path) -> None:
    """Verify PostToolUse resolves missing tool/Path via transcriptPath stepIdx and flags missing artifact metadata."""
    _seed_flow_workspace(tmp_path)
    art_dir = tmp_path / "artifacts"
    art_dir.mkdir()
    plan_file = art_dir / "implementation_plan.md"
    plan_file.write_text("# Plan\n", encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"step_index": 7, "name": "write_to_file", "Path": str(plan_file)}) + "\n",
        encoding="utf-8",
    )
    rt_dir = tmp_path / "rt"
    out = _run_hook(
        POST_TOOL_TELEMETRY_SH,
        "agy",
        {
            "workspacePaths": [str(tmp_path)],
            "conversationId": "conv-telemetry-1",
            "stepIdx": 7,
            "transcriptPath": str(transcript),
            "artifactDirectoryPath": str(art_dir),
        },
        extra_env={"FLOW_RUNTIME_DIR": str(rt_dir)},
    )
    assert out == {}
    state_files = list(rt_dir.glob("*/studio-live-state.json"))
    assert len(state_files) == 1
    state = json.loads(state_files[0].read_text(encoding="utf-8"))
    assert state["lastTool"] == "write_to_file"
    assert state["lastFilePath"] == str(plan_file).replace("\\", "/")
    assert state["proceedGuard"] == "missing_artifact_metadata"


@pytest.mark.parametrize(
    ("case_id", "worker_mode"),
    (
        ("sibling-bb-agent-name-bypasses-stop-gate", "bb-agent"),
        ("system-message-only-transcript-bypasses-stop-gate", "system-transcript"),
        ("coordinator-with-open-task-and-dirty-tree-blocks", "coordinator"),
    ),
)
def test_stop_check_worker_detection_and_system_message_only_transcript(
    tmp_path: Path,
    case_id: str,
    worker_mode: str,
) -> None:
    """Verify Stop gate bypasses ^(flow-|bb-|runtime-) and SYSTEM_MESSAGE-only workers."""
    git_kw: dict[str, Any] = {"cwd": tmp_path, "check": True, "capture_output": True, "text": True, "encoding": "utf-8"}
    subprocess.run(["git", "init"], **git_kw)
    subprocess.run(["git", "config", "user.email", "test@example.com"], **git_kw)
    subprocess.run(["git", "config", "user.name", "Test"], **git_kw)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], **git_kw)
    _seed_flow_workspace(tmp_path)
    task_dir = tmp_path / ".agents" / "bundles" / "specs" / "catalog-ui" / "chapters" / "ch01-core" / "tasks"
    task_dir.mkdir(parents=True)
    (tmp_path / ".agents" / "bundles" / "specs" / "catalog-ui" / "chapters" / "ch01-core" / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: catalog-ui\nchapter_id: ch01-core\nstate: active\n---\n\n## Plan\n\n- [ ] t01\n",
        encoding="utf-8",
    )
    (task_dir / "t01-open.md").write_text(
        "---\ntype: Task\nid: catalog-ui:ch01:t01\nstate: pending\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], **git_kw)
    subprocess.run(["git", "commit", "-m", "seed"], **git_kw)
    (tmp_path / "dirty.txt").write_text("uncommitted work\n", encoding="utf-8")

    payload: dict[str, Any] = {"conversationId": "conv-stop-1", "workspacePaths": [str(tmp_path)]}
    if worker_mode == "bb-agent":
        payload["agentName"] = "bb-executor-1"
    elif worker_mode == "system-transcript":
        transcript = tmp_path / "worker-transcript.jsonl"
        transcript.write_text(
            json.dumps({"step_index": 0, "type": "SYSTEM_MESSAGE", "content": "Assigned task"}) + "\n",
            encoding="utf-8",
        )
        payload["transcriptPath"] = str(transcript)

    out = _run_hook(
        STOP_CHECK_SH,
        "agy",
        payload,
        extra_env={"FLOW_RUNTIME_DIR": str(tmp_path / "rt"), "FLOW_STOP_CHECK": "enforce"},
    )
    if worker_mode == "coordinator":
        assert out.get("decision") == "deny" or out.get("blocked") is True or "reason" in out, f"[{case_id}] {out}"
    else:
        assert out == {}, f"[{case_id}] expected worker bypass, got {out}"


def test_hooks_activity_overlay_and_dirty_sha_relaxation(tmp_path: Path) -> None:
    """Verify activity tracking across telemetry, invocation, and stop-check hooks."""
    git_kw: dict[str, Any] = {"cwd": tmp_path, "check": True, "capture_output": True, "text": True, "encoding": "utf-8"}
    subprocess.run(["git", "init"], **git_kw)
    subprocess.run(["git", "config", "user.email", "t@example.com"], **git_kw)
    subprocess.run(["git", "config", "user.name", "Test"], **git_kw)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], **git_kw)

    spec_dir = tmp_path / ".agents" / "bundles" / "specs" / "live-flow"
    (spec_dir / "tasks").mkdir(parents=True)
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles"}),
        encoding="utf-8",
    )
    (spec_dir / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: live-flow\ntitle: Live Flow\nstate: completed\nhas_chapters: false\n"
        "last_reviewed_commit: null\n---\n\n- [x] t01 — App (tasks/t01-app.md)\n",
        encoding="utf-8",
    )
    (spec_dir / "tasks" / "t01-app.md").write_text(
        "---\ntype: Task\nid: live-flow:t01\ntitle: App\nstate: completed\ncommit: null\n"
        "files: [src/mod.py]\ntests: []\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], **git_kw)
    subprocess.run(["git", "commit", "-m", "seed"], **git_kw)

    (tmp_path / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")
    rt_dir = tmp_path / "rt"
    cfg_dir = tmp_path / "cfg"
    extra_env = {"FLOW_RUNTIME_DIR": str(rt_dir), "FLOW_CONFIG_DIR": str(cfg_dir), "FLOW_STOP_CHECK": "enforce"}

    stop_out = _run_hook(
        STOP_CHECK_SH,
        "agy",
        {"conversationId": "conv-dirty", "workspacePaths": [str(tmp_path)]},
        extra_env=extra_env,
    )
    assert stop_out == {}

    (spec_dir / "spec.md").write_text(
        "---\ntype: Spec\nflow_id: live-flow\ntitle: Live Flow\nstate: active\nhas_chapters: false\n"
        "---\n\n- [ ] t01 — App (tasks/t01-app.md)\n",
        encoding="utf-8",
    )
    (spec_dir / "tasks" / "t01-app.md").write_text(
        "---\ntype: Task\nid: live-flow:t01\ntitle: App\nstate: pending\nfiles: [src/mod.py]\ntests: []\n---\n",
        encoding="utf-8",
    )
    _run_hook(
        POST_TOOL_TELEMETRY_SH,
        "agy",
        {
            "workspacePaths": [str(tmp_path)],
            "conversationId": "conv-live-1",
            "toolCall": {"name": "edit_file"},
            "Path": str(tmp_path / "src" / "mod.py"),
        },
        extra_env=extra_env,
    )
    act_files = list(rt_dir.glob("*/activity/conv-live-1.json"))
    assert len(act_files) == 1
    act_data = json.loads(act_files[0].read_text(encoding="utf-8"))
    assert "live-flow" in act_data["flows"]

    _run_hook(
        POST_INVOCATION_SH,
        "agy",
        {"workspacePaths": [str(tmp_path)], "conversationId": "conv-live-1"},
        extra_env=extra_env,
    )
    act_after = json.loads(act_files[0].read_text(encoding="utf-8"))
    assert act_after["active"] is False
