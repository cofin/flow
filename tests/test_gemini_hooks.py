from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gemini_hook_manifest_uses_bare_extension_path_token() -> None:
    """Gemini hydrates ${extensionPath} and ${/} at extension-load time, before
    spawning the shell. Nested forms like ${CLAUDE_PLUGIN_ROOT:-${extensionPath}}
    are not template syntax — they get parsed by bash with neither var set, which
    expands to an empty prefix."""
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert "${extensionPath}" in command
    assert "${/}" in command
    assert "${CLAUDE_PLUGIN_ROOT" not in command, "Gemini manifest must not embed Claude env-var syntax"


def test_claude_plugin_points_to_dedicated_hook_manifest() -> None:
    """Both Claude and Gemini default-discover hooks/hooks.json; we resolve the
    conflict by giving Gemini that file and pointing Claude at hooks-claude.json
    via plugin.json's hooks field."""
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert plugin.get("hooks") == "./hooks/hooks-claude.json"
    assert (REPO_ROOT / "hooks" / "hooks-claude.json").is_file()


def test_claude_hook_manifest_uses_claude_plugin_root_env_var() -> None:
    hooks = json.loads((REPO_ROOT / "hooks" / "hooks-claude.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert "${CLAUDE_PLUGIN_ROOT}" in command
    assert "${extensionPath}" not in command, "Claude manifest must not embed Gemini template syntax"


def test_codex_hooks_relocated_to_dot_codex_directory() -> None:
    """The .codex-plugin/plugin.json `hooks` field is undocumented and does not
    fire. Codex reads hooks from .codex/hooks.json with camelCase event names."""
    codex_plugin = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "hooks" not in codex_plugin

    codex_hooks_path = REPO_ROOT / ".codex" / "hooks.json"
    assert codex_hooks_path.is_file()

    codex_hooks = json.loads(codex_hooks_path.read_text(encoding="utf-8"))
    assert "SessionStart" in codex_hooks["hooks"], "Codex uses PascalCase SessionStart event names"
    assert codex_hooks["hooks"]["SessionStart"][0].get("matcher") is not None


def test_gemini_hook_manifest_uses_top_level_hooks_record() -> None:
    gemini_hooks = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "hooks" in gemini_hooks
    assert "SessionStart" in gemini_hooks["hooks"]


def test_session_start_emits_claude_compatible_payload_when_claude_env_present() -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT / ".claude-plugin")

    result = subprocess.run(
        ["node", str(REPO_ROOT / "hooks" / "session-start.js")],
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


def test_session_start_emits_gemini_payload_when_gemini_session_present() -> None:
    """Gemini gets both hookSpecificOutput (for model context) and systemMessage
    (for user-visible session banner)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_PLUGIN_", "CODEX_PLUGIN_", "OPENCODE_PLUGIN_", "CURSOR_PLUGIN_"))}
    env["GEMINI_SESSION_ID"] = "test-session"

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / "session-start.sh")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "systemMessage" in payload, "Gemini hook must emit systemMessage for user-visible context"


def _codex_command(manifest_path: Path) -> str:
    hooks = json.loads(manifest_path.read_text(encoding="utf-8"))
    return hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]


def test_codex_hook_manifest_uses_plugin_root_token() -> None:
    """The Codex-native manifest must anchor paths to $PLUGIN_ROOT (canonical) so
    the hook resolves once installed, and must avoid Gemini tokens that bash
    cannot expand. Fixes flow-9qx / GH #64."""
    command = _codex_command(REPO_ROOT / "hooks" / "hooks-codex.json")

    assert "PLUGIN_ROOT" in command
    assert "${extensionPath}" not in command, "Codex manifest must not embed Gemini template syntax"
    assert "${/}" not in command, "Codex manifest must not embed Gemini path-separator token"
    assert "bun " in command and "node " in command and "bash " in command, "Codex hook keeps the bun||node||bash ladder"


def test_dot_codex_hooks_uses_plugin_root_token() -> None:
    """The in-repo project-layer manifest (.codex/hooks.json) must use the same
    $PLUGIN_ROOT anchoring, not a bare session-cwd-relative path."""
    command = _codex_command(REPO_ROOT / ".codex" / "hooks.json")

    assert "PLUGIN_ROOT" in command
    assert "${extensionPath}" not in command
    assert "${/}" not in command


def test_session_start_emits_codex_payload_when_plugin_root_present() -> None:
    """Codex exports PLUGIN_ROOT; the hook must detect it and emit the modern
    hookSpecificOutput shape."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_PLUGIN_", "CODEX_PLUGIN_", "OPENCODE_PLUGIN_", "CURSOR_PLUGIN_", "GEMINI_"))}
    env["PLUGIN_ROOT"] = str(REPO_ROOT)

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / "session-start.sh")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_session_start_honors_flow_host_override() -> None:
    """Codex's project-layer hook sets FLOW_HOST=codex but no PLUGIN_ROOT. The
    hook must still emit the Codex hookSpecificOutput shape (not the legacy
    additional_context fallback)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_PLUGIN_", "CODEX_PLUGIN_", "OPENCODE_PLUGIN_", "CURSOR_PLUGIN_", "GEMINI_", "PLUGIN_ROOT"))}
    env.pop("PLUGIN_ROOT", None)
    env["FLOW_HOST"] = "codex"

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / "session-start.sh")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "hookSpecificOutput" in payload, "FLOW_HOST=codex must force the Codex payload shape"
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_session_start_codex_works_outside_flow_repo() -> None:
    """Regression guard for the install path: with PLUGIN_ROOT pointing at the
    plugin install dir, the hook must work even when cwd is an unrelated dir."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_PLUGIN_", "CODEX_PLUGIN_", "OPENCODE_PLUGIN_", "CURSOR_PLUGIN_", "GEMINI_"))}
    env["PLUGIN_ROOT"] = str(REPO_ROOT)

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / "session-start.sh")],
        cwd="/tmp",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "hookSpecificOutput" in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_session_start_works_outside_flow_repo() -> None:
    """Regression test: previously the hook only worked when cwd had a hooks/
    directory because of the empty-prefix bug. Verify it works from /tmp."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_PLUGIN_", "CODEX_PLUGIN_", "OPENCODE_PLUGIN_", "CURSOR_PLUGIN_", "GEMINI_"))}
    env["GEMINI_SESSION_ID"] = "test-session"

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / "session-start.sh")],
        cwd="/tmp",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "hookSpecificOutput" in payload
