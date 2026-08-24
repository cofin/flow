from __future__ import annotations

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
