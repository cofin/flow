from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_setup_does_not_create_flows_md() -> None:
    for relative_path in (
        "commands/flow/setup.toml",
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "skills/flow/references/setup.md",
    ):
        text = _read(relative_path)
        assert "flows.md - Empty flow registry" not in text


def test_setup_defines_new_paths() -> None:
    for relative_path in (
        "commands/flow/setup.toml",
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "skills/flow/references/setup.md",
    ):
        text = _read(relative_path)
        assert "bundles/specs/" in text
        assert "bundles/knowledge/" in text
        assert "knowledge/index.md" not in text or "bundles/knowledge/index.md" in text


def test_setup_prompts_for_branched_workspaces() -> None:
    for relative_path in (
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "commands/flow/setup.toml",
    ):
        text = _read(relative_path)
        assert "branched workspaces" in text
        assert "use_branched_workspaces" in text


def test_setup_performs_environment_detection() -> None:
    for relative_path in (
        "commands/flow-setup.md",
        "templates/opencode/commands/flow-setup.md",
        "commands/flow/setup.toml",
    ):
        text = _read(relative_path)
        assert "Environment & Harness Detection" in text
        assert "hooks.json" in text


def test_setup_summary_is_inventory_driven_and_fail_closed() -> None:
    text = _read("skills/flow-setup/SKILL.md")

    for required in (
        "migration-inventory.json",
        "source/destination",
        "last_successful_step",
        "resume_operation",
        "postconditions",
        ".agents/skills/",
    ):
        assert required in text
    assert "setup_status: complete" in text
    assert "A second identical run" in text


def test_setup_reference_defines_deterministic_migration_resume() -> None:
    text = _read("skills/flow/references/setup.md")
    normalized = " ".join(text.split())

    for required in (
        "setup-migration-v1",
        "migration-inventory.json",
        "semantic_mappings",
        "approved_at",
        "last_successful_step",
        "resume_operation",
        "source/destination count",
        "fresh approval",
        "plan_revision",
        "plan_commit",
    ):
        assert required in normalized


def test_setup_preserves_project_shaped_nested_knowledge() -> None:
    summary = _read("skills/flow-setup/SKILL.md")
    reference = _read("skills/flow/references/setup.md")
    agents = _read("AGENTS.md")

    assert "project-shaped nested knowledge" in summary
    assert "nested relative path" in reference
    assert "knowledge indexes and links" in reference
    assert "structure is scope-derived" in reference
    for relative_path in (
        "knowledge/data-model/schema.md",
        "knowledge/app-design/services.md",
        "knowledge/standards/testing.md",
    ):
        assert relative_path in reference
    assert "relative paths unchanged" in reference
    assert "flat `knowledge/` chapters" not in summary
    assert "THE synthesized current-state chapters, flat" not in agents


def test_setup_never_mutates_git_tags() -> None:
    agents = _read("AGENTS.md")

    assert "never create, move, force-update, or delete Git tags" in agents
    for relative_path in (
        "skills/flow-setup/SKILL.md",
        "skills/flow/references/setup.md",
    ):
        assert "git tag" not in _read(relative_path).lower()
