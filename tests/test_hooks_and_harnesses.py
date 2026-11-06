"""Tests for POSIX sh + PowerShell SessionStart and Stop hooks and multi-harness surfaces."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.validate import REPO_ROOT

HOOK_SCRIPT = REPO_ROOT / "hooks" / "session-start.sh"
POWERSHELL_HOOK_SCRIPT = REPO_ROOT / "hooks" / "session-start.ps1"
STOP_HOOK_SCRIPT = REPO_ROOT / "hooks" / "stop-check.sh"
POWERSHELL_STOP_HOOK_SCRIPT = REPO_ROOT / "hooks" / "stop-check.ps1"
POWERSHELL_BIN = shutil.which("pwsh") or shutil.which("powershell")
NODE_BIN = shutil.which("node")


def _seed_sample_bundle(tmp_path: Path) -> None:
    """Create a sample single-chapter .agents/bundles and .agents/skills workspace in ``tmp_path``."""
    bundles_dir = tmp_path / ".agents" / "bundles"
    spec_dir = bundles_dir / "specs" / "auth-refactor"
    spec_dir.mkdir(parents=True)
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}),
        encoding="utf-8",
    )
    (bundles_dir / "index.md").write_text('---\nokf_version: "0.2"\nbundle: demo\n---\n', encoding="utf-8")
    (spec_dir / "spec.md").write_text(
        "---\ntype: Spec\ntitle: Auth Refactor\ndescription: Desc\nflow_id: auth-refactor\n"
        "state: active\ncurrent_task: TASK-1.2\n---\n",
        encoding="utf-8",
    )
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "index.md").write_text("# Project Skills\n", encoding="utf-8")


def _init_git_repo_with_two_commits(tmp_path: Path) -> tuple[str, str]:
    """Initialize a sandboxed Git repository in ``tmp_path`` and return ``(older_sha, newer_sha)``."""
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Flow Test",
        "GIT_AUTHOR_EMAIL": "flow@example.com",
        "GIT_COMMITTER_NAME": "Flow Test",
        "GIT_COMMITTER_EMAIL": "flow@example.com",
    }
    subprocess.run(["git", "init"], cwd=str(tmp_path), env=git_env, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(tmp_path),
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = tmp_path / "app.py"
    tracked.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=str(tmp_path), env=git_env, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: initial slice"],
        cwd=str(tmp_path),
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    )
    sha1 = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=str(tmp_path),
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    tracked.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=str(tmp_path), env=git_env, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: reviewed checkpoint"],
        cwd=str(tmp_path),
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    )
    sha2 = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=str(tmp_path),
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return sha1, sha2


def _seed_multichapter_workspace(tmp_path: Path, *, sha1: str = "1111111", sha2: str = "2222222") -> Path:
    """Seed a clean multi-chapter workspace where ch01 is reviewed/completed and ch02 is mid-flight."""
    bundles_dir = tmp_path / ".agents" / "bundles"
    flow_dir = bundles_dir / "specs" / "auth-refactor"
    ch1_tasks = flow_dir / "chapters" / "ch01-tokens" / "tasks"
    ch2_tasks = flow_dir / "chapters" / "ch02-session" / "tasks"
    ch1_tasks.mkdir(parents=True)
    ch2_tasks.mkdir(parents=True)

    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"setup_status": "complete", "bundle_root": ".agents/bundles", "okf_version": "0.2"}),
        encoding="utf-8",
    )
    (bundles_dir / "index.md").write_text('---\nokf_version: "0.2"\nbundle: demo\n---\n', encoding="utf-8")
    (flow_dir / "chapters" / "index.md").write_text(
        "# Chapters: Auth Refactor\n\n"
        "* [ch01-tokens](ch01-tokens/spec.md) — [completed] Token signing.\n"
        "* [ch02-session](ch02-session/spec.md) — [active] Session middleware.\n",
        encoding="utf-8",
    )
    (flow_dir / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: auth-refactor\n"
        "title: Auth Refactor\n"
        "description: Multi-chapter auth flow.\n"
        "state: active\n"
        "has_chapters: true\n"
        "current_chapter: ch02-session\n"
        "current_task: auth-refactor:ch02:t02\n"
        f"last_reviewed_commit: {sha2}\n"
        "---\n\n"
        "## 5. Implementation Plan\n\n"
        f"- [x] [{sha2}] [ch01-tokens](chapters/ch01-tokens/spec.md) — Token signing\n"
        "- [~] [ch02-session](chapters/ch02-session/spec.md) — Session middleware\n",
        encoding="utf-8",
    )
    (flow_dir / "chapters" / "ch01-tokens" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "chapter_id: ch01-tokens\n"
        "state: completed\n"
        f"last_reviewed_commit: {sha2}\n"
        "---\n\n"
        "## 5. Implementation Plan\n\n"
        f"- [x] [{sha1}] [t01](tasks/t01-signer.md) — Signer slice\n",
        encoding="utf-8",
    )
    (ch1_tasks / "t01-signer.md").write_text(
        f"---\ntype: Task\nid: auth-refactor:ch01:t01\nstate: completed\ncommit: {sha1}\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (flow_dir / "chapters" / "ch02-session" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "chapter_id: ch02-session\n"
        "state: active\n"
        "last_reviewed_commit: null\n"
        "---\n\n"
        "## 5. Implementation Plan\n\n"
        f"- [x] [{sha2}] [t01](tasks/t01-cookie.md) — Cookie slice\n"
        "- [ ] [t02](tasks/t02-middleware.md) — Middleware slice\n",
        encoding="utf-8",
    )
    (ch2_tasks / "t01-cookie.md").write_text(
        f"---\ntype: Task\nid: auth-refactor:ch02:t01\nstate: completed\ncommit: {sha2}\n---\n\nBody.\n",
        encoding="utf-8",
    )
    (ch2_tasks / "t02-middleware.md").write_text(
        "---\ntype: Task\nid: auth-refactor:ch02:t02\nstate: pending\ncommit: null\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return flow_dir


def _mark_ch02_all_tasks_completed_without_closing(flow_dir: Path, sha: str = "2222222") -> None:
    """Complete task t02 in ch02-session and update its checklist while leaving ch02-session unclosed."""
    ch2_spec = flow_dir / "chapters" / "ch02-session" / "spec.md"
    ch2_spec.write_text(
        ch2_spec.read_text(encoding="utf-8").replace(
            "- [ ] [t02](tasks/t02-middleware.md)",
            f"- [x] [{sha}] [t02](tasks/t02-middleware.md)",
        ),
        encoding="utf-8",
    )
    t02 = flow_dir / "chapters" / "ch02-session" / "tasks" / "t02-middleware.md"
    t02.write_text(
        f"---\ntype: Task\nid: auth-refactor:ch02:t02\nstate: completed\ncommit: {sha}\n---\n\nBody.\n",
        encoding="utf-8",
    )


def _run_sh_hook(
    script: Path,
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
    cmd = ["sh", str(script), "--harness", harness]
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
    parsed: dict[str, Any] = json.loads(proc.stdout)
    return parsed


def _run_ps1_hook(
    script: Path,
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
        str(script),
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
    parsed: dict[str, Any] = json.loads(proc.stdout)
    return parsed


def _mutate_stop_task_checklist_drift(flow_dir: Path, _sha1: str, sha2: str) -> None:
    """Mark t02 completed in frontmatter while leaving ch02-session/spec.md checklist at [ ]."""
    t02 = flow_dir / "chapters" / "ch02-session" / "tasks" / "t02-middleware.md"
    t02.write_text(
        f"---\ntype: Task\nid: auth-refactor:ch02:t02\nstate: completed\ncommit: {sha2}\n---\n\nBody.\n",
        encoding="utf-8",
    )


def _mutate_stop_unclosed_chapter(flow_dir: Path, _sha1: str, sha2: str) -> None:
    """Finish all tasks in ch02-session without running chapter review or closing the chapter."""
    _mark_ch02_all_tasks_completed_without_closing(flow_dir, sha=sha2)


def _mutate_stop_stale_git_review_stamp(flow_dir: Path, sha1: str, sha2: str) -> None:
    """Set ch01-tokens task commit to newer sha2 while last_reviewed_commit remains older sha1."""
    (flow_dir / "chapters" / "ch01-tokens" / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "chapter_id: ch01-tokens\n"
        "state: completed\n"
        f"last_reviewed_commit: {sha1}\n"
        "---\n\n"
        "## 5. Implementation Plan\n\n"
        f"- [x] [{sha2}] [t01](tasks/t01-signer.md) — Signer slice\n",
        encoding="utf-8",
    )
    (flow_dir / "chapters" / "ch01-tokens" / "tasks" / "t01-signer.md").write_text(
        f"---\ntype: Task\nid: auth-refactor:ch01:t01\nstate: completed\ncommit: {sha2}\n---\n\nBody.\n",
        encoding="utf-8",
    )


def _mutate_stop_missing_from_index(flow_dir: Path, _sha1: str, _sha2: str) -> None:
    """Drop ch02-session from chapters/index.md."""
    (flow_dir / "chapters" / "index.md").write_text(
        "# Chapters: Auth Refactor\n\n* [ch01-tokens](ch01-tokens/spec.md) — [completed] Token signing.\n",
        encoding="utf-8",
    )


def _mutate_stop_missing_from_root_spec(flow_dir: Path, _sha1: str, sha2: str) -> None:
    """Drop ch02-session from root spec.md."""
    (flow_dir / "spec.md").write_text(
        "---\n"
        "type: Spec\n"
        "flow_id: auth-refactor\n"
        "state: active\n"
        "has_chapters: true\n"
        "current_chapter: ch01-tokens\n"
        f"last_reviewed_commit: {sha2}\n"
        "---\n\n"
        "## 5. Implementation Plan\n\n"
        f"- [x] [{sha2}] [ch01-tokens](chapters/ch01-tokens/spec.md) — Token signing\n",
        encoding="utf-8",
    )


def _mutate_stop_current_chapter_stuck(flow_dir: Path, _sha1: str, _sha2: str) -> None:
    """Point current_chapter at completed ch01-tokens while ch02-session remains open."""
    spec_path = flow_dir / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("current_chapter: ch02-session", "current_chapter: ch01-tokens"),
        encoding="utf-8",
    )


def _mutate_stop_standalone_hr(flow_dir: Path, _sha1: str, _sha2: str) -> None:
    """Append a standalone --- horizontal rule to root spec.md."""
    spec_path = flow_dir / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n---\n\nExtra.\n", encoding="utf-8")


def _mutate_stop_revision_history(flow_dir: Path, _sha1: str, _sha2: str) -> None:
    """Append a forbidden ## Revision History section to root spec.md."""
    spec_path = flow_dir / "spec.md"
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n## Revision History\n\nOld.\n", encoding="utf-8")


