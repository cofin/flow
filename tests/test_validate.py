"""Tests for the consolidated multi-harness repository validator."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.validate import (
    EXPECTED_AGENTS,
    EXPECTED_SKILLS,
    MAX_SKILL_FILE_BYTES,
    READONLY_AGENTS,
    REPO_ROOT,
    main,
    validate_agents,
    validate_anti_sprawl,
    validate_hooks,
    validate_lockfile,
    validate_manifests,
    validate_markdown_links,
    validate_repository,
    validate_skills,
)


def test_validate_repository_passes_on_live_checkout() -> None:
    """Verify that the live repository passes all multi-harness validation checks."""
    assert validate_repository(REPO_ROOT) == []
    assert main([]) == 0


def test_validate_manifests_detects_version_mismatch_and_invalid_keys(tmp_path: Path) -> None:
    """Verify that manifest validation flags version drift and disallowed Antigravity keys."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "flow"\nversion = "0.26.0"\n', encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "flow", "version": "0.25.0", "main": ".opencode/plugins/flow.js"}),
        encoding="utf-8",
    )
    (tmp_path / "plugin.json").write_text(
        json.dumps({"name": "flow", "displayName": "Flow", "version": "0.26.0", "hooks": "./hooks.json"}),
        encoding="utf-8",
    )
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "flow", "version": "0.26.0", "hooks": "./hooks/hooks-claude.json"}),
        encoding="utf-8",
    )
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "flow", "version": "0.26.0", "source": "./"}]}),
        encoding="utf-8",
    )
    (tmp_path / ".codex-plugin").mkdir()
    (tmp_path / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "flow", "version": "0.26.0"}),
        encoding="utf-8",
    )
    (tmp_path / ".cursor-plugin").mkdir()
    (tmp_path / ".cursor-plugin" / "plugin.json").write_text(
        json.dumps({"name": "flow", "version": "0.26.0", "hooks": "./hooks/hooks-cursor.json"}),
        encoding="utf-8",
    )
    (tmp_path / ".agents" / "plugins").mkdir(parents=True)
    (tmp_path / ".agents" / "plugins" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "flow", "version": "0.26.0", "source": {"path": "./"}}]}),
        encoding="utf-8",
    )

    errors = validate_manifests(tmp_path)
    assert any("package.json: version" in err for err in errors)
    assert any("disallowed Antigravity manifest keys: ['hooks']" in err for err in errors)


