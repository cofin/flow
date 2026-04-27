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


def _write_skill(path: Path, *, name: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
name: {name}
description: {description}
---

# {name}

## Workflow

Follow the repo-specific workflow.

## Guardrails

Keep changes targeted.

## Validation

Run the relevant validation command.

## Example

Use this skill when the trigger applies.
""",
        encoding="utf-8",
    )


def test_skill_description_rejects_workflow_summary_terms(tmp_path: Path) -> None:
    skill_path = tmp_path / "postgres" / "SKILL.md"
    _write_skill(
        skill_path,
        name="postgres",
        description=(
            "Auto-activate for .sql files. Produces PostgreSQL queries and "
            "connection patterns. Use when writing PostgreSQL migrations."
        ),
    )
    _write_json(
        tmp_path / "postgres" / "agents" / "openai.yaml",
        {"interface": {"display_name": "PostgreSQL", "short_description": "PostgreSQL support"}},
    )

    violations = validate_skills.validate_skill(skill_path)

    assert any("must start with 'Use when'" in violation.message for violation in violations)
    assert any("workflow/output summary term" in violation.message for violation in violations)


def test_skill_requires_openai_metadata(tmp_path: Path) -> None:
    skill_path = tmp_path / "python" / "SKILL.md"
    _write_skill(
        skill_path,
        name="python",
        description="Use when editing Python files, pyproject.toml, uv workflows, ruff, mypy, or pytest.",
    )

    violations = validate_skills.validate_skill(skill_path)

    assert any("agents/openai.yaml missing" in violation.message for violation in violations)


def test_repo_skills_have_trigger_only_descriptions_and_openai_metadata() -> None:
    violations = []
    for skill_path in validate_skills.iter_skills():
        violations.extend(validate_skills.validate_skill(skill_path))

    assert violations == []


def test_repo_has_flow_lifecycle_skill_split() -> None:
    expected = {"flow", "flow-setup", "flow-planning", "flow-execution", "flow-sync-status", "flow-completion"}

    assert expected.issubset({path.parent.name for path in validate_skills.iter_skills()})


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
    """Claude's plugin.json declares hooks-claude.json explicitly; the validator
    must follow that pointer rather than picking up the Gemini-only hooks.json."""
    assert list(validate_skills.iter_claude_hook_configs()) == [REPO_ROOT / "hooks" / "hooks-claude.json"]


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


def test_makefile_recipes_fail_fast() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert ".SHELLFLAGS" in makefile
    assert "-e" in makefile
    assert "-o pipefail" in makefile
    assert "lint:" in makefile
    assert "uv run --extra dev tools/sync-codex-package.py" in makefile
    assert "validate-codex-manifest:" in makefile
    assert "codex-package-check:" in makefile
    assert (
        "check: lint validate-skills codex-package-check validate-codex-manifest "
        "validate-claude-manifest sync-manifests"
    ) in makefile


def test_repo_uses_supported_cursor_surface() -> None:
    assert not (REPO_ROOT / ".cursor-plugin" / "plugin.json").exists()
    assert (REPO_ROOT / ".cursor" / "rules" / "flow.mdc").is_file()


def test_repo_host_native_agent_surfaces_validate() -> None:
    expected = {"code-reviewer", "executor", "plan-generator", "prd-orchestrator"}

    assert {path.stem for path in validate_skills.iter_gemini_agents()} == expected
    assert {path.stem for path in validate_skills.iter_codex_agents()} == expected
    assert {path.stem for path in validate_skills.iter_opencode_agents()} == expected
    assert {path.stem.removesuffix(".agent") for path in validate_skills.iter_vscode_agents()} == expected

    violations = []
    for agent_path in validate_skills.iter_gemini_agents():
        violations.extend(validate_skills.validate_gemini_agent(agent_path))
        violations.extend(validate_skills.validate_claude_agent(agent_path))
    for agent_path in validate_skills.iter_codex_agents():
        violations.extend(validate_skills.validate_codex_agent(agent_path))
    for agent_path in validate_skills.iter_opencode_agents():
        violations.extend(validate_skills.validate_opencode_agent(agent_path))
    for agent_path in validate_skills.iter_vscode_agents():
        violations.extend(validate_skills.validate_vscode_agent(agent_path))

    assert violations == []


def test_repo_codex_manifest_validates() -> None:
    codex_violations = validate_skills.validate_manifest(REPO_ROOT / ".codex-plugin" / "plugin.json")

    assert codex_violations == []
