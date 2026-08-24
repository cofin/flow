from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_TEMPLATES = REPO_ROOT / "templates" / "agent" / "knowledge"


def _okf_contract() -> dict[str, object]:
    text = (REPO_ROOT / "skills" / "okf" / "SKILL.md").read_text(encoding="utf-8")
    marker = "<!-- okf-materialization-contract: start -->"
    section = text.split(marker, maxsplit=1)[1]
    raw = section.split("```yaml\n", maxsplit=1)[1].split("\n```", maxsplit=1)[0]
    loaded = yaml.safe_load(raw)
    assert isinstance(loaded, dict)
    return loaded


def test_minimal_unknown_project_has_no_fabricated_knowledge(tmp_path: Path) -> None:
    destination = tmp_path / ".agents" / "bundles" / "knowledge"
    shutil.copytree(KNOWLEDGE_TEMPLATES, destination)

    files = sorted(
        path.relative_to(destination).as_posix() for path in destination.rglob("*.md")
    )
    assert files == ["index.md"]
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in destination.rglob("*.md")
    )
    for invented_claim in (
        "Core Module",
        "Migration Discipline",
        "Ubiquitous Language",
        "ADR-0001",
        "Why Rejected",
    ):
        assert invented_claim not in text


def test_materialization_requires_repository_evidence_or_explicit_decision() -> None:
    contract = _okf_contract()

    assert contract["default_scaffold"] == [
        "bundles/index.md",
        "bundles/log.md",
        "bundles/product/product.md",
        "bundles/product/tech-stack.md",
        "bundles/knowledge/index.md",
        "bundles/knowledge/workflow.md",
    ]
    assert contract["repository_evidence"] == {
        "applies_to": ["architecture", "data-model", "domain", "pattern", "standard"],
        "required": ["repository_relative_paths", "symbols_or_observed_behavior"],
    }
    assert contract["decision_evidence"] == {
        "applies_to": ["decision", "rejected-alternative"],
        "required": ["explicit_user_decision", "recorded_at", "actor"],
    }
    assert contract["archive"] == {
        "resident_spec_directories": "forbidden",
        "effect": "knowledge_synthesis_log_append_and_completed_spec_removal",
    }


def test_materialization_preserves_project_shaped_nested_paths_and_reruns() -> None:
    contract = _okf_contract()

    assert contract["path_policy"] == {
        "shape": "repository_derived_hierarchy",
        "nested_paths": "preserve",
        "unknown_types": "tolerate",
        "rerun": "idempotent_without_duplicate_or_overwrite",
        "links": "resolve_before_commit",
    }

    index = (KNOWLEDGE_TEMPLATES / "index.md").read_text(encoding="utf-8")
    assert "patterns/<topic>.md" in index
    assert "](../patterns.md)" not in index
    assert not (KNOWLEDGE_TEMPLATES / "patterns.md").exists()

    skill = (REPO_ROOT / "skills" / "okf" / "SKILL.md").read_text(encoding="utf-8")
    for lazy_path in (
        "patterns/<topic>.md",
        "architecture/<area>.md",
        "domains/<domain>.md",
        "data-model/<area>.md",
        "decisions/<decision>.md",
        "standards/<topic>.md",
    ):
        assert lazy_path in skill
    assert "separate rejections tree" in " ".join(skill.split())


def test_empty_tags_do_not_satisfy_a_required_relevance_policy() -> None:
    contract = _okf_contract()

    assert contract["tags"] == {
        "optional_by_okf": True,
        "required_by_profile": "non_empty_lowercase_hyphenated_strings",
        "empty_list_satisfies_required": False,
    }


def test_public_guidance_never_advertises_a_flat_pattern_default() -> None:
    public_paths = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "skills").rglob("*.md")),
        *sorted((REPO_ROOT / "templates").rglob("*.md")),
    ]
    compatibility_paths = {
        "skills/flow/references/setup.md",
        "skills/okf/SKILL.md",
        "templates/agent/knowledge/index.md",
    }

    violations = []
    for path in public_paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if "knowledge/patterns.md" in text and relative not in compatibility_paths:
            violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert violations == []
    assert "knowledge/patterns/**/*.md" in (REPO_ROOT / "AGENTS.md").read_text(
        encoding="utf-8"
    )


def test_workflow_template_preserves_state_recovery_and_mutation_contract() -> None:
    workflow = (REPO_ROOT / "templates" / "agent" / "workflow.md").read_text(
        encoding="utf-8"
    )
    continuity = workflow.split("## Direct-read continuity", maxsplit=1)[1].split(
        "## Task and state operations", maxsplit=1
    )[0]
    operations = workflow.split("## Task and state operations", maxsplit=1)[1].split(
        "## Verification strategies", maxsplit=1
    )[0]

    journal_scan = continuity.index("transactions/*/journal.md")
    normal_work = continuity.index("Before selecting a flow or doing normal work")
    spec_read = continuity.index("candidate spec frontmatter")
    assert normal_work <= journal_scan < spec_read
    for state in (
        "prepared",
        "task_writes_started",
        "recovery_required",
        "contended",
        "rollback_in_progress",
    ):
        assert state in continuity
    assert "Jointly arbitrate every nonterminal journal" in continuity
    assert "recover the selected transaction from its recorded fragments" in continuity

    for guard in (
        "expected_plan_revision",
        "expected_plan_commit",
        "expected_state_revision",
    ):
        assert guard in operations
    journal_first = operations.index("prepared transaction journal")
    tracked_write = operations.index("before tracked state changes")
    assert journal_first < tracked_write
    assert "task-first/spec-last" in operations
    assert "record final validation before marking the journal terminal" in operations
    assert "never starts a replacement mutation" in operations


def test_workflow_template_resolves_plugin_default_skip_state_authority() -> None:
    workflow = (REPO_ROOT / "templates" / "agent" / "workflow.md").read_text(
        encoding="utf-8"
    )
    operations = workflow.split("## Task and state operations", maxsplit=1)[1].split(
        "## Verification strategies", maxsplit=1
    )[0]

    assert "plugin/default-skip mode" in operations
    assert "active packaged `flow-state` skill" in operations
    assert "its sibling `references/state.md`" in operations
    assert "do not require or synthesize a project-local skill path" in operations


def test_workflow_template_resolves_standalone_state_authority() -> None:
    workflow = (REPO_ROOT / "templates" / "agent" / "workflow.md").read_text(
        encoding="utf-8"
    )
    operations = workflow.split("## Task and state operations", maxsplit=1)[1].split(
        "## Verification strategies", maxsplit=1
    )[0]

    assert ".agents/skills/flow-state/SKILL.md" in operations
    assert "resolve `references/state.md` relative to it" in operations
    assert "If neither authority is available, stop before mutation" in operations
    graph = json.loads(
        (REPO_ROOT / "contracts/standalone-install.json").read_text(encoding="utf-8")
    )
    assert graph["nodes"]["skill:flow-state"]["source"] == "skills/flow-state"
    assert (REPO_ROOT / "skills/flow-state/references/state.md").is_file()
