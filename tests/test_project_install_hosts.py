from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "install-project-flow.py"
SPEC = importlib.util.spec_from_file_location("install_project_flow_hosts", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


@pytest.mark.parametrize(
    ("host", "present", "absent"),
    [
        ("antigravity", ".agents/agents/executor.md", ".claude/commands/flow-setup.md"),
        (
            "claude_code",
            ".claude/commands/flow-setup.md",
            ".opencode/commands/flow-setup.md",
        ),
        ("codex_cli", ".codex/agents/executor.toml", ".claude/commands/flow-setup.md"),
        ("cursor", ".agents/flow/agents/researcher.md", ".codex/agents/executor.toml"),
        (
            "opencode",
            ".opencode/commands/flow-setup.md",
            ".claude/commands/flow-setup.md",
        ),
        (
            "openclaw",
            ".agents/flow/agents/researcher.md",
            ".opencode/commands/flow-setup.md",
        ),
        (
            "vscode_copilot",
            ".github/agents/executor.agent.md",
            ".claude/commands/flow-setup.md",
        ),
    ],
)
def test_clean_plugin_free_host_gets_complete_selected_surface(
    tmp_path: Path, host: str, present: str, absent: str
) -> None:
    project = tmp_path / host
    project.mkdir()
    result = INSTALLER.install_project_flow(
        project, source_root=REPO_ROOT, mode="install", host=host
    )
    assert result.action == "installed"
    assert (project / present).is_file()
    assert not (project / absent).exists()
    for skill in INSTALLER.PORTABLE_SKILLS:
        assert (project / ".agents" / "skills" / skill / "SKILL.md").is_file()
    for role in ("executor", "plan-generator", "quality-reviewer", "researcher"):
        assert (project / ".agents" / "flow" / "agents" / f"{role}.md").is_file()
    researcher = (project / ".agents/flow/agents/researcher.md").read_text()
    assert "structured-result-v1" in researcher
    state = json.loads((project / ".agents/setup-state.json").read_text())
    assert state["project_install"]["active_host"] == host


def test_generated_template_gate_reports_missing_stale_and_unmanaged(
    tmp_path: Path,
) -> None:
    generator_path = REPO_ROOT / "tools/sync-standalone-skill-templates.py"
    spec = importlib.util.spec_from_file_location(
        "standalone_generator", generator_path
    )
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    output = tmp_path / "skills"
    generator.write_templates(REPO_ROOT, output)
    assert generator.check_templates(REPO_ROOT, output) == []

    missing = output / "flow" / "SKILL.md"
    missing.unlink()
    assert any(
        "missing standalone skill template: flow/SKILL.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )
    generator.write_templates(REPO_ROOT, output)
    stale = output / "flow" / "SKILL.md"
    stale.write_text("stale\n")
    assert any(
        "stale standalone skill template: flow/SKILL.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )
    generator.write_templates(REPO_ROOT, output)
    unmanaged = output / "flow" / "unmanaged.md"
    unmanaged.write_text("unexpected\n")
    assert any(
        "unmanaged standalone skill template: flow/unmanaged.md" in item
        for item in generator.check_templates(REPO_ROOT, output)
    )


def test_installer_refuses_stale_generated_skill_before_writes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    canonical = source / "skills/example/SKILL.md"
    generated = source / "templates/agent/skills/example/SKILL.md"
    canonical.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    canonical.write_text("canonical\n")
    generated.write_text("stale\n")
    original = INSTALLER.PORTABLE_SKILLS
    original_generated = INSTALLER.GENERATED_STANDALONE_SKILLS
    INSTALLER.PORTABLE_SKILLS = ("example",)
    INSTALLER.GENERATED_STANDALONE_SKILLS = frozenset({"example"})
    try:
        with pytest.raises(
            INSTALLER.InstallError, match="stale generated standalone skill: example"
        ):
            INSTALLER._standalone_files(source, "cursor")
    finally:
        INSTALLER.PORTABLE_SKILLS = original
        INSTALLER.GENERATED_STANDALONE_SKILLS = original_generated


def test_unsupported_host_and_duplicate_authority_refuse_without_writes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(INSTALLER.InstallError, match="unsupported active host"):
        INSTALLER.install_project_flow(
            project, source_root=REPO_ROOT, mode="install", host="unknown"
        )
    assert not (project / ".agents").exists()

    collision = project / ".agents/skills/flow/SKILL.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("another authority\n")
    with pytest.raises(INSTALLER.InstallError, match="unmanaged target collision"):
        INSTALLER.install_project_flow(
            project, source_root=REPO_ROOT, mode="install", host="cursor"
        )
    assert collision.read_text() == "another authority\n"
