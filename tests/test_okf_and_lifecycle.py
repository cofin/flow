"""Tests for OKF v0.2 bundle validation and Flow lifecycle reference integrity."""

from __future__ import annotations

from pathlib import Path

from tools.validate import REPO_ROOT, validate_okf_bundle


def test_validate_okf_bundle_accepts_valid_bundle_and_checks_footnotes(tmp_path: Path) -> None:
    """Verify OKF v0.2 bundle validation enforces root index.md, reserved files, and source footnotes."""
    bundle_dir = tmp_path / ".agents" / "bundles"
    knowledge_dir = bundle_dir / "knowledge" / "patterns"
    knowledge_dir.mkdir(parents=True)

    (bundle_dir / "index.md").write_text(
        '---\nokf_version: "0.2"\nbundle: sample-repo\n---\n\n# Sample Bundle\n',
        encoding="utf-8",
    )
    (bundle_dir / "log.md").write_text("## 2026-11-01 — Setup\n\nInitialized bundle.\n", encoding="utf-8")
    (knowledge_dir / "serialization.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Serialization\n"
        "description: Centralized msgspec JSON helpers.\n"
        "status: stable\n"
        "sources:\n"
        "  - id: ser-1\n"
        "    resource: src/ser.py::encode_json\n"
        "    title: Serializer\n"
        "---\n\n"
        "<!-- truth: start -->\n"
        "- Use `encode_json`[^ser-1].\n"
        "<!-- truth: end -->\n\n"
        "[^ser-1]: `src/ser.py::encode_json` — Serializer.\n",
        encoding="utf-8",
    )

    assert validate_okf_bundle(bundle_dir) == []

    (knowledge_dir / "serialization.md").write_text(
        "---\n"
        "type: Pattern\n"
        "title: Serialization\n"
        "description: Centralized msgspec JSON helpers.\n"
        "sources:\n"
        "  - id: missing-fn\n"
        "    resource: src/ser.py\n"
        "---\n\nBody without footnote definition.\n",
        encoding="utf-8",
    )
    errors = validate_okf_bundle(bundle_dir)
    assert errors == [
        "knowledge/patterns/serialization.md: source id 'missing-fn' missing matching [^missing-fn]: footnote in body"
    ]


def test_state_contract_and_lifecycle_references_stay_lean() -> None:
    """Verify that skills/flow/references/state.md stays compact and all lifecycle references exist."""
    refs_dir = REPO_ROOT / "skills" / "flow" / "references"
    expected_refs = {
        "archive.md",
        "cleanup.md",
        "discipline.md",
        "finish.md",
        "implement.md",
        "interaction.md",
        "learn.md",
        "plan.md",
        "prd.md",
        "research.md",
        "revert.md",
        "review.md",
        "revise.md",
        "setup.md",
        "state.md",
        "status.md",
        "validate.md",
    }
    found_refs = {p.name for p in refs_dir.glob("*.md")}
    assert found_refs == expected_refs

    state_bytes = (refs_dir / "state.md").stat().st_size
    assert state_bytes < 12000


def test_flow_docs_is_tool_agnostic_and_core_engineering_disciplines_exist() -> None:
    """Verify flow-docs is tool-agnostic and core Flow disciplines avoid external source names."""
    docs_refs_dir = REPO_ROOT / "skills" / "flow-docs" / "references"
    found_docs_refs = {p.name for p in docs_refs_dir.glob("*.md")}
    assert found_docs_refs == {
        "agent-context.md",
        "prose-and-documentation.md",
        "prs-commits-and-changelogs.md",
    }

    for doc_file in (REPO_ROOT / "skills" / "flow-docs").rglob("*.md"):
        lowered = doc_file.read_text(encoding="utf-8").lower()
        for forbidden_lockin in ("zensical", "mkdocstrings", "griffe", "shibuya"):
            assert forbidden_lockin not in lowered

    plan_text = (REPO_ROOT / "skills" / "flow" / "references" / "plan.md").read_text(encoding="utf-8")
    assert "Problem Statement & Objectives" in plan_text
    assert "Zero-Context Isolation Rules" in plan_text
    assert "Compare Interface Alternatives" in plan_text

    prd_text = (REPO_ROOT / "skills" / "flow" / "references" / "prd.md").read_text(encoding="utf-8")
    assert "North Star Goal & Problem Framing" in prd_text

    implement_text = (REPO_ROOT / "skills" / "flow" / "references" / "implement.md").read_text(encoding="utf-8")
    assert "Public-Seam TDD" in implement_text
    assert "Hypothesis-Driven Bug Diagnosis Loop" in implement_text

    review_text = (REPO_ROOT / "skills" / "flow" / "references" / "review.md").read_text(encoding="utf-8")
    assert "Baseline Structural Code Smells" in review_text
    assert "quality-review-v1" in review_text

    forbidden_external_and_project_terms = (
        "elephant",
        "goldfish",
        "conductor",
        "heilmeier",
        "fowler",
        "pocock",
        "docgen",
        "grilling",
        "tracer-bullet",
        "writing-for-agents",
        "tools/validate.py",
        "make validate",
        "make release",
        "bump-my-version",
        "single-file-validator",
        "flow-session-start",
        "v0.24",
        "v0.25",
        "zensical",
        "mkdocstrings",
    )
    for path in (
        *REPO_ROOT.glob("skills/**/*.md"),
        *REPO_ROOT.glob("agents/*.md"),
        *REPO_ROOT.glob(".codex/agents/*.toml"),
        *REPO_ROOT.glob("rules/*.md"),
        *REPO_ROOT.glob("templates/**/*.md"),
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
    ):
        text_lower = path.read_text(encoding="utf-8").lower()
        for term in forbidden_external_and_project_terms:
            assert term not in text_lower, f"{path.relative_to(REPO_ROOT)} contains forbidden term {term!r}"
