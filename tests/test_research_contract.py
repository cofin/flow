"""Behavioral contract tests for bounded, read-only planning research."""

from __future__ import annotations

from pathlib import Path

import yaml

from tools.flow_contract import load_contract

REPO_ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _fenced_yaml(text: str, marker: str) -> dict[str, object]:
    section = text.split(marker, 1)[1]
    payload = section.split("```yaml\n", 1)[1].split("\n```", 1)[0]
    parsed = yaml.safe_load(payload)
    assert isinstance(parsed, dict)
    return parsed


def test_researcher_is_read_only_and_returns_a_closed_result() -> None:
    contract = load_contract(REPO_ROOT / "contracts" / "flow.yaml")
    researcher = contract.agents["researcher"]
    assert all(
        "file_write" not in requirements
        for requirements in researcher.tool_requirements.values()
    )

    prompt = _text("agents/researcher.md")
    assert "write research notes" not in prompt.lower()
    schema = _fenced_yaml(prompt, "<!-- researcher-result-contract: structured-result-v1 -->")
    assert schema == {
        "question": "string",
        "sources": [
            {
                "citation": "repository path and lines, or primary-source URL",
                "supports": ["finding id"],
            }
        ],
        "findings": [{"id": "finding id", "claim": "string"}],
        "confidence": "high | medium | low",
        "limitations": ["string"],
        "contradictions": [
            {
                "claims": ["finding id", "finding id"],
                "resolution": "string | unresolved",
            }
        ],
        "recommended_decision": "string",
    }
    assert "Do not create, edit, or move files" in prompt


def test_parent_validates_before_writing_and_retains_citations() -> None:
    for relative in ("agents/plan-generator.md", "agents/prd-orchestrator.md"):
        prompt = _text(relative)
        assert "Only the parent writes" in prompt
        assert "validate every researcher result" in prompt.lower()
        assert "malformed" in prompt.lower()
        assert "uncited" in prompt.lower()
        assert "unresolved contradiction" in prompt.lower()
        assert "preserve every source citation" in prompt.lower()


def test_fan_out_is_predicate_driven_and_proportional() -> None:
    research = _text("skills/flow/references/research.md")
    fan_out = _fenced_yaml(research, "<!-- research-fanout-contract: proportional-v1 -->")
    assert fan_out == {
        "researcher": {
            "when": "at least_two_independent_unknowns | current_external_evidence_required",
            "count": "one_per_independent_unknown_or_source_domain",
        },
        "interface_design": {"when": "competing_public_shapes"},
        "architecture_review": {
            "when": "new_seam | state_contract | public_contract | hard_to_reverse_choice"
        },
        "devils_advocacy": {
            "when": "destructive | security_sensitive | high_uncertainty"
        },
        "otherwise": "zero_extra_dispatches",
    }
    assert "one task per execution subagent" in research.lower()
    assert "3 to 5" not in research


def test_current_primary_sources_remain_mandatory() -> None:
    researcher = _text("agents/researcher.md").lower()
    research = _text("skills/flow/references/research.md").lower()
    assert "primary sources" in researcher
    assert "current external" in researcher
    assert "primary sources" in research
    assert "current source" in research
