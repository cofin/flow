from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gemini_extension_session_start_hook_uses_extension_path() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    command = hooks["SessionStart"][0]["hooks"][0]["command"]

    assert command == "${extensionPath}/hooks/session-start"
    assert "${CLAUDE_PLUGIN_ROOT}" not in command


def test_claude_plugin_references_claude_specific_hook_config() -> None:
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert plugin["hooks"] == "./hooks/hooks-claude.json"


def test_claude_hook_manifest_uses_claude_plugin_root() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks-claude.json").read_text(encoding="utf-8"))

    command = hooks["SessionStart"][0]["hooks"][0]["command"]

    assert command == "${CLAUDE_PLUGIN_ROOT}/hooks/session-start"
    assert "${extensionPath}" not in command


def test_session_start_emits_claude_compatible_payload_when_claude_env_present() -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT / ".claude-plugin")

    result = subprocess.run(
        [str(REPO_ROOT / "hooks" / "session-start")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "additionalContext" in payload["hookSpecificOutput"]
