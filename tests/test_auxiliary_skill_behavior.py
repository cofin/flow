from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("skill", "references", "semantic_markers"),
    [
        (
            "apilookup",
            ("lookup-strategy.md", "registry.json", "registry-schema.md"),
            ("staleness", "search"),
        ),
        ("architecture-critic", ("persona.md", "checklist.md"), ("6-12", "structural")),
        (
            "challenge",
            (
                "challenge-strategy.md",
                "../perspectives/references/critical-thinking.md",
            ),
            ("partially holds", "evidence"),
        ),
        (
            "consensus",
            (
                "consensus-strategy.md",
                "stance-rotation.md",
                "../perspectives/references/stances.md",
            ),
            ("confidence", "isolated"),
        ),
        (
            "deepthink",
            ("reasoning-strategy.md", "confidence-tracking.md"),
            ("hypothesis", "confidence"),
        ),
        (
            "devils-advocate",
            ("persona.md", "checklist.md"),
            ("failure mode", "severity"),
        ),
        (
            "docgen",
            ("docgen-strategy.md", "component-template.md"),
            ("manifest", "complete"),
        ),
        (
            "performance-analyst",
            ("persona.md", "checklist.md"),
            ("measurement", "hot path"),
        ),
        (
            "perspectives",
            ("critical-thinking.md", "stances.md"),
            ("advocate", "neutral"),
        ),
        ("security-auditor", ("persona.md", "checklist.md"), ("attack", "severity")),
        ("tracer", ("tracing-strategy.md", "trace-modes.md"), ("stop", "edge")),
    ],
)
def test_auxiliary_skills_link_distinct_behavior_authorities(
    skill: str, references: tuple[str, ...], semantic_markers: tuple[str, ...]
) -> None:
    skill_file = ROOT / "skills" / skill / "SKILL.md"
    text = skill_file.read_text().lower()

    for reference in references:
        assert (
            f"](references/{reference.lower()})" in text
            or f"]({reference.lower()})" in text
        )
    for marker in semantic_markers:
        assert marker in text


def test_debloat_requires_characterization_and_replacement_gate_proof() -> None:
    skill = (ROOT / "skills/debloat/SKILL.md").read_text().lower()
    gate_reference = ROOT / "skills/debloat/references/test-and-gate-debloat.md"

    assert "green-before/green-after characterization" in skill
    assert "representative violation" in skill
    assert "non-zero" in skill
    assert gate_reference.is_file()
    gate_text = gate_reference.read_text().lower()
    assert "replacement-first sequence" in gate_text
    assert "representative violation" in gate_text
    assert "non-zero" in gate_text


def test_debloat_has_no_duplicate_project_template_authority() -> None:
    assert (ROOT / "skills/debloat/SKILL.md").is_file()
    assert not (ROOT / "templates/agent/skills/debloat/SKILL.md").exists()