STOP_VIOLATION_CASES: tuple[tuple[str, Callable[[Path, str, str], None], str], ...] = (
    ("task-checklist-drift", _mutate_stop_task_checklist_drift, "has state marker [ ] in spec.md but expected [x]"),
    ("unclosed-finished-chapter", _mutate_stop_unclosed_chapter, "all 2 task(s) are done, but chapter is not closed"),
    ("stale-git-review-stamp", _mutate_stop_stale_git_review_stamp, "is newer than last_reviewed_commit"),
    (
        "missing-from-index",
        _mutate_stop_missing_from_index,
        "chapters/index.md: missing entry for chapter ch02-session",
    ),
    (
        "missing-from-root-spec",
        _mutate_stop_missing_from_root_spec,
        "full-plan roadmap is missing chapter ch02-session",
    ),
    (
        "current-chapter-stuck",
        _mutate_stop_current_chapter_stuck,
        "current_chapter 'ch01-tokens' must advance to an open remaining chapter",
    ),
    ("standalone-body-hr", _mutate_stop_standalone_hr, "standalone --- horizontal rule forbidden"),
    ("revision-history-heading", _mutate_stop_revision_history, "historical changelog/revision section forbidden"),
)

STOP_BYPASS_AND_LEAF_CASES: tuple[tuple[str, str, dict[str, Any], dict[str, str] | None], ...] = (
    ("cursor-dedup-on-claude", "claude", {}, {"CURSOR_VERSION": "1.0.0"}),
    ("agy-execution-num-cap", "agy", {"executionNum": 2}, None),
    ("agy-non-model-stop", "agy", {"terminationReason": "max_steps_exceeded"}, None),
    ("agy-error-present", "agy", {"error": "quota_exceeded"}, None),
    ("claude-stop-hook-active", "claude", {"stop_hook_active": True}, None),
    ("cursor-loop-count-cap", "cursor", {"loop_count": 1}, None),
    ("cursor-aborted-status", "cursor", {"status": "aborted"}, None),
    ("agy-leaf-subagent-parent-id", "agy", {"parentConversationId": "conv-parent-123"}, None),
    ("agy-leaf-subagent-prompt-path", "agy", {"lastUserInput": "Follow agents/executor.md for task t02"}, None),
)


