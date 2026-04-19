from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gemini_extension_session_start_hook_uses_extension_path() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert command == "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/session-start"
    assert "${extensionPath}" in command
    assert "${CLAUDE_PLUGIN_ROOT:-" in command


def test_claude_plugin_relies_on_auto_discovered_root_hook_config() -> None:
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert "hooks" not in plugin


def test_shared_hook_manifest_supports_claude_runtime_resolution() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert command.startswith("${CLAUDE_PLUGIN_ROOT:-")
    assert command.endswith("}/hooks/session-start")


def test_shared_hook_manifest_uses_top_level_hooks_record() -> None:
    gemini_hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    assert "hooks" in gemini_hooks
    assert "SessionStart" in gemini_hooks["hooks"]


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
