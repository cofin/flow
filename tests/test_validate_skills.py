from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "validate.py"
SYNC_LOCAL_SKILLS_PATH = REPO_ROOT / "tools" / "sync-local-skill-templates.py"


def _load_validate_skills_module():
    spec = importlib.util.spec_from_file_location("validate_skills", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_skills = _load_validate_skills_module()


def _load_sync_local_skills_module():
    spec = importlib.util.spec_from_file_location(
        "sync_local_skill_templates", SYNC_LOCAL_SKILLS_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_local_skills = _load_sync_local_skills_module()


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
        {
            "interface": {
                "display_name": "PostgreSQL",
                "short_description": "PostgreSQL support",
            }
        },
    )

    violations = validate_skills.validate_skill(skill_path)

    assert any(
        "must start with 'Use when'" in violation.message for violation in violations
    )
    assert any(
        "workflow/output summary term" in violation.message for violation in violations
    )


def test_skill_requires_openai_metadata(tmp_path: Path) -> None:
    skill_path = tmp_path / "python" / "SKILL.md"
    _write_skill(
        skill_path,
        name="python",
        description="Use when editing Python files, pyproject.toml, uv workflows, ruff, mypy, or pytest.",
    )

    violations = validate_skills.validate_skill(skill_path)

    assert any(
        "agents/openai.yaml missing" in violation.message for violation in violations
    )


def test_repo_skills_have_trigger_only_descriptions_and_openai_metadata() -> None:
    violations = []
    for skill_path in validate_skills.iter_skills():
        violations.extend(validate_skills.validate_skill(skill_path))

    assert violations == []


def test_repo_has_flow_lifecycle_skill_split() -> None:
    expected = {
        "flow",
        "flow-setup",
        "flow-planning",
        "flow-execution",
        "flow-sync-status",
        "flow-completion",
    }

    assert expected.issubset(
        {path.parent.name for path in validate_skills.iter_skills()}
    )


def test_repo_local_skill_templates_are_generated_and_current() -> None:
    output_root = REPO_ROOT / "templates" / "agent" / "skills"
    result = subprocess.run(
        [
            sys.executable,
            str(SYNC_LOCAL_SKILLS_PATH),
            "--check",
            "--repo-root",
            str(REPO_ROOT),
            "--output-root",
            str(output_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "Local skill templates are current.\n"
    assert set(sync_local_skills.APPROVED_SKILL_FILES) == {"debloat", "flow-state"}
    assert all(
        not relative.startswith("scripts/")
        for files in sync_local_skills.APPROVED_SKILL_FILES.values()
        for relative in files
    )


def test_local_skill_template_check_rejects_isolated_mutation(tmp_path: Path) -> None:
    output_root = tmp_path / "templates" / "agent" / "skills"
    sync_local_skills.write_templates(REPO_ROOT, output_root)
    mutated = output_root / "debloat" / "SKILL.md"
    mutated.write_text(
        mutated.read_text(encoding="utf-8") + "\nmutation\n", encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SYNC_LOCAL_SKILLS_PATH),
            "--check",
            "--repo-root",
            str(REPO_ROOT),
            "--output-root",
            str(output_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == (
        f"Local skill templates are stale:\n  - stale local skill template: {mutated}\n"
    )


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

    violations = validate_skills.validate_manifest(
        tmp_path / ".claude-plugin" / "plugin.json"
    )

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

    violations = validate_skills.validate_manifest(
        tmp_path / ".claude-plugin" / "plugin.json"
    )

    assert any(
        "./.claude-plugin/agents/" in violation.message for violation in violations
    )


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

    violations = validate_skills.validate_manifest(
        tmp_path / ".claude-plugin" / "plugin.json"
    )
    violations.extend(
        validate_skills.validate_claude_hook_config(
            tmp_path / "hooks" / "hooks-claude.json"
        )
    )

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

    assert any(
        "top-level 'hooks' record" in violation.message for violation in violations
    )


def test_antigravity_hook_config_rejects_legacy_extension_tokens(
    tmp_path: Path,
) -> None:
    hooks_path = tmp_path / "hooks.json"
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
                                "command": "bash ${extensionPath}${/}hooks${/}session-start.sh",
                            }
                        ],
                    }
                ]
            }
        },
    )

    violations = validate_skills.validate_antigravity_hook_config(hooks_path)

    assert any(
        "legacy extension template tokens" in violation.message
        for violation in violations
    )


