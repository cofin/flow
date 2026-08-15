from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _marked_contract(relative_path: str, marker: str) -> dict[str, object]:
    text = _read(relative_path)
    match = re.search(
        rf"<!-- {re.escape(marker)}: start -->\s*```yaml\n(.*?)\n```\s*"
        rf"<!-- {re.escape(marker)}: end -->",
        text,
        re.DOTALL,
    )
    assert match is not None, f"{relative_path} has no {marker} block"
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict)
    return loaded


def _flow_contract() -> dict[str, object]:
    loaded = yaml.safe_load(_read("contracts/flow.yaml"))
    assert isinstance(loaded, dict)
    return loaded


def test_implement_invariant_ids_match_the_canonical_agent_contract() -> None:
    contract = _flow_contract()
    commands = contract["commands"]
    agents = contract["agents"]
    assert isinstance(commands, list)
    assert isinstance(agents, list)
    command = next(item for item in commands if item["id"] == "flow/implement")
    agent = next(item for item in agents if item["id"] == "executor")

    assert command["lifecycle_owner"] == "flow-execution"
    assert command["procedure_source"] == "skills/flow/references/implement.md"
    assert command["shared_contracts"] == [
        "flow-state-v1",
        "worksheet-execution-v1",
    ]
    assert agent["invariant_ids"] == [
        "worksheet-execution-v1",
        "flow-state-v1",
        "git-no-tags-v1",
    ]


def test_implement_policy_summary_matches_its_authority() -> None:
    summary = _marked_contract(
        "skills/flow-execution/SKILL.md", "flow-execution-policy"
    )
    agent = _marked_contract("agents/executor.md", "flow-execution-policy")
    authority = _marked_contract(
        "skills/flow/references/implement.md", "flow-execution-policy"
    )

    assert summary == agent == authority
    assert summary["authority"] == "skills/flow/references/implement.md"
    assert summary["invariants"] == [
        "worksheet-first",
        "fail-closed-no-production-mutation",
        "fresh-validated-plan-resume",
    ]


def test_implement_mismatch_routes_are_total_and_traceable() -> None:
    contract = _marked_contract(
        "skills/flow/references/implement.md", "flow-execution-contract"
    )
    mismatch_classes = contract["mismatch_classes"]
    routes = contract["mismatch_routes"]
    assert isinstance(mismatch_classes, list)
    assert isinstance(routes, dict)

    assert set(routes) == set(mismatch_classes)
    for mismatch_class in mismatch_classes:
        route = routes[mismatch_class]
        assert route["transition"] == "mismatch-discover-block"
        assert route["task_operation"] == "block"
        assert route["handoff"] in {"revise", "refine"}
        assert route["unblock_condition"]
        assert route["next_exact_planning_action"]
    assert contract["transitions"]["mismatch-discover-block"] == {
        "operations": ["discover", "block"],
        "production_mutations": [],
    }
