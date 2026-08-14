"""Behavior tests for the canonical Flow command and interaction contract."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tomllib
from typing import Any

import pytest
import yaml

from tools.flow_contract import (
    ContractError,
    load_contract,
    normalize_result,
    parse_request,
    select_transport,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "flow.yaml"


def _load_script(name: str):
    path = REPO_ROOT / "tools" / name
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py").replace("-", "_"), path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def contract():
    return load_contract(CONTRACT_PATH)


def _choice(choice_id: str) -> dict[str, str]:
    return {
        "id": choice_id,
        "label": choice_id.replace("_", " ").title(),
        "description": f"Use {choice_id} for this repository decision.",
    }


def _request(
    mode: str, choice_ids: tuple[str, ...] = ("approve", "revise"), **changes: Any
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "contract_id": "structured-choice-v1",
        "decision_id": "draft_gate",
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
    elif mode == "open":
        request.update(
            choices=[],
            recommended_choice_id=None,
            allow_custom=False,
            free_form_reason="revision_details",
            input_guidance="Describe the exact requested edits.",
        )
    request.update(changes)
    return request


def _result(request: dict[str, Any], outcome: str, **changes: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "decision_id": request["decision_id"],
        "selection_mode": request["selection_mode"],
        "outcome": outcome,
        "selected_choice_ids": [],
        "custom_text": None,
        "open_text": None,
        "transport": "native",
        "tool_name": "AskUserQuestion",
        "fallback_reasons": [],
    }
    result.update(changes)
    return result


def test_contract_has_exact_namespaces(contract) -> None:
    assert contract.schema_version == 1
    assert contract.git_policy.tags == "forbidden"
    assert contract.git_policy.allowed_local_operations == (
        "notes",
        "branches",
        "worktrees",
    )
    assert tuple(contract.harnesses) == (
        "antigravity",
        "claude_code",
        "codex_cli",
        "opencode",
        "cursor",
        "vscode_copilot",
        "openclaw",
    )
    assert tuple(contract.commands) == tuple(
        f"flow/{name}"
        for name in (
            "setup prd plan refine sync research docs implement status revert validate revise archive refresh task finish review cleanup"
        ).split()
    )
    assert contract.state_operations == (
        "create",
        "activate",
        "claim",
        "release",
        "note",
        "discover",
        "block",
        "unblock",
        "checkpoint",
        "close",
        "skip",
        "reopen",
        "revise",
        "reconcile",
        "complete",
        "archive",
        "recover",
        "status",
    )
    assert (
        contract.interaction.procedure_source == "skills/flow/references/interaction.md"
    )
    assert contract.interaction.planning_gates == {
        "pre_quality": ("revise", "refine"),
        "post_quality": ("approve", "revise", "refine"),
    }
    assert contract.interaction.transition_effects["revise"] == (
        "collect_open_revision_details",
        "apply_changes",
        "increment_plan_identity_if_plan_bearing",
        "revalidate",
        "represent_gate",
    )


@pytest.mark.parametrize(
    ("mode", "choice_ids"),
    [
        ("binary", ("approve", "revise")),
        ("single_select", ("approve", "revise", "refine")),
        ("multi_select", ("source", "tests", "docs", "ci")),
        ("open", ()),
    ],
)
def test_all_request_variants_parse(
    contract, mode: str, choice_ids: tuple[str, ...]
) -> None:
    assert parse_request(contract, _request(mode, choice_ids)).selection_mode == mode


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra=True),
        lambda value: value.pop("question"),
        lambda value: value["choices"][0].update(reason="alias"),
        lambda value: value["choices"][0].pop("description"),
        lambda value: value.update(recommended_choice_id="revise"),
        lambda value: value["choices"].append(deepcopy(value["choices"][0])),
        lambda value: value["choices"][0].update(id="Not-valid"),
        lambda value: value["choices"][0].update(label="Approve (Recommended)"),
        lambda value: value.update(allow_custom=False),
        lambda value: value.update(min_selections=1),
    ],
)
def test_request_schema_rejects_unknown_missing_alias_and_variant_errors(
    contract, mutation
) -> None:
    request = _request("single_select")
    mutation(request)
    with pytest.raises(ContractError):
        parse_request(contract, request)


def test_open_request_is_strict(contract) -> None:
    for changes in (
        {"choices": [_choice("approve")]},
        {"recommended_choice_id": "approve"},
        {"allow_custom": True},
        {"min_selections": 0},
        {"free_form_reason": "approval"},
        {"input_guidance": "   "},
    ):
        with pytest.raises(ContractError):
            parse_request(contract, _request("open", (), **changes))


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(0, 1), (2, 1), (1, 5), (True, 2), (1, None)],
)
def test_multi_request_bounds_are_validated(
    contract, minimum: Any, maximum: Any
) -> None:
    with pytest.raises(ContractError):
        parse_request(
            contract,
            _request(
                "multi_select",
                ("a", "b", "c", "d"),
                min_selections=minimum,
                max_selections=maximum,
            ),
        )


def test_transport_capability_mappings(contract) -> None:
    request = parse_request(contract, _request("multi_select", ("a", "b", "c", "d")))
    for harness_id, tool in (
        ("antigravity", "ask_question"),
        ("claude_code", "AskUserQuestion"),
        ("opencode", "question"),
    ):
        decision = select_transport(
            contract, harness_id, request, tool_available=True, tool_allowed=True
        )
        assert decision.transport == "native"
        assert decision.tool_name == tool
        assert decision.fallback_reasons == ()

    codex = select_transport(
        contract, "codex_cli", request, tool_available=True, tool_allowed=True
    )
    assert codex.transport == "sequential_text"
    assert codex.fallback_reasons == (
        "mode_unsupported",
        "choice_count_unsupported",
        "bounds_unsupported",
    )


@pytest.mark.parametrize("harness_id", ["cursor", "vscode_copilot", "openclaw"])
def test_null_tool_hosts_use_absent_fallback(contract, harness_id: str) -> None:
    decision = select_transport(
        contract,
        harness_id,
        parse_request(contract, _request("binary")),
        tool_available=False,
        tool_allowed=False,
    )
    assert decision.tool_name is None
    assert decision.fallback_reasons == ("tool_absent",)


def test_absent_and_denied_short_circuit(contract) -> None:
    request = parse_request(contract, _request("multi_select", ("a", "b", "c", "d")))
    absent = select_transport(
        contract, "codex_cli", request, tool_available=False, tool_allowed=True
    )
    denied = select_transport(
        contract, "codex_cli", request, tool_available=True, tool_allowed=False
    )
    assert absent.fallback_reasons == ("tool_absent",)
    assert denied.fallback_reasons == ("tool_denied",)


@pytest.mark.parametrize("choice_count", [2, 3])
def test_codex_binary_and_single_native_boundaries(contract, choice_count: int) -> None:
    mode = "binary" if choice_count == 2 else "single_select"
    request = parse_request(
        contract, _request(mode, tuple(f"c{i}" for i in range(choice_count)))
    )
    assert (
        select_transport(
            contract, "codex_cli", request, tool_available=True, tool_allowed=True
        ).transport
        == "native"
    )


@pytest.mark.parametrize(
    ("mode", "outcome", "changes"),
    [
        ("binary", "selected", {"selected_choice_ids": ["approve"]}),
        ("binary", "custom", {"custom_text": "Use a different gate"}),
        ("single_select", "custom", {"custom_text": "Use a fourth option"}),
        ("single_select", "selected", {"selected_choice_ids": ["approve"]}),
        ("multi_select", "selected", {"selected_choice_ids": ["a", "b"]}),
        (
            "multi_select",
            "selected_with_custom",
            {"selected_choice_ids": ["a"], "custom_text": "also examples"},
        ),
        (
            "open",
            "submitted",
            {
                "open_text": "Rename it to release-train.",
                "transport": "sequential_text",
                "tool_name": None,
                "fallback_reasons": ["tool_absent"],
            },
        ),
        ("binary", "cancelled", {}),
        ("single_select", "cancelled", {}),
        ("multi_select", "cancelled", {}),
        (
            "open",
            "cancelled",
            {
                "transport": "sequential_text",
                "tool_name": None,
                "fallback_reasons": ["tool_absent"],
            },
        ),
    ],
)
def test_result_union_accepts_every_outcome(
    contract, mode: str, outcome: str, changes: dict[str, Any]
) -> None:
    choice_ids = ("a", "b", "c") if mode == "multi_select" else ("approve", "revise")
    request_data = _request(mode, choice_ids)
    request = parse_request(contract, request_data)
    result_data = _result(request_data, outcome, **changes)
    assert normalize_result(contract, request, result_data).outcome == outcome


def test_result_requires_exact_request_correlation_and_keys(contract) -> None:
    request_data = _request("single_select")
    request = parse_request(contract, request_data)
    valid = _result(request_data, "selected", selected_choice_ids=["approve"])
    mutations = (
        {**valid, "unexpected": True},
        {key: value for key, value in valid.items() if key != "open_text"},
        {**valid, "decision_id": "another"},
        {**valid, "selection_mode": "binary"},
        {**valid, "selected_choice_ids": ["unknown"]},
        {**valid, "selected_choice_ids": ["approve", "approve"]},
    )
    for result in mutations:
        with pytest.raises(ContractError):
            normalize_result(contract, request, result)


def test_result_transport_fallback_contract(contract) -> None:
    request_data = _request("single_select", ("one", "two", "three", "four"))
    request = parse_request(contract, request_data)
    base = _result(
        request_data,
        "selected",
        selected_choice_ids=["one"],
        transport="sequential_text",
        tool_name="request_user_input",
    )
    normalize_result(
        contract, request, {**base, "fallback_reasons": ["choice_count_unsupported"]}
    )
    for reasons in (
        [],
        ["choice_count_unsupported", "mode_unsupported"],
        ["mode_unsupported", "mode_unsupported"],
        ["tool_absent", "mode_unsupported"],
    ):
        with pytest.raises(ContractError):
            normalize_result(contract, request, {**base, "fallback_reasons": reasons})
    null_tool = {**base, "tool_name": None, "fallback_reasons": ["tool_absent"]}
    normalize_result(contract, request, null_tool)
    with pytest.raises(ContractError, match="unverified tool"):
        normalize_result(
            contract,
            request,
            {
                **base,
                "tool_name": "invented_question",
                "fallback_reasons": ["tool_denied"],
            },
        )


def test_multi_result_counts_custom_as_one(contract) -> None:
    request_data = _request(
        "multi_select",
        ("a", "b", "c", "d"),
        min_selections=2,
        max_selections=3,
    )
    request = parse_request(contract, request_data)
    valid = _result(
        request_data,
        "selected_with_custom",
        selected_choice_ids=["a", "b"],
        custom_text="docs",
    )
    normalize_result(contract, request, valid)
    for changes in (
        {"selected_choice_ids": [], "custom_text": "docs"},
        {"selected_choice_ids": ["a", "b", "c"], "custom_text": "docs"},
        {"selected_choice_ids": ["a"], "custom_text": "  "},
    ):
        with pytest.raises(ContractError):
            normalize_result(
                contract,
                request,
                _result(request_data, "selected_with_custom", **changes),
            )


@pytest.mark.parametrize(
    ("outcome", "selected", "custom_text", "valid"),
    [
        ("selected", (), None, False),
        ("selected", ("a",), None, True),
        ("selected", ("a", "b", "c", "d"), None, True),
        ("selected_with_custom", (), "other", True),
        ("selected_with_custom", ("a", "b", "c"), "other", True),
        ("selected_with_custom", ("a", "b", "c", "d"), "other", False),
    ],
)
def test_multi_result_all_boundary_counts(
    contract,
    outcome: str,
    selected: tuple[str, ...],
    custom_text: str | None,
    valid: bool,
) -> None:
    request_data = _request(
        "multi_select", ("a", "b", "c", "d"), min_selections=1, max_selections=4
    )
    request = parse_request(contract, request_data)
    result = _result(
        request_data,
        outcome,
        selected_choice_ids=list(selected),
        custom_text=custom_text,
    )
    if valid:
        normalize_result(contract, request, result)
    else:
        with pytest.raises(ContractError):
            normalize_result(contract, request, result)


def test_contract_loader_rejects_alias_unknown_version_and_duplicate_ids(
    tmp_path: Path,
) -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    mutations = []
    wrong_version = deepcopy(data)
    wrong_version["schema_version"] = 2
    mutations.append(wrong_version)
    unknown = deepcopy(data)
    unknown["unknown"] = True
    mutations.append(unknown)
    duplicate = deepcopy(data)
    duplicate["commands"].append(deepcopy(duplicate["commands"][0]))
    mutations.append(duplicate)
    for index, bad in enumerate(mutations):
        path = tmp_path / f"bad-{index}.yaml"
        path.write_text(yaml.safe_dump(bad, sort_keys=False), encoding="utf-8")
        with pytest.raises(ContractError):
            load_contract(path)

    alias_path = tmp_path / "alias.yaml"
    alias_path.write_text(
        "schema_version: 1\nstate_operations: &ops []\ncommands: *ops\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="aliases"):
        load_contract(alias_path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["git_policy"].update(tags="allowed"),
        lambda data: data["harnesses"][-1].update(supported_modes=["binary"]),
        lambda data: data["harnesses"][-1].update(plan_capability="native"),
        lambda data: data["harnesses"][2].update(command_surface="slash_command"),
        lambda data: data["commands"][0].update(state_operations=["tag"]),
        lambda data: data["commands"][0].update(runtime_dependency="python"),
        lambda data: data["commands"][0].update(mutability="read_only"),
        lambda data: data["commands"][0]["invocations"]["cursor"].update(
            spelling="/flow-setup"
        ),
        lambda data: data["commands"][0].update(question_capability=None),
        lambda data: data["agents"][-1].update(invariant_ids=["flow-state-v1"]),
    ],
)
def test_contract_rejects_impossible_cross_record_claims(
    tmp_path: Path, mutate
) -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ContractError):
        load_contract(path)


def test_command_generator_is_deterministic_and_check_is_non_destructive(
    tmp_path: Path,
) -> None:
    generator = _load_script("sync-command-surfaces.py")

    first = generator.write_surfaces(CONTRACT_PATH, tmp_path)
    snapshot = {path: path.read_bytes() for path in first}
    second = generator.write_surfaces(CONTRACT_PATH, tmp_path)
    assert first == second
    assert snapshot == {path: path.read_bytes() for path in second}
    assert all(b"generated-sha256:" in payload for payload in snapshot.values())
    plan_toml = tomllib.loads(
        (tmp_path / "commands/flow/plan.toml").read_text(encoding="utf-8")
    )
    plan_record = json.loads(plan_toml["prompt"])
    assert plan_record["canonical_id"] == "flow/plan"
    assert plan_record["procedure_source"] == "skills/flow/references/plan.md"
    assert plan_record["question_tool"] == "request_user_input"
    assert plan_record["git_tags"] == "forbidden"
    assert generator.check_surfaces(CONTRACT_PATH, tmp_path) == []
    victim = first[0]
    victim.write_text("user-owned\n", encoding="utf-8")
    assert generator.check_surfaces(CONTRACT_PATH, tmp_path) == [
        f"stale command output: {victim.relative_to(tmp_path)}"
    ]
    assert victim.read_text(encoding="utf-8") == "user-owned\n"