def test_validate_hooks_enforces_stop_hook_schemas_and_dynamic_opencode_context(tmp_path: Path) -> None:
    """Verify validate_hooks flags nested Antigravity Stop matchers, missing loop_limit, and static OpenCode caching."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)
    for script_name in ("session-start.sh", "session-start.ps1", "stop-check.sh", "stop-check.ps1"):
        shutil.copy2(REPO_ROOT / "hooks" / script_name, hooks_dir / script_name)

    (tmp_path / "hooks.json").write_text(
        json.dumps(
            {
                "flow-session-start": {"SessionStart": [{"type": "command", "command": "sh ./hooks/session-start.sh"}]},
                "flow-stop-check": {
                    "Stop": [{"matcher": "*", "hooks": [{"type": "command", "command": "sh ./hooks/stop-check.sh"}]}]
                },
            }
        ),
        encoding="utf-8",
    )
    (hooks_dir / "hooks-claude.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "startup",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "sh ./hooks/session-start.sh",
                                    "commandWindows": "powershell -File session-start.ps1",
                                }
                            ],
                        }
                    ],
                    "Stop": [{"type": "command", "command": "sh ./hooks/stop-check.sh"}],
                }
            }
        ),
        encoding="utf-8",
    )
    (hooks_dir / "hooks-cursor.json").write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {
                    "sessionStart": [{"command": "sh ./hooks/session-start.sh --harness cursor"}],
                    "stop": [{"command": "sh ./hooks/stop-check.sh --harness cursor"}],
                },
            }
        ),
        encoding="utf-8",
    )
    opencode_dir = tmp_path / ".opencode" / "plugins"
    opencode_dir.mkdir(parents=True)
    (opencode_dir / "flow.js").write_text(
        'const flowPlugin = { id: "flow", async setup(ctx) {\n'
        "  const summary = readBundleSummary(ctx.cwd);\n"
        "  return summary;\n"
        "} };\n",
        encoding="utf-8",
    )

    errors = validate_hooks(tmp_path)
    assert "hooks.json: Antigravity Stop must be a flat array of command handlers" in errors
    assert "hooks/hooks-claude.json: Stop must use nested matcher format" in errors
    assert "hooks/hooks-cursor.json: must declare hooks.stop with integer loop_limit" in errors
    assert ".opencode/plugins/flow.js: must invoke readBundleSummary dynamically per turn" in errors


def test_validate_skills_enforces_byte_cap_and_frontmatter(tmp_path: Path) -> None:
    """Verify that skill validation enforces the 24 KB Antigravity cap and description rules."""
    skills_dir = tmp_path / "skills"
    for name in EXPECTED_SKILLS:
        sdir = skills_dir / name
        sdir.mkdir(parents=True)
        (sdir / "SKILL.md").write_bytes(
            (
                f"---\r\nname: {name}\r\ndescription: Use when testing {name}.\r\n---\r\n\r\n"
                "## Workflow\r\n\r\nStep.\r\n\r\n## Guardrails\r\n\r\nRule.\r\n\r\n"
                "## Validation\r\n\r\nCheck.\r\n\r\n## Example\r\n\r\nEx.\r\n"
            ).encode()
        )

    assert validate_skills(tmp_path) == []

    oversized = "x" * MAX_SKILL_FILE_BYTES
    (skills_dir / "flow" / "SKILL.md").write_text(
        f"---\nname: flow\ndescription: Auto-activate for everything.\n---\n{oversized}",
        encoding="utf-8",
    )
    errors = validate_skills(tmp_path)
    assert any("exceeds 24000 byte cap" in err for err in errors)
    assert any("description must start with 'Use when'" in err for err in errors)
    assert any("forbidden term 'Auto-activate'" in err for err in errors)


def test_validate_agents_enforces_sandbox_policy_h1_headings_and_yaml_lists(tmp_path: Path) -> None:
    """Verify subagent validation enforces commandExecutionPolicy: sandbox, H1 headings, and YAML disallowedTools."""
    agents_dir = tmp_path / "agents"
    codex_dir = tmp_path / ".codex" / "agents"
    agents_dir.mkdir(parents=True)
    codex_dir.mkdir(parents=True)

    for name in EXPECTED_AGENTS:
        (agents_dir / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: Desc\nmodel: inherit\nmainAgent: true\nsubagent: true\n"
            "commandExecutionPolicy: off\nskills:\n  - flow\n---\n\n## Role\n",
            encoding="utf-8",
        )
        (codex_dir / f"{name}.toml").write_text(
            f'name = "{name}"\ndescription = "Desc"\nsandbox_mode = "read-only"\ndeveloper_instructions = "Follow."\n',
            encoding="utf-8",
        )

    errors = validate_agents(tmp_path)
    assert any("mainAgent must be false" in err for err in errors)
    assert any("commandExecutionPolicy must be 'sandbox'" in err for err in errors)
    assert any("missing required H1 heading '# Role & Identity'" in err for err in errors)
    assert any("read-only agent must declare readonly: true" in err for err in errors)

    for name in EXPECTED_AGENTS:
        is_ro = name in READONLY_AGENTS
        ro_yaml = (
            "readonly: true\ndisallowedTools:\n  - Edit\n  - MultiEdit\n  - NotebookEdit\n  - Write\n" if is_ro else ""
        )
        codex_sb = "read-only" if is_ro else "workspace-write"
        (agents_dir / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: Desc\nmodel: inherit\nmainAgent: false\nsubagent: true\n"
            f"commandExecutionPolicy: sandbox\n{ro_yaml}skills:\n  - flow\n---\n\n"
            "# Role & Identity\n\nRole.\n\n# Responsibilities\n\nWork.\n\n"
            "# Verification & Constraints\n\nVerify.\n\n# Output Contract\n\nOut.\n",
            encoding="utf-8",
        )
        (codex_dir / f"{name}.toml").write_text(
            f'name = "{name}"\ndescription = "Desc"\nsandbox_mode = "{codex_sb}"\ndeveloper_instructions = "Follow."\n',
            encoding="utf-8",
        )

    assert validate_agents(tmp_path) == []


def test_validate_anti_sprawl_and_lockfile(tmp_path: Path) -> None:
    """Verify anti-sprawl checks and lockfile host portability."""
    (tmp_path / "skills").mkdir()
    assert validate_anti_sprawl(tmp_path) == []

    (tmp_path / "CLAUDE.md").write_text("# Obsolete\n", encoding="utf-8")
    (tmp_path / "plugins" / "flow").mkdir(parents=True)
    sprawl_errors = validate_anti_sprawl(tmp_path)
    assert "Retired path must not exist: CLAUDE.md" in sprawl_errors
    assert "Retired path must not exist: plugins/flow" in sprawl_errors

    (tmp_path / "uv.lock").write_text(
        'registry = "https://pypi.org/simple"\nsdist = "https://files.pythonhosted.org/pkg.tar.gz"\n',
        encoding="utf-8",
    )
    assert validate_lockfile(tmp_path) == []

    (tmp_path / "uv.lock").write_text('registry = "https://internal.example.corp/simple"\n', encoding="utf-8")
    assert validate_lockfile(tmp_path) == [
        "uv.lock: non-public package host 'internal.example.corp' in 'https://internal.example.corp/simple'"
    ]


def test_validate_markdown_links_detects_broken_links(tmp_path: Path) -> None:
    """Verify that broken relative Markdown links are detected while code spans are ignored."""
    skills_dir = tmp_path / "skills" / "flow"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "See [missing](references/missing.md) and `[ignored](references/not-real.md)`.\n",
        encoding="utf-8",
    )
    errors = validate_markdown_links(tmp_path)
    assert errors == ["skills/flow/SKILL.md: broken relative link 'references/missing.md'"]
