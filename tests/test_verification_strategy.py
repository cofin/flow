from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DISCIPLINE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "discipline.md"


def _marked_yaml(path: Path, name: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(name)}: start -->\s*```yaml\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(name)}: end -->",
        content,
        re.DOTALL,
    )
    assert match is not None, f"missing {name} block in {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


@dataclass(frozen=True)
class TaskFixture:
    change_class: str
    verification_strategy: str
    initial_evidence: str
    waiver: dict[str, str] | None = None
    discovered_implementation_gap: bool = False


def _diagnose(task: TaskFixture, contract: dict[str, Any]) -> list[str]:
    diagnostics: list[str] = []
    strategies = contract["strategies"]
    matching = [
        name
        for name, record in strategies.items()
        if record["change_class"] == task.change_class
    ]
    if len(matching) != 1:
        return [f"unknown change class: {task.change_class}"]
    expected = matching[0]
    if task.verification_strategy != expected:
        diagnostics.append(
            f"{task.change_class} requires {expected}, got {task.verification_strategy}"
        )

    red_evidence = {
        "focused_behavioral_test_fails_for_missing_behavior",
        "focused_reproduction_fails_for_reported_defect",
    }
    if task.initial_evidence in red_evidence and expected not in {
        "behavior_tdd",
        "regression_tdd",
    }:
        diagnostics.append(
            f"artificial TDD is invalid for {task.change_class}; use {strategies[expected]['initial_evidence']}"
        )

    if task.waiver is not None:
        required = set(contract["waiver"]["required"])
        missing = sorted(required - set(task.waiver))
        if missing:
            diagnostics.append(f"verification waiver missing: {', '.join(missing)}")

    if task.discovered_implementation_gap and expected == "integration_acceptance":
        diagnostics.append("integration acceptance implementation gap requires revise")
    return diagnostics


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    parsed = _marked_yaml(DISCIPLINE_PATH, "verification-strategy-contract")
    assert parsed["contract"] == "verification-strategy-v1"
    return parsed


@pytest.mark.parametrize(
    ("change_class", "expected_strategy", "initial_evidence"),
    [
        (
            "new_observable_behavior",
            "behavior_tdd",
            "focused_behavioral_test_fails_for_missing_behavior",
        ),
        (
            "defect_correction",
            "regression_tdd",
            "focused_reproduction_fails_for_reported_defect",
        ),
        (
            "behavior_preserving_refactor_or_deletion",
            "characterization",
            "focused_behavior_baseline_passes_before_change",
        ),
        (
            "manifest_config_generated_or_tooling",
            "static_validation",
            "native_parser_lint_type_or_build_baseline",
        ),
        (
            "links_examples_or_document_structure",
            "documentation_validation",
            "docs_native_baseline",
        ),
        (
            "composition_of_existing_contracts",
            "integration_acceptance",
            "focused_integration_baseline_passes",
        ),
    ],
)
def test_change_class_selects_exact_strategy(
    contract: dict[str, Any],
    change_class: str,
    expected_strategy: str,
    initial_evidence: str,
) -> None:
    task = TaskFixture(change_class, expected_strategy, initial_evidence)

    assert _diagnose(task, contract) == []
    assert (
        contract["strategies"][expected_strategy]["initial_evidence"]
        == initial_evidence
    )


@pytest.mark.parametrize(
    ("change_class", "strategy"),
    [
        ("manifest_config_generated_or_tooling", "static_validation"),
        ("links_examples_or_document_structure", "documentation_validation"),
        ("behavior_preserving_refactor_or_deletion", "characterization"),
    ],
)
def test_nonbehavior_work_rejects_artificial_red_evidence(
    contract: dict[str, Any], change_class: str, strategy: str
) -> None:
    task = TaskFixture(
        change_class,
        strategy,
        "focused_behavioral_test_fails_for_missing_behavior",
    )

    assert _diagnose(task, contract) == [
        f"artificial TDD is invalid for {change_class}; use "
        f"{contract['strategies'][strategy]['initial_evidence']}"
    ]


def test_invalid_strategy_diagnoses_expected_selection(
    contract: dict[str, Any],
) -> None:
    task = TaskFixture(
        "defect_correction",
        "characterization",
        "focused_reproduction_fails_for_reported_defect",
    )

    assert _diagnose(task, contract) == [
        "defect_correction requires regression_tdd, got characterization"
    ]


def test_waiver_requires_all_compensating_fields(contract: dict[str, Any]) -> None:
    task = TaskFixture(
        "manifest_config_generated_or_tooling",
        "static_validation",
        "native_parser_lint_type_or_build_baseline",
        waiver={"rationale": "tool unavailable"},
    )

    assert _diagnose(task, contract) == [
        "verification waiver missing: approver, compensating_evidence"
    ]


def test_integration_gap_routes_through_revise(contract: dict[str, Any]) -> None:
    task = TaskFixture(
        "composition_of_existing_contracts",
        "integration_acceptance",
        "focused_integration_baseline_passes",
        discovered_implementation_gap=True,
    )

    assert _diagnose(task, contract) == [
        "integration acceptance implementation gap requires revise"
    ]


def test_low_signal_policy_distinguishes_operational_structure(
    contract: dict[str, Any],
) -> None:
    policy = contract["low_signal_tests"]

    assert "private_implementation_shape" in policy["reject"]
    assert "source_scanner_when_native_gate_exists" in policy["reject"]
    assert "operationally_meaningful_structure" in policy["retain"]
