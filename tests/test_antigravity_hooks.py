from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ANTIGRAVITY_HOOK_EVENTS = {"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}


def _load_agy_hooks() -> dict:
    return json.loads((REPO_ROOT / "hooks" / "hooks-agy.json").read_text(encoding="utf-8"))


def test_antigravity_root_plugin_manifest_exists() -> None:
    manifest_path = REPO_ROOT / "plugin.json"

    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://antigravity.google/schemas/v1/plugin.json"
    assert manifest["name"] == "flow"


def test_antigravity_hooks_use_only_real_events() -> None:
    # Antigravity has no SessionStart event; priming must ride PreInvocation.
    hooks = _load_agy_hooks()
    events = {event for spec in hooks.values() for event in spec}
    assert events, "hooks-agy.json must define at least one hook event"
    assert events <= ANTIGRAVITY_HOOK_EVENTS
    assert "PreInvocation" in events


def test_antigravity_hook_commands_are_python_free_and_root_anchored() -> None:
    hooks = _load_agy_hooks()
    commands = [
        handler["command"]
        for spec in hooks.values()
        for handlers in spec.values()
        for handler in handlers
    ]
    assert commands
    for command in commands:
        assert "python" not in command
        assert "${extensionPath}" not in command
        assert "${/}" not in command
        assert any(token in command for token in ("ANTIGRAVITY_PLUGIN_ROOT", "AGY_PLUGIN_ROOT", "PLUGIN_ROOT"))


def test_antigravity_pre_invocation_scripts_shipped() -> None:
    sh = REPO_ROOT / "hooks" / "agy-pre-invocation.sh"
    ps1 = REPO_ROOT / "hooks" / "agy-pre-invocation.ps1"
    assert sh.is_file() and ps1.is_file()
    assert "injectSteps" in sh.read_text(encoding="utf-8")
    assert "injectSteps" in ps1.read_text(encoding="utf-8")