@pytest.mark.parametrize(
    ("harness", "stdin_key"),
    (
        ("agy", "workspacePaths"),
        ("claude", "cwd"),
        ("cursor", "workspace_roots"),
    ),
)
def test_session_start_hook_outputs_valid_json_for_all_harnesses(
    tmp_path: Path,
    harness: str,
    stdin_key: str,
) -> None:
    """Verify hooks/session-start.sh emits the expected JSON schema for Antigravity, Claude Code, and Cursor."""
    _seed_sample_bundle(tmp_path)
    stdin_val: Any = [str(tmp_path)] if stdin_key != "cwd" else str(tmp_path)
    payload = _run_sh_hook(HOOK_SCRIPT, harness, {stdin_key: stdin_val})

    if harness == "agy":
        msg = payload["injectSteps"][0]["systemMessage"]["systemMessage"]
        assert "auth-refactor(active, task=TASK-1.2)" in msg
        assert ".agents/skills/index.md" in msg
    elif harness == "claude":
        assert payload["continue"] is True
        assert "auth-refactor(active, task=TASK-1.2)" in payload["hookSpecificOutput"]["additionalContext"]
    else:
        assert payload["continue"] is True
        assert "auth-refactor(active, task=TASK-1.2)" in payload["additional_context"]


def test_session_start_reports_current_chapter_and_pending_sync(tmp_path: Path) -> None:
    """Verify session-start surfaces active chapter IDs and pending chapter review/Markdown sync alerts."""
    flow_dir = _seed_multichapter_workspace(tmp_path)
    _mark_ch02_all_tasks_completed_without_closing(flow_dir)

    payload = _run_sh_hook(HOOK_SCRIPT, "agy", {"workspacePaths": [str(tmp_path)]})
    msg = payload["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "auth-refactor(active, chapter=ch02-session, task=auth-refactor:ch02:t02)" in msg
    assert "Pending chapter review/Markdown sync: auth-refactor/ch02-session." in msg

    if POWERSHELL_BIN is not None:
        ps_payload = _run_ps1_hook(POWERSHELL_HOOK_SCRIPT, "agy", {"workspacePaths": [str(tmp_path)]})
        ps_msg = ps_payload["injectSteps"][0]["systemMessage"]["systemMessage"]
        assert "auth-refactor(active, chapter=ch02-session, task=auth-refactor:ch02:t02)" in ps_msg
        assert "Pending chapter review/Markdown sync: auth-refactor/ch02-session." in ps_msg


def test_session_start_claude_deduplicates_under_cursor(tmp_path: Path) -> None:
    """Verify --harness claude suppresses duplicate output when CURSOR_VERSION is set."""
    payload = _run_sh_hook(
        HOOK_SCRIPT,
        "claude",
        {},
        project_dir=tmp_path,
        extra_env={"CURSOR_VERSION": "1.0.0"},
    )
    assert payload == {"continue": True}


def test_powershell_hook_surface_and_windows_manifest_wiring() -> None:
    """Verify PowerShell SessionStart + Stop scripts exist and all harness manifests wire Stop hooks."""
    assert POWERSHELL_HOOK_SCRIPT.is_file()
    assert POWERSHELL_STOP_HOOK_SCRIPT.is_file()
    ps1_text = POWERSHELL_HOOK_SCRIPT.read_text(encoding="utf-8")
    assert '$ErrorActionPreference = "Stop"' in ps1_text
    assert "--harness" in ps1_text
    assert "--project" in ps1_text
    assert "injectSteps" in ps1_text
    assert "hookSpecificOutput" in ps1_text
    assert "additional_context" in ps1_text

    stop_ps1_text = POWERSHELL_STOP_HOOK_SCRIPT.read_text(encoding="utf-8")
    assert '$ErrorActionPreference = "Stop"' in stop_ps1_text
    assert "last_reviewed_commit" in stop_ps1_text
    assert "followup_message" in stop_ps1_text

    agy_hooks = json.loads((REPO_ROOT / "hooks.json").read_text(encoding="utf-8"))
    assert "stop-check.sh" in agy_hooks["flow-stop-check"]["Stop"][0]["command"]

    claude_hooks = json.loads((REPO_ROOT / "hooks" / "hooks-claude.json").read_text(encoding="utf-8"))
    start_handler = claude_hooks["hooks"]["SessionStart"][0]["hooks"][0]
    assert "session-start.sh" in start_handler["command"]
    assert "session-start.ps1" in start_handler["commandWindows"]
    assert "-ExecutionPolicy Bypass" in start_handler["commandWindows"]

    stop_handler = claude_hooks["hooks"]["Stop"][0]["hooks"][0]
    assert "stop-check.sh" in stop_handler["command"]
    assert "stop-check.ps1" in stop_handler["commandWindows"]
    assert "-ExecutionPolicy Bypass" in stop_handler["commandWindows"]

    cursor_hooks = json.loads((REPO_ROOT / "hooks" / "hooks-cursor.json").read_text(encoding="utf-8"))
    assert cursor_hooks["hooks"]["stop"][0]["loop_limit"] == 2
    assert "stop-check.sh" in cursor_hooks["hooks"]["stop"][0]["command"]

    codex_plugin = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert codex_plugin["hooks"] == "./hooks/hooks-claude.json"


@pytest.mark.skipif(POWERSHELL_BIN is None, reason="pwsh or powershell is not installed on this host")
@pytest.mark.parametrize(
    ("harness", "stdin_key"),
    (
        ("agy", "workspacePaths"),
        ("claude", "cwd"),
        ("cursor", "workspace_roots"),
    ),
)
def test_powershell_session_start_hook_outputs_valid_json_for_all_harnesses(
    tmp_path: Path,
    harness: str,
    stdin_key: str,
) -> None:
    """Verify hooks/session-start.ps1 emits the expected JSON schema across all harnesses and deduplicates Cursor."""
    _seed_sample_bundle(tmp_path)
    stdin_val: Any = [str(tmp_path)] if stdin_key != "cwd" else str(tmp_path)
    payload = _run_ps1_hook(POWERSHELL_HOOK_SCRIPT, harness, {stdin_key: stdin_val})

    if harness == "agy":
        msg = payload["injectSteps"][0]["systemMessage"]["systemMessage"]
        assert "auth-refactor(active, task=TASK-1.2)" in msg
        assert ".agents/skills/index.md" in msg
    elif harness == "claude":
        assert payload["continue"] is True
        assert "auth-refactor(active, task=TASK-1.2)" in payload["hookSpecificOutput"]["additionalContext"]
        dedup = _run_ps1_hook(
            POWERSHELL_HOOK_SCRIPT,
            "claude",
            {},
            project_dir=tmp_path,
            extra_env={"CURSOR_VERSION": "1.0.0"},
        )
        assert dedup == {"continue": True}
    else:
        assert payload["continue"] is True
        assert "auth-refactor(active, task=TASK-1.2)" in payload["additional_context"]


@pytest.mark.parametrize("harness", ("agy", "claude", "cursor"))
def test_stop_check_allows_clean_mid_chapter_and_reviewed_git_ancestry(tmp_path: Path, harness: str) -> None:
    """Verify stop-check allows clean mid-chapter progress and valid Git ancestry on reviewed chapters."""
    sha1, sha2 = _init_git_repo_with_two_commits(tmp_path)
    _seed_multichapter_workspace(tmp_path, sha1=sha1, sha2=sha2)

    assert _run_sh_hook(STOP_HOOK_SCRIPT, harness, {}, project_dir=tmp_path) == {}
    if POWERSHELL_BIN is not None:
        assert _run_ps1_hook(POWERSHELL_STOP_HOOK_SCRIPT, harness, {}, project_dir=tmp_path) == {}


@pytest.mark.parametrize(
    ("harness", "expected_key", "expected_val"),
    (
        ("agy", "decision", "continue"),
        ("claude", "decision", "block"),
        ("cursor", "followup_message", None),
        ("json", "blocked", True),
    ),
)
def test_stop_check_emits_harness_specific_block_schema(
    tmp_path: Path,
    harness: str,
    expected_key: str,
    expected_val: str | bool | None,
) -> None:
    """Verify stop-check emits Antigravity 'continue', Claude 'block', and Cursor 'followup_message' payloads."""
    flow_dir = _seed_multichapter_workspace(tmp_path)
    _mark_ch02_all_tasks_completed_without_closing(flow_dir)

    payload = _run_sh_hook(STOP_HOOK_SCRIPT, harness, {}, project_dir=tmp_path)
    assert expected_key in payload
    if expected_val is not None:
        assert payload[expected_key] == expected_val
        assert "Flow Stop Gate blocked turn completion" in payload["reason"]
    else:
        assert "Flow Stop Gate blocked turn completion" in payload[expected_key]

    if POWERSHELL_BIN is not None:
        ps_payload = _run_ps1_hook(POWERSHELL_STOP_HOOK_SCRIPT, harness, {}, project_dir=tmp_path)
        assert expected_key in ps_payload
        if expected_val is not None:
            assert ps_payload[expected_key] == expected_val


@pytest.mark.parametrize(
    ("case_id", "mutator", "expected_substring"),
    STOP_VIOLATION_CASES,
    ids=[case[0] for case in STOP_VIOLATION_CASES],
)
def test_stop_check_blocks_unsynced_markdown_and_stale_review_stamps(
    tmp_path: Path,
    case_id: str,
    mutator: Callable[[Path, str, str], None],
    expected_substring: str,
) -> None:
    """Verify stop-check catches checklist drift, unclosed chapters, stale Git review SHAs, and history bloat."""
    sha1, sha2 = _init_git_repo_with_two_commits(tmp_path)
    flow_dir = _seed_multichapter_workspace(tmp_path, sha1=sha1, sha2=sha2)
    mutator(flow_dir, sha1, sha2)

    payload = _run_sh_hook(STOP_HOOK_SCRIPT, "agy", {}, project_dir=tmp_path)
    assert payload.get("decision") == "continue", f"[{case_id}] expected block payload, got {payload}"
    assert expected_substring in payload.get("reason", ""), f"[{case_id}] missing {expected_substring!r} in {payload}"

    if POWERSHELL_BIN is not None:
        ps_payload = _run_ps1_hook(POWERSHELL_STOP_HOOK_SCRIPT, "agy", {}, project_dir=tmp_path)
        assert ps_payload.get("decision") == "continue"
        assert expected_substring in ps_payload.get("reason", "")


@pytest.mark.parametrize(
    ("case_id", "harness", "stdin_payload", "extra_env"),
    STOP_BYPASS_AND_LEAF_CASES,
    ids=[case[0] for case in STOP_BYPASS_AND_LEAF_CASES],
)
def test_stop_check_respects_circuit_breakers_and_leaf_subagent_guards(
    tmp_path: Path,
    case_id: str,
    harness: str,
    stdin_payload: dict[str, Any],
    extra_env: dict[str, str] | None,
) -> None:
    """Verify stop-check prevents infinite loops and allows clean leaf subagent turns to return to coordinator."""
    flow_dir = _seed_multichapter_workspace(tmp_path)
    _mark_ch02_all_tasks_completed_without_closing(flow_dir)

    payload = _run_sh_hook(STOP_HOOK_SCRIPT, harness, stdin_payload, project_dir=tmp_path, extra_env=extra_env)
    assert payload == {}, f"[{case_id}] expected allow {{}}, got {payload}"

    if POWERSHELL_BIN is not None:
        ps_payload = _run_ps1_hook(
            POWERSHELL_STOP_HOOK_SCRIPT,
            harness,
            stdin_payload,
            project_dir=tmp_path,
            extra_env=extra_env,
        )
        assert ps_payload == {}, f"[{case_id}] expected PowerShell allow {{}}, got {ps_payload}"


def test_opencode_v2_plugin_is_self_contained() -> None:
    """Verify .opencode/plugins/flow.js uses native node:fs/node:path and exports V2 setup(ctx)."""
    plugin_js = (REPO_ROOT / ".opencode" / "plugins" / "flow.js").read_text(encoding="utf-8")
    assert 'id: "flow"' in plugin_js
    assert "async setup(ctx)" in plugin_js
    assert "node:fs" in plugin_js
    assert "node:path" in plugin_js
    assert "python3" not in plugin_js
    assert "managedConfig" not in plugin_js


@pytest.mark.skipif(NODE_BIN is None, reason="node is not installed on this host")
def test_opencode_v2_plugin_recomputes_bundle_summary_dynamically_per_turn(tmp_path: Path) -> None:
    """Verify OpenCode V2 context hook re-reads spec/chapter state on each turn without re-running setup(ctx)."""
    assert NODE_BIN is not None
    flow_dir = _seed_multichapter_workspace(tmp_path)
    plugin_path = REPO_ROOT / ".opencode" / "plugins" / "flow.js"
    probe_js = (
        'import fs from "node:fs";\n'
        'import path from "node:path";\n'
        'import { pathToFileURL } from "node:url";\n'
        "const mod = await import(pathToFileURL(process.argv[1]).href);\n"
        "const ws = process.argv[2];\n"
        "let contextFn = null;\n"
        "await mod.flowPlugin.setup({\n"
        "  workspace: { root: ws },\n"
        "  session: { hook: (_ev, fn) => { contextFn = fn; } },\n"
        "});\n"
        "const turn1 = (await contextFn()).systemMessage;\n"
        'const ch2Dir = path.join(ws, ".agents/bundles/specs/auth-refactor/chapters/ch02-session");\n'
        'const ch2Spec = path.join(ch2Dir, "spec.md");\n'
        'const ch2Task = path.join(ch2Dir, "tasks/t02-middleware.md");\n'
        'const doneFm = ["---", "type: Task", "id: auth-refactor:ch02:t02", '
        '"state: completed", "commit: 2222222", "---", ""].join("\\n");\n'
        'fs.writeFileSync(ch2Task, doneFm, "utf8");\n'
        'const nextSpec = fs.readFileSync(ch2Spec, "utf8").replace("- [ ] [t02]", "- [x] [2222222] [t02]");\n'
        'fs.writeFileSync(ch2Spec, nextSpec, "utf8");\n'
        "const turn2 = (await contextFn()).systemMessage;\n"
        "process.stdout.write(JSON.stringify({ turn1, turn2 }) + '\\n');\n"
    )
    proc = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", probe_js, str(plugin_path), str(tmp_path)],
        text=True,
        capture_output=True,
        cwd=str(flow_dir),
        check=True,
    )
    out = json.loads(proc.stdout)
    assert "auth-refactor(active, chapter=ch02-session, task=auth-refactor:ch02:t02)" in out["turn1"]
    assert "Pending chapter review/Markdown sync" not in out["turn1"]
    assert "Pending chapter review/Markdown sync: auth-refactor/ch02-session." in out["turn2"]
