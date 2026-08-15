"""Parsed planning-contract and test-only transition oracle tests."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_PATHS = (
    REPO_ROOT / "agents" / "plan-generator.md",
    REPO_ROOT / "agents" / "prd-orchestrator.md",
)
PROCEDURE_PATHS = (
    REPO_ROOT / "skills" / "flow-planning" / "SKILL.md",
    REPO_ROOT / "skills" / "flow" / "references" / "prd.md",
    REPO_ROOT / "skills" / "flow" / "references" / "plan.md",
    REPO_ROOT / "skills" / "flow" / "references" / "refine.md",
)
INTERACTION_PATH = REPO_ROOT / "skills" / "flow" / "references" / "interaction.md"
CONTRACT_PATTERN = re.compile(
    r"<!-- planning-contract: structured-choice-v1 -->\s*```yaml\s*(.*?)```",
    re.DOTALL,
)


def _parsed_contract(path: Path) -> dict[str, Any]:
    match = CONTRACT_PATTERN.search(path.read_text(encoding="utf-8"))
    assert match is not None, f"missing parsed planning contract in {path}"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def _choice(choice_id: str) -> dict[str, str]:
    return {
        "id": choice_id,
        "label": choice_id.replace("_", " ").title(),
        "description": f"Use the {choice_id} outcome for this decision.",
    }


def _request(
    mode: str,
    *,
    decision_id: str = "draft_gate",
    choice_ids: tuple[str, ...] = ("approve", "revise"),
    **overrides: Any,
) -> dict[str, Any]:
    request = {
        "contract_id": "structured-choice-v1",
        "decision_id": decision_id,
        "selection_mode": mode,
        "question": "Choose the next planning action.",
        "disabled_choice_policy": "omit",
        "choices": [_choice(choice_id) for choice_id in choice_ids],
        "recommended_choice_id": choice_ids[0] if choice_ids else None,
        "allow_custom": mode != "open",
        "min_selections": None,
        "max_selections": None,
        "free_form_reason": None,
        "input_guidance": None,
    }
    if mode == "multi_select":
        request.update(min_selections=1, max_selections=len(choice_ids))
    if mode == "open":
        request.update(
            choices=[],
            recommended_choice_id=None,
            allow_custom=False,
            free_form_reason="revision_details",
            input_guidance="Describe the exact changes requested.",
        )
    request.update(overrides)
    return request


def _validate_request(
    contract: dict[str, Any], request: dict[str, Any]
) -> dict[str, Any]:
    request_contract = contract["request"]
    assert set(request) == set(request_contract["exact_keys"])
    assert request["contract_id"] == contract["contract_id"]
    assert request["selection_mode"] in request_contract["variants"]
    assert request["decision_id"]
    assert request["question"]
    assert request["disabled_choice_policy"] == "omit"

    mode = request["selection_mode"]
    variant = request_contract["variants"][mode]
    choices = request["choices"]
    assert isinstance(choices, list)
    assert variant["choice_count"][0] <= len(choices) <= variant["choice_count"][1]
    ids: list[str] = []
    for choice in choices:
        assert set(choice) == set(request_contract["exact_choice_keys"])
        assert re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", choice["id"])
        assert 1 <= len(choice["label"]) <= 60
        assert "(Recommended)" not in choice["label"]
        assert 1 <= len(choice["description"]) <= 160
        ids.append(choice["id"])
    assert len(ids) == len(set(ids))

    if mode == "open":
        assert request["recommended_choice_id"] is None
        assert request["allow_custom"] is False
        assert request["min_selections"] is None
        assert request["max_selections"] is None
        assert request["free_form_reason"] in variant["free_form_reasons"]
        assert request["input_guidance"] and request["input_guidance"].strip()
    else:
        assert request["recommended_choice_id"] == ids[0]
        assert request["allow_custom"] is True
        assert request["free_form_reason"] is None
        assert request["input_guidance"] is None
        if mode == "multi_select":
            minimum = request["min_selections"]
            maximum = request["max_selections"]
            assert isinstance(minimum, int) and not isinstance(minimum, bool)
            assert isinstance(maximum, int) and not isinstance(maximum, bool)
            assert 1 <= minimum <= maximum <= len(ids)
        else:
            assert request["min_selections"] is None
            assert request["max_selections"] is None
    return request


def _result(
    request: dict[str, Any],
    outcome: str,
    *,
    selected: tuple[str, ...] = (),
    custom_text: str | None = None,
    open_text: str | None = None,
    transport: str = "native",
    tool_name: str | None = "AskUserQuestion",
    fallback_reasons: tuple[str, ...] = (),
    **overrides: Any,
) -> dict[str, Any]:
    result = {
        "decision_id": request["decision_id"],
        "selection_mode": request["selection_mode"],
        "outcome": outcome,
        "selected_choice_ids": list(selected),
        "custom_text": custom_text,
        "open_text": open_text,
        "transport": transport,
        "tool_name": tool_name,
        "fallback_reasons": list(fallback_reasons),
    }
    result.update(overrides)
    return result


def _normalize_result(
    contract: dict[str, Any], request: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    result_contract = contract["result"]
    assert set(result) == set(result_contract["exact_keys"])
    assert result["decision_id"] == request["decision_id"]
    assert result["selection_mode"] == request["selection_mode"]
    assert result["transport"] in {"native", "sequential_text"}
    selected = result["selected_choice_ids"]
    request_ids = [choice["id"] for choice in request["choices"]]
    assert len(selected) == len(set(selected))
    assert all(choice_id in request_ids for choice_id in selected)
    assert selected == [choice_id for choice_id in request_ids if choice_id in selected]

    reasons = result["fallback_reasons"]
    reason_order = result_contract["fallback_reason_order"]
    assert len(reasons) == len(set(reasons))
    assert reasons == [reason for reason in reason_order if reason in reasons]
    if result["transport"] == "native":
        assert reasons == [] and result["tool_name"]
    else:
        assert reasons

    mode = request["selection_mode"]
    outcome = result["outcome"]
    custom = result["custom_text"]
    opened = result["open_text"]
    if outcome == "cancelled":
        assert selected == [] and custom is None and opened is None
    elif mode == "open":
        assert outcome == "submitted"
        assert selected == [] and custom is None
        assert opened is not None and opened.strip()
    elif mode in {"binary", "single_select"}:
        assert outcome in {"selected", "custom"}
        if outcome == "selected":
            assert len(selected) == 1 and custom is None and opened is None
        else:
            assert selected == [] and custom is not None and custom.strip()
            assert opened is None
    else:
        assert outcome in {"selected", "selected_with_custom"}
        if outcome == "selected":
            assert custom is None and opened is None
            total = len(selected)
        else:
            assert custom is not None and custom.strip() and opened is None
            total = len(selected) + 1
        assert request["min_selections"] <= total <= request["max_selections"]
    return {
        **result,
        "custom_text": custom.strip() if isinstance(custom, str) else custom,
        "open_text": opened.strip() if isinstance(opened, str) else opened,
    }


def _plan_fixture(*, complete: bool = True) -> dict[str, Any]:
    return {
        "research_closed": complete,
        "requirements": ["R1", "R2"],
        "requirement_tasks": {"R1": ["1.1"], "R2": ["1.2"]}
        if complete
        else {"R1": ["1.1"]},
        "tasks": [
            {
                "id": "1.1",
                "worksheet_sections": [
                    "Objective",
                    "Context",
                    "Steps",
                    "Verification",
                    "Acceptance Criteria",
                ],
                "verification_strategy": "behavior_tdd",
                "verification": "uv run pytest tests/test_feature.py -q; expected passing",
                "files": ["src/feature.py"],
                "one_invocation": True,
                "one_commit": True,
            },
            {
                "id": "1.2",
                "worksheet_sections": [
                    "Objective",
                    "Context",
                    "Steps",
                    "Verification",
                    "Acceptance Criteria",
                ],
                "verification_strategy": "static_validation",
                "verification": "uv run python tools/validate.py; expected exit 0",
                "files": ["docs/feature.md"],
                "one_invocation": True,
                "one_commit": True,
            },
        ],
        "unresolved_decisions": [],
        "deferred_research": [],
        "review_round": 0,
        "plan_revision": 4,
        "plan_commit": "abc1234",
        "phase": "research_closed",
    }


def _gap_scan(plan: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not plan["research_closed"] or plan["deferred_research"]:
        gaps.append("deferred_research")
    if plan["unresolved_decisions"]:
        gaps.append("unresolved_decisions")
    if set(plan["requirement_tasks"]) != set(plan["requirements"]):
        gaps.append("requirement_traceability")
    required_sections = {
        "Objective",
        "Context",
        "Steps",
        "Verification",
        "Acceptance Criteria",
    }
    seen_files: set[str] = set()
    for task in plan["tasks"]:
        if set(task["worksheet_sections"]) != required_sections:
            gaps.append("stub_body")
        if not task["verification_strategy"]:
            gaps.append("missing_verification_strategy")
        if "expected" not in task["verification"]:
            gaps.append("vague_verification")
        if seen_files.intersection(task["files"]):
            gaps.append("overlapping_ownership")
        seen_files.update(task["files"])
        if not task["one_invocation"] or not task["one_commit"]:
            gaps.append("oversized_task")
    return list(dict.fromkeys(gaps))


def _advance(
    declaration: dict[str, Any],
    plan: dict[str, Any],
    event: str,
    *,
    findings: tuple[str, ...] = (),
) -> tuple[str, list[str]]:
    phases = declaration["planning_loop"]["phases"]
    current = plan["phase"]
    if event == "advance":
        plan["phase"] = phases[phases.index(current) + 1]
    elif current == "gap_scan" and event == "scan":
        gaps = _gap_scan(plan)
        plan["phase"] = "refine" if gaps else "revision_update"
        return plan["phase"], gaps
    elif current == "refine" and event in {"revise", "refine"}:
        plan["phase"] = "revision_update"
    elif current == "revision_update" and event == "plan_changed":
        plan["plan_revision"] += 1
        plan["plan_commit"] = None
        plan["phase"] = "review"
    elif current == "revision_update" and event == "unchanged":
        plan["phase"] = "review"
    elif current == "review" and event == "reviewed":
        plan["review_round"] += 1
        blocking = [
            finding for finding in findings if finding in {"Critical", "Important"}
        ]
        if not blocking:
            plan["phase"] = "approved"
        elif (
            plan["review_round"]
            >= declaration["planning_loop"]["review"]["max_external_rounds"]
        ):
            plan["phase"] = "blocked"
        else:
            plan["phase"] = "refine"
        return plan["phase"], blocking
    else:
        raise AssertionError(f"invalid transition: {current}/{event}")
    return plan["phase"], []


def test_all_planning_surfaces_declare_the_same_executable_loop() -> None:
    declarations = [_parsed_contract(path) for path in (*AGENT_PATHS, *PROCEDURE_PATHS)]
    loops = [declaration["planning_loop"] for declaration in declarations]
    assert all(loop == loops[0] for loop in loops)
    assert loops[0]["phases"] == [
        "research_closed",
        "draft",
        "gap_scan",
        "refine",
        "revision_update",
        "review",
        "approved",
        "revise",
        "blocked",
    ]
    assert loops[0]["review"] == {
        "max_external_rounds": 3,
        "blocking_severities": ["Critical", "Important"],
        "on_limit": "blocked",
    }


def test_interaction_is_the_declared_sole_choice_authority() -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    assert contract["contract_id"] == "structured-choice-v1"
    for path in (*AGENT_PATHS, *PROCEDURE_PATHS):
        declaration = _parsed_contract(path)
        assert (
            declaration["interaction_authority"]
            == "skills/flow/references/interaction.md"
        )


@pytest.mark.parametrize(
    ("mode", "choice_ids"),
    [
        ("binary", ("approve", "revise")),
        ("single_select", ("approve", "revise", "refine")),
        ("multi_select", ("api", "cli", "docs", "tests")),
        ("open", ()),
    ],
)
def test_each_tagged_request_variant_is_valid(
    mode: str, choice_ids: tuple[str, ...]
) -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    assert _validate_request(contract, _request(mode, choice_ids=choice_ids))


@pytest.mark.parametrize(
    "candidate",
    [
        _request("binary", choice_ids=("approve",)),
        _request("binary", choice_ids=("approve", "revise", "refine")),
        _request("single_select", choice_ids=("approve",)),
        _request("single_select", choice_ids=("a", "b", "c", "d", "e")),
        _request("multi_select", choice_ids=("a", "b"), min_selections=0),
        _request(
            "multi_select", choice_ids=("a", "b"), min_selections=2, max_selections=1
        ),
        _request("multi_select", choice_ids=("a", "b"), max_selections=3),
        _request("open", choice_ids=(), recommended_choice_id="approve"),
        _request("open", choice_ids=(), allow_custom=True),
        _request("open", choice_ids=(), free_form_reason="approval"),
        _request("open", choice_ids=(), input_guidance=" "),
    ],
)
def test_invalid_tagged_request_variants_are_rejected(
    candidate: dict[str, Any],
) -> None:
    with pytest.raises(AssertionError):
        _validate_request(_parsed_contract(INTERACTION_PATH), candidate)


@pytest.mark.parametrize("alias", ["choice_id", "reason", "impact", "unknown"])
def test_choice_aliases_and_unknown_keys_are_rejected(alias: str) -> None:
    request = _request("binary")
    request["choices"][0][alias] = request["choices"][0].pop("description")
    with pytest.raises(AssertionError):
        _validate_request(_parsed_contract(INTERACTION_PATH), request)


@pytest.mark.parametrize(
    "result",
    [
        lambda request: _result(request, "selected", selected=("approve",)),
        lambda request: _result(request, "custom", custom_text="Use a staged rollout"),
        lambda request: _result(request, "cancelled"),
    ],
)
def test_selected_custom_and_cancelled_results_are_normalized(result) -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request("binary")
    normalized = _normalize_result(contract, request, result(request))
    assert normalized["decision_id"] == "draft_gate"


def test_open_submission_is_normalized_and_trimmed() -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request("open", choice_ids=())
    normalized = _normalize_result(
        contract,
        request,
        _result(request, "submitted", open_text="  change the timeout  "),
    )
    assert normalized["open_text"] == "change the timeout"


@pytest.mark.parametrize(
    ("selected", "custom", "minimum", "maximum", "valid"),
    [
        ((), "other", 1, 2, True),
        ((), "   ", 1, 2, False),
        (("a", "b"), "other", 1, 2, False),
        ((), None, 2, 3, False),
        (("a", "b"), None, 2, 3, True),
        (("a", "b", "c"), None, 2, 3, True),
        (("a", "b", "c"), None, 1, 2, False),
    ],
)
def test_multi_cardinality_including_other(
    selected: tuple[str, ...],
    custom: str | None,
    minimum: int,
    maximum: int,
    valid: bool,
) -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request(
        "multi_select",
        choice_ids=("a", "b", "c"),
        min_selections=minimum,
        max_selections=maximum,
    )
    outcome = "selected_with_custom" if custom is not None else "selected"
    result = _result(request, outcome, selected=selected, custom_text=custom)
    if valid:
        assert _normalize_result(contract, request, result)
    else:
        with pytest.raises(AssertionError):
            _normalize_result(contract, request, result)


@pytest.mark.parametrize(
    "overrides",
    [
        {"decision_id": "another_decision"},
        {"selection_mode": "single_select"},
        {"selected_choice_ids": ["unknown"]},
        {"extra": "forbidden"},
    ],
)
def test_result_request_correlation_and_exact_keys(overrides: dict[str, Any]) -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request("binary")
    result = _result(request, "selected", selected=("approve",), **overrides)
    with pytest.raises(AssertionError):
        _normalize_result(contract, request, result)


def test_fallback_reasons_are_complete_ordered_and_transport_correlated() -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request("multi_select", choice_ids=("a", "b", "c", "d"))
    reasons = ("mode_unsupported", "choice_count_unsupported", "bounds_unsupported")
    result = _result(
        request,
        "selected",
        selected=("a",),
        transport="sequential_text",
        tool_name="request_user_input",
        fallback_reasons=reasons,
    )
    assert _normalize_result(contract, request, result)["fallback_reasons"] == list(
        reasons
    )
    bad = deepcopy(result)
    bad["fallback_reasons"] = list(reversed(reasons))
    with pytest.raises(AssertionError):
        _normalize_result(contract, request, bad)


def test_null_tool_fallback_uses_only_tool_absent() -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    request = _request("binary")
    result = _result(
        request,
        "selected",
        selected=("approve",),
        transport="sequential_text",
        tool_name=None,
        fallback_reasons=("tool_absent",),
    )
    assert _normalize_result(contract, request, result)


def test_complete_plan_trace_reaches_approval() -> None:
    declaration = _parsed_contract(AGENT_PATHS[0])
    plan = _plan_fixture()
    for expected in ("draft", "gap_scan"):
        assert _advance(declaration, plan, "advance")[0] == expected
    assert _advance(declaration, plan, "scan") == ("revision_update", [])
    assert _advance(declaration, plan, "unchanged")[0] == "review"
    assert _advance(declaration, plan, "reviewed") == ("approved", [])


def test_vague_plan_trace_refines_and_updates_plan_identity() -> None:
    declaration = _parsed_contract(AGENT_PATHS[0])
    plan = _plan_fixture(complete=False)
    plan["tasks"][0]["verification"] = "test it"
    plan["tasks"][1]["files"] = ["src/feature.py"]
    plan["tasks"][1]["one_commit"] = False
    _advance(declaration, plan, "advance")
    _advance(declaration, plan, "advance")
    phase, gaps = _advance(declaration, plan, "scan")
    assert phase == "refine"
    assert gaps == [
        "deferred_research",
        "requirement_traceability",
        "vague_verification",
        "overlapping_ownership",
        "oversized_task",
    ]
    assert _advance(declaration, plan, "refine")[0] == "revision_update"
    assert _advance(declaration, plan, "plan_changed")[0] == "review"
    assert plan["plan_revision"] == 5 and plan["plan_commit"] is None


def test_three_unresolved_reviews_hard_block_ready() -> None:
    declaration = _parsed_contract(AGENT_PATHS[0])
    plan = _plan_fixture()
    plan["phase"] = "review"
    for round_number in (1, 2):
        assert (
            _advance(declaration, plan, "reviewed", findings=("Important",))[0]
            == "refine"
        )
        assert plan["review_round"] == round_number
        plan["phase"] = "review"
    phase, findings = _advance(declaration, plan, "reviewed", findings=("Critical",))
    assert phase == "blocked"
    assert findings == ["Critical"]


def test_draft_gate_sets_and_recommendation_reordering() -> None:
    interaction = _parsed_contract(INTERACTION_PATH)
    gate = interaction["draft_gate"]
    assert gate["before_quality"] == ["revise", "refine"]
    assert gate["after_quality"] == ["approve", "revise", "refine"]
    active = deepcopy(gate["after_quality"])
    active.remove("refine")
    active.insert(0, "refine")
    request = _request("single_select", choice_ids=tuple(active))
    assert _validate_request(interaction, request)["recommended_choice_id"] == "refine"


@pytest.mark.parametrize("action", ["revise", "refine"])
def test_revise_and_refine_loop_back_through_validation(action: str) -> None:
    declaration = _parsed_contract(AGENT_PATHS[0])
    plan = _plan_fixture()
    plan["phase"] = "refine"
    assert _advance(declaration, plan, action)[0] == "revision_update"
    assert _advance(declaration, plan, "plan_changed")[0] == "review"


def test_open_is_allowed_for_revision_details_but_not_enumerable_approval() -> None:
    contract = _parsed_contract(INTERACTION_PATH)
    revision = _request("open", choice_ids=(), free_form_reason="revision_details")
    assert _validate_request(contract, revision)
    approval = _request("open", choice_ids=(), free_form_reason="approval")
    with pytest.raises(AssertionError):
        _validate_request(contract, approval)


def test_installed_workflows_never_reference_a_runtime_evaluator() -> None:
    for path in (*AGENT_PATHS, *PROCEDURE_PATHS, INTERACTION_PATH):
        text = path.read_text(encoding="utf-8")
        assert "tools/planning_contract.py" not in text
        assert "import planning_contract" not in text
    assert not (REPO_ROOT / "tools" / "planning_contract.py").exists()
