from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


import sys

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_antigravity_root_plugin_manifest_exists() -> None:
    manifest_path = REPO_ROOT / "plugin.json"

    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://antigravity.google/schemas/v1/plugin.json"
    assert manifest["name"] == "flow"
    assert "Context-Driven Development" in manifest["description"]


def test_antigravity_root_hook_manifest_uses_plugin_root_env_vars() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks-agy.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["command"]

    assert "ANTIGRAVITY_PLUGIN_ROOT" in command
    assert "PLUGIN_ROOT" in command
    assert "${extensionPath}" not in command
    assert "${/}" not in command
    assert "Gemini" not in hooks["hooks"]["SessionStart"][0].get("description", "")


def test_session_start_emits_antigravity_payload_when_antigravity_root_present() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "priming.py")],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "systemMessage" not in payload
