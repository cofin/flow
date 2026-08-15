from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _execution_contract() -> dict[str, object]:
    text = (REPO_ROOT / "skills/flow/references/implement.md").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"<!-- flow-execution-contract: start -->\s*```yaml\n(.*?)\n```\s*"
        r"<!-- flow-execution-contract: end -->",
        text,
        re.DOTALL,
    )
    assert match is not None
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize(
    ("scenario", "expected_operations"),
    [
        ("preflight-claim", ["claim"]),
        ("mismatch-discover-block", ["discover", "block"]),
        ("nonblocking-discover-release", ["discover", "release"]),
        ("revised-plan-resume", ["claim"]),
    ],
)
def test_execution_state_scenarios_use_declared_markdown_operations(
    scenario: str, expected_operations: list[str]
) -> None:
    contract = _execution_contract()

    assert contract["transitions"][scenario]["operations"] == expected_operations


def test_execution_mismatch_and_resume_scenarios_fail_closed() -> None:
    contract = _execution_contract()

    assert contract["preflight"]["failure_transition"] == "mismatch-discover-block"
    assert (
        contract["transitions"]["mismatch-discover-block"]["production_mutations"] == []
    )
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