def test_repo_claude_hook_discovery_targets_claude_specific_config() -> None:
    """Claude's plugin.json declares hooks-claude.json explicitly."""
    assert list(validate_skills.iter_claude_hook_configs()) == [
        REPO_ROOT / "hooks" / "hooks-claude.json"
    ]


def test_antigravity_hook_config_accepts_plugin_root_command(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks.json"
    _write_json(
        hooks_path,
        {
            "flow-priming": {
                "PreInvocation": [
                    {
                        "type": "command",
                        "command": 'bash "${PLUGIN_ROOT:-${ANTIGRAVITY_PLUGIN_ROOT:-.}}/hooks/agy-pre-invocation.sh"',
                    }
                ]
            }
        },
    )

    assert validate_skills.validate_antigravity_hook_config(hooks_path) == []


def test_antigravity_hook_config_rejects_session_start(tmp_path: Path) -> None:
    # Antigravity has no SessionStart event; registering one must be flagged.
    hooks_path = tmp_path / "hooks.json"
    _write_json(
        hooks_path,
        {
            "flow-priming": {
                "SessionStart": [
                    {
                        "type": "command",
                        "command": 'bash "${PLUGIN_ROOT:-.}/hooks/session-start.sh"',
                    }
                ]
            }
        },
    )

    violations = validate_skills.validate_antigravity_hook_config(hooks_path)
    assert any(
        "SessionStart" in v.message or "unknown Antigravity event" in v.message
        for v in violations
    )


def test_makefile_recipes_fail_fast() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert ".SHELLFLAGS" in makefile
    assert "-e" in makefile
    assert "-o pipefail" in makefile
    assert "lint:" in makefile
    assert "uv run --extra dev tools/sync-codex-package.py" in makefile
    assert "validate:" in makefile
    assert "codex-package-check:" in makefile
    assert (
        "check: lint sync-codex-package codex-package-check validate sync-manifests test"
    ) in makefile


def test_repo_uses_supported_cursor_surface() -> None:
    assert not (REPO_ROOT / ".cursor-plugin" / "plugin.json").exists()
    assert (REPO_ROOT / ".cursor" / "rules" / "flow.mdc").is_file()


def test_repo_harness_native_agent_surfaces_validate() -> None:
    generated_expected = {
        "code-reviewer",
        "executor",
        "flow-reconciler",
        "plan-generator",
        "prd-orchestrator",
    }
    canonical_expected = generated_expected | {"quality-reviewer"}

    assert {
        path.stem for path in validate_skills.iter_antigravity_agents()
    } == canonical_expected
    assert {
        path.stem for path in validate_skills.iter_codex_agents()
    } == generated_expected
    assert {
        path.stem for path in validate_skills.iter_opencode_agents()
    } == generated_expected
    assert {
        path.stem.removesuffix(".agent")
        for path in validate_skills.iter_vscode_agents()
    } == generated_expected

    violations = []
    for agent_path in validate_skills.iter_antigravity_agents():
        violations.extend(validate_skills.validate_antigravity_agent(agent_path))
        violations.extend(validate_skills.validate_claude_agent(agent_path))
    for agent_path in validate_skills.iter_codex_agents():
        violations.extend(validate_skills.validate_codex_agent(agent_path))
    for agent_path in validate_skills.iter_opencode_agents():
        violations.extend(validate_skills.validate_opencode_agent(agent_path))
    for agent_path in validate_skills.iter_vscode_agents():
        violations.extend(validate_skills.validate_vscode_agent(agent_path))

    assert violations == []


def test_repo_codex_manifest_validates() -> None:
    codex_violations = validate_skills.validate_manifest(
        REPO_ROOT / ".codex-plugin" / "plugin.json"
    )

    assert codex_violations == []


def test_skill_uses_bundles_directory_layout() -> None:
    skill_content = (REPO_ROOT / "skills" / "flow" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert ".agents/bundles/specs/" in skill_content
    assert ".agents/specs/" not in skill_content


def _write_okf_file(path: Path, frontmatter: str, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{content}", encoding="utf-8")


def test_validate_okf_flow_frontmatter_fails_on_missing_required_fields(
    tmp_path: Path,
) -> None:
    # Missing required field 'state'
    spec_path = tmp_path / "bundles" / "specs" / "test-flow" / "spec.md"
    _write_okf_file(
        spec_path,
        """
type: Spec
flow_id: test-flow
title: Test flow
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    violations = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert any(
        "missing required field" in v.message and "state" in v.message
        for v in violations
    )


def test_validate_okf_task_frontmatter_fails_on_missing_fields(tmp_path: Path) -> None:
    # Missing required field 'state' in task
    spec_path = tmp_path / "bundles" / "specs" / "test-flow" / "spec.md"
    _write_okf_file(
        spec_path,
        """
type: Spec
flow_id: test-flow
title: Test flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )
    task_path = spec_path.parent / "tasks" / "001-task.md"
    _write_okf_file(
        task_path,
        """
type: Task
id: test-flow:001-task
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    violations = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert any(
        "missing required field" in v.message and "state" in v.message
        for v in violations
    )


def test_validate_okf_task_referenced_files_exist(tmp_path: Path) -> None:
    spec_path = tmp_path / "bundles" / "specs" / "test-flow" / "spec.md"
    _write_okf_file(
        spec_path,
        """
type: Spec
flow_id: test-flow
title: Test flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )
    task_path = spec_path.parent / "tasks" / "001-task.md"
    # References non-existent file 'src/non_existent.py'
    _write_okf_file(
        task_path,
        """
type: Task
id: test-flow:001-task
state: closed
depends_on: []
files:
  - src/non_existent.py
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    violations = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert any(
        "referenced file does not exist" in v.message
        and "src/non_existent.py" in v.message
        for v in violations
    )

    # Let's create the file and make sure validation passes
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "non_existent.py").write_text("# exists now", encoding="utf-8")
    violations2 = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert not any(
        "referenced file does not exist" in v.message
        and "src/non_existent.py" in v.message
        for v in violations2
    )


def test_validate_okf_task_id_format(tmp_path: Path) -> None:
    spec_path = tmp_path / "bundles" / "specs" / "test-flow" / "spec.md"
    _write_okf_file(
        spec_path,
        """
type: Spec
flow_id: test-flow
title: Test flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )
    task_path = spec_path.parent / "tasks" / "001-task.md"
    # Task ID does not match expected format '<flow_id>:<task_name>' (uses 'wrong-flow' instead of 'test-flow')
    _write_okf_file(
        task_path,
        """
id: wrong-flow:001-task
status: open
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    violations = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert any(
        "task ID prefix" in v.message and "test-flow" in v.message for v in violations
    )


def test_validate_okf_task_orphaned_fails(tmp_path: Path) -> None:
    spec_path = tmp_path / "bundles" / "specs" / "test-flow" / "spec.md"
    _write_okf_file(
        spec_path,
        """
type: Spec
flow_id: test-flow
title: Test flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
        content="""
# Test Flow

## Implementation Plan

### Phase 1: Setup
- [ ] Task 1.1: First task
""",
    )

    # 1. Valid task file (1.1.md)
    _write_okf_file(
        spec_path.parent / "tasks" / "1.1.md",
        """
id: test-flow:1.1
status: open
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    # 2. Orphaned task file (1.2.md - not in spec.md checklist!)
    _write_okf_file(
        spec_path.parent / "tasks" / "1.2.md",
        """
id: test-flow:1.2
status: open
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
""",
    )

    violations = validate_skills.validate_okf_bundle(
        spec_path.parent, repo_root=tmp_path
    )
    assert any(
        "orphaned task file" in v.message and "1.2" in v.message for v in violations
    )
