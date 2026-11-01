"""Tests for pure POSIX sh SessionStart hook execution and multi-harness surfaces."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tools.validate import REPO_ROOT

HOOK_SCRIPT = REPO_ROOT / "hooks" / "session-start.sh"


def test_session_start_hook_outputs_valid_json_for_all_harnesses(tmp_path: Path) -> None:
    """Verify hooks/session-start.sh emits the expected JSON schema for Antigravity, Claude Code, and Cursor."""
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

    agy_stdin = json.dumps({"workspacePaths": [str(tmp_path)]})
    agy_proc = subprocess.run(
        ["sh", str(HOOK_SCRIPT), "--harness", "agy"],
        input=agy_stdin,
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    agy_payload = json.loads(agy_proc.stdout)
    agy_msg = agy_payload["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "auth-refactor(active, task=TASK-1.2)" in agy_msg
    assert ".agents/skills/index.md" in agy_msg

    claude_stdin = json.dumps({"cwd": str(tmp_path)})
    env_no_cursor = {k: v for k, v in os.environ.items() if k != "CURSOR_VERSION"}
    claude_proc = subprocess.run(
        ["sh", str(HOOK_SCRIPT), "--harness", "claude"],
        input=claude_stdin,
        text=True,
        capture_output=True,
        env=env_no_cursor,
        check=True,
    )
    claude_payload = json.loads(claude_proc.stdout)
    assert claude_payload["continue"] is True
    assert "auth-refactor(active, task=TASK-1.2)" in claude_payload["hookSpecificOutput"]["additionalContext"]

    cursor_stdin = json.dumps({"workspace_roots": [str(tmp_path)]})
    cursor_proc = subprocess.run(
        ["sh", str(HOOK_SCRIPT), "--harness", "cursor"],
        input=cursor_stdin,
        text=True,
        capture_output=True,
        check=True,
    )
    cursor_payload = json.loads(cursor_proc.stdout)
    assert cursor_payload["continue"] is True
    assert "auth-refactor(active, task=TASK-1.2)" in cursor_payload["additional_context"]


def test_session_start_claude_deduplicates_under_cursor(tmp_path: Path) -> None:
    """Verify --harness claude suppresses duplicate output when CURSOR_VERSION is set."""
    env_with_cursor = {**os.environ, "CURSOR_VERSION": "1.0.0"}
    proc = subprocess.run(
        ["sh", str(HOOK_SCRIPT), "--harness", "claude", "--project", str(tmp_path)],
        input="{}",
        text=True,
        capture_output=True,
        env=env_with_cursor,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload == {"continue": True}


def test_opencode_v2_plugin_is_self_contained() -> None:
    """Verify .opencode/plugins/flow.js uses native node:fs/node:path and exports V2 setup(ctx)."""
    plugin_js = (REPO_ROOT / ".opencode" / "plugins" / "flow.js").read_text(encoding="utf-8")
    assert 'id: "flow"' in plugin_js
    assert "async setup(ctx)" in plugin_js
    assert "node:fs" in plugin_js
    assert "node:path" in plugin_js
    assert "python3" not in plugin_js
    assert "managedConfig" not in plugin_js
