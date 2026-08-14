from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "skills" / "flow" / "references" / "implement.md"
POLICY_PATHS = (
    REPO_ROOT / "agents" / "executor.md",
    REPO_ROOT / "skills" / "flow-execution" / "SKILL.md",
    CONTRACT_PATH,
    REPO_ROOT / "skills" / "flow" / "references" / "revise.md",
)
INSTALLED_EXECUTION_FILES = tuple((REPO_ROOT / "agents").rglob("*.md")) + tuple(
    (REPO_ROOT / "skills").rglob("*.md")
)

INVARIANT_IDS = {
    "worksheet-first",
    "fail-closed-no-production-mutation",
    "fresh-validated-plan-resume",
}
TRANSITION_IDS = {
    "preflight-claim",
    "mismatch-discover-block",
    "nonblocking-discover-release",
    "revised-plan-resume",
}


def _marked_yaml(path: Path, name: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"<!-- {re.escape(name)}: start -->\s*```yaml\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(name)}: end -->",
        re.DOTALL,
    )
    match = pattern.search(content)
    assert match is not None, f"missing {name} block in {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


@dataclass(frozen=True)
class TraceResult:
    operations: tuple[str, ...]
    handoff: str
    unblock_condition: str
    next_exact_planning_action: str
    production_mutations: tuple[str, ...]


def _trace_mismatch(contract: dict[str, Any], mismatch: str) -> TraceResult:
    route = contract["mismatch_routes"][mismatch]
    transition = contract["transitions"][route["transition"]]
    assert transition["operations"][-1] == route["task_operation"]
    return TraceResult(
        operations=tuple(transition["operations"]),
        handoff=route["handoff"],
        unblock_condition=route["unblock_condition"],
        next_exact_planning_action=route["next_exact_planning_action"],
        production_mutations=tuple(transition["production_mutations"]),
    )


def test_execution_policy_ids_are_declared_by_every_canonical_workflow() -> None:
    for path in POLICY_PATHS:
        policy = _marked_yaml(path, "flow-execution-policy")
        assert policy["contract"] == "worksheet-execution-v1"
        assert set(policy["invariants"]) == INVARIANT_IDS
        assert set(policy["transitions"]) == TRANSITION_IDS
        assert policy["authority"] == "skills/flow/references/implement.md"


def test_preflight_and_mismatch_report_are_closed() -> None:
    contract = _marked_yaml(CONTRACT_PATH, "flow-execution-contract")

    assert contract["preflight"]["checks"] == [
        "dependencies_closed",
        "worksheet_complete",
        "verification_strategy_declared",
        "plan_identity_matches",
        "state_revision_matches",
    ]
    assert contract["preflight"]["before_operation"] == "claim"
    assert contract["preflight"]["failure_transition"] == ("mismatch-discover-block")
    assert set(contract["mismatch_routes"]) == {
        "code_drift",
        "missing_decision",
        "invalid_file_symbol_or_test_target",
        "acceptance_contradiction",
        "scope_expansion",
        "invalid_verification_command",
    }
    assert contract["mismatch_report"]["required"] == [
        "mismatch_class",
        "evidence",
        "impact",
        "task_operation",
        "unblock_condition",
        "next_exact_planning_action",
    ]
    assert contract["mismatch_report"]["unknown_fields"] == "refuse"


@pytest.mark.parametrize(
    ("scenario", "mismatch", "expected"),
    [
        (
            "missing target symbol",
            "invalid_file_symbol_or_test_target",
            TraceResult(
                operations=("discover", "block"),
                handoff="revise",
                unblock_condition="target_corrected_in_new_validated_plan",
                next_exact_planning_action="revise_then_refine_and_validate",
                production_mutations=(),
            ),
        ),
        (
            "stale verification command",
            "invalid_verification_command",
            TraceResult(
                operations=("discover", "block"),
                handoff="revise",
                unblock_condition="verification_corrected_in_new_validated_plan",
                next_exact_planning_action="revise_then_refine_and_validate",
                production_mutations=(),
            ),
        ),
    ],
)
def test_mismatch_trace_stops_before_source_mutation(
    scenario: str,
    mismatch: str,
    expected: TraceResult,
) -> None:
    contract = _marked_yaml(CONTRACT_PATH, "flow-execution-contract")

    result = _trace_mismatch(contract, mismatch)

    assert scenario
    assert result == expected
    assert result.production_mutations == ()


def test_resume_requires_reloaded_fresh_validated_plan_identity() -> None:
    contract = _marked_yaml(CONTRACT_PATH, "flow-execution-contract")

    assert contract["resume"] == {
        "transition": "revised-plan-resume",
        "requires": [
            "plan_identity_changed",
            "plan_validation_passed",
            "tracked_markdown_reloaded",
            "preflight_repeated",
        ],
        "otherwise": "stop_without_production_mutation",
    }


def test_installed_workflows_do_not_reference_the_test_oracle() -> None:
    forbidden = ("test_execution_contract", "_trace_mismatch", "TraceResult")
    violations = {
        str(path.relative_to(REPO_ROOT)): token
        for path in INSTALLED_EXECUTION_FILES
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    }
    assert not violations
    assert not (REPO_ROOT / "tools" / "execution_contract.py").exists()
