from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "validate-skills.py"


def _load_validate_skills_module():
    spec = importlib.util.spec_from_file_location("validate_skills", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_skills = _load_validate_skills_module()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_claude_manifest_rejects_invalid_hooks_shape(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".claude-plugin" / "plugin.json",
        {
            "name": "flow",
            "skills": ["./skills/"],
            "commands": ["./commands/"],
            "hooks": {"session-start": "../hooks/session-start"},
        },
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "commands").mkdir()

    violations = validate_skills.validate_manifest(tmp_path / ".claude-plugin" / "plugin.json")

    assert any("hooks" in violation.message.lower() for violation in violations)


def test_claude_manifest_rejects_missing_agent_paths(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".claude-plugin" / "plugin.json",
        {
            "name": "flow",
            "skills": ["./skills/"],
            "commands": ["./commands/"],
            "agents": ["./.claude-plugin/agents/"],
            "hooks": "./hooks/hooks-claude.json",
        },
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "commands").mkdir()
    _write_json(tmp_path / "hooks" / "hooks-claude.json", {"SessionStart": []})

    violations = validate_skills.validate_manifest(tmp_path / ".claude-plugin" / "plugin.json")

    assert any("./.claude-plugin/agents/" in violation.message for violation in violations)


def test_claude_hook_config_rejects_cursor_placeholder(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks" / "hooks.json"
    _write_json(
        hooks_path,
        {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "${extensionPath}/hooks/session-start",
                            }
                        ],
                    }
                ]
            }
        },
    )

    violations = validate_skills.validate_claude_hook_config(hooks_path)

    assert any("${extensionPath}" in violation.message for violation in violations)


def test_claude_manifest_accepts_valid_string_hooks_path(tmp_path: Path) -> None:
    _write_json(
        tmp_path / ".claude-plugin" / "plugin.json",
        {
            "name": "flow",
            "skills": ["./skills/"],
            "commands": ["./commands/"],
            "hooks": "./hooks/hooks-claude.json",
        },
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "commands").mkdir()
    _write_json(
        tmp_path / "hooks" / "hooks-claude.json",
        {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start",
                            }
                        ],
                    }
                ]
            }
        },
    )

    violations = validate_skills.validate_manifest(tmp_path / ".claude-plugin" / "plugin.json")
    violations.extend(validate_skills.validate_claude_hook_config(tmp_path / "hooks" / "hooks-claude.json"))

    assert violations == []


def test_hook_config_requires_top_level_hooks_record(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks" / "hooks-claude.json"
    _write_json(
        hooks_path,
        {
            "SessionStart": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start",
                        }
                    ],
                }
            ]
        },
    )

    violations = validate_skills.validate_claude_hook_config(hooks_path)

    assert any("top-level 'hooks' record" in violation.message for violation in violations)


def test_gemini_hook_config_rejects_claude_placeholder(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks" / "hooks.json"
    _write_json(
        hooks_path,
        {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start",
                            }
                        ],
                    }
                ]
            }
        },
    )

    violations = validate_skills.validate_gemini_hook_config(hooks_path)

    assert any("${CLAUDE_PLUGIN_ROOT}" in violation.message for violation in violations)


def test_repo_claude_hook_discovery_targets_claude_specific_config() -> None:
    assert list(validate_skills.iter_claude_hook_configs()) == [REPO_ROOT / "hooks" / "hooks.json"]


def test_shared_hook_config_allows_cross_host_fallback_command(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks" / "hooks.json"
    _write_json(
        hooks_path,
        {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/session-start",
                            }
                        ],
                    }
                ]
            }
        },
    )

    assert validate_skills.validate_claude_hook_config(hooks_path) == []
    assert validate_skills.validate_gemini_hook_config(hooks_path) == []


def test_repo_cursor_and_codex_manifests_still_validate() -> None:
    cursor_violations = validate_skills.validate_manifest(REPO_ROOT / ".cursor-plugin" / "plugin.json")
    codex_violations = validate_skills.validate_manifest(REPO_ROOT / ".codex-plugin" / "plugin.json")

    assert cursor_violations == []
    assert codex_violations == []
