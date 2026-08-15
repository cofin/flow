"""Semantic parity tests for generated Flow command and agent adapters."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tomllib
from types import ModuleType
from typing import Any

import pytest

from tools.flow_contract import (
    ContractError,
    FlowContract,
    load_contract,
    normalize_result,
    parse_request,
    select_transport,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "flow.yaml"
GENERATED_HASH = re.compile(r"(?<=generated-sha256: )[0-9a-f]{64}")


def _load_generator(filename: str) -> ModuleType:
    path = REPO_ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def contract() -> FlowContract:
    return load_contract(CONTRACT_PATH)


@pytest.fixture(scope="module")
def command_generator() -> ModuleType:
    return _load_generator("sync-command-surfaces.py")


@pytest.fixture(scope="module")
def agent_generator() -> ModuleType:
    return _load_generator("sync-agent-surfaces.py")


def _generated_record(relative: str, content: str) -> dict[str, Any]:
    if relative.startswith("commands/flow/"):
        return json.loads(tomllib.loads(content)["prompt"])
    if relative.startswith(".codex/agents/"):
        return json.loads(tomllib.loads(content)["developer_instructions"])
    fenced = content.split("```json\n", 1)[1].split("\n```", 1)[0]
    return json.loads(fenced)


def _choice(choice_id: str) -> dict[str, str]:
    return {
        "id": choice_id,
        "label": choice_id.replace("_", " ").title(),
        "description": f"Use {choice_id} for this decision.",
    }


def _request(
    mode: str,
    choice_ids: tuple[str, ...] = ("approve", "revise"),
    **changes: Any,
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


def test_checked_in_surfaces_equal_generator_output(
    command_generator: ModuleType, agent_generator: ModuleType
) -> None:
    expected = {
        **command_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT),
        **agent_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT),
    }
    assert expected
    assert set(expected) == {
        path.relative_to(REPO_ROOT).as_posix()
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and path.relative_to(REPO_ROOT).as_posix() in expected
    }
    for relative, rendered in expected.items():
        assert (REPO_ROOT / relative).read_text(encoding="utf-8") == rendered


def test_generated_hashes_cover_only_generated_adapters(
    command_generator: ModuleType, agent_generator: ModuleType
) -> None:
    generated = {
        **command_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT),
        **agent_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT),
    }
    for relative, content in generated.items():
        matches = GENERATED_HASH.findall(content)
        assert len(matches) == 1, relative
        unstamped = GENERATED_HASH.sub("", content)
        assert matches[0] == hashlib.sha256(unstamped.encode()).hexdigest(), relative

    for path in (REPO_ROOT / "agents").glob("*.md"):
        assert "generated-sha256:" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("command_id", "argument_schema"),
    [
        (
            "flow/setup",
            {"syntax": "[goal]", "required": [], "optional": ["goal"]},
        ),
        (
            "flow/sync",
            {"syntax": "[flow_id]", "required": [], "optional": ["flow_id"]},
        ),
        (
            "flow/task",
            {"syntax": "<exploration>", "required": ["exploration"], "optional": []},
        ),
    ],
)
@pytest.mark.parametrize(
    ("host", "relative_pattern", "tool", "choice_max"),
    [
        ("claude_code", "commands/flow-{name}.md", "AskUserQuestion", 4),
        ("codex_cli", "commands/flow/{name}.toml", "request_user_input", 3),
        ("opencode", "templates/opencode/commands/flow-{name}.md", "question", 4),
    ],
)
def test_representative_command_metadata_is_semantic_and_host_exact(
    command_generator: ModuleType,
    command_id: str,
    argument_schema: dict[str, object],
    host: str,
    relative_pattern: str,
    tool: str,
    choice_max: int,
) -> None:
    rendered = command_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT)
    name = command_id.removeprefix("flow/")
    relative = relative_pattern.format(name=name)
    record = _generated_record(relative, rendered[relative])
    assert record["kind"] == "flow_command_adapter"
    assert record["canonical_id"] == command_id
    assert record["host"] == host
    assert record["argument_schema"] == argument_schema
    assert record["question_transport"] == "conditional_native"
    assert record["question_tool"] == tool
    assert record["question_permission_check"] == "declared_and_allowed"
    assert record["choice_min"] == 2
    assert record["choice_max"] == choice_max
    assert record["disabled_choice_policy"] == "omit"
    assert record["custom_answer_behavior"] == "native_custom_input"
    assert record["sequential_fallback"] is True
    assert record["runtime_dependency"] == "agent_file_tools_only"
    assert record["git_tags"] == "forbidden"
    if record["interaction_mode"] == "structured_choice":
        assert record["question_capability"] == "structured-choice-v1"
        assert "structured-choice-v1" in record["shared_contracts"]


@pytest.mark.parametrize(
    "agent_id",
    ["executor", "plan-generator", "flow-reconciler", "quality-reviewer"],
)
def test_required_agent_invariants_and_host_capabilities_survive_generation(
    contract: FlowContract, agent_generator: ModuleType, agent_id: str
) -> None:
    rendered = agent_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT)
    agent = contract.agents[agent_id]
    for host, output in agent.generation.outputs.items():
        record = _generated_record(output.path, rendered[output.path])
        capability = contract.harnesses[host]
        assert record["kind"] == "flow_agent_adapter"
        assert record["canonical_id"] == agent_id
        assert record["canonical_source"] == agent.canonical_source
        assert record["host"] == host
        assert record["invariant_ids"] == list(agent.invariant_ids)
        assert record["interaction_requirement"] == agent.interaction_requirement
        assert record["tool_capability_requirements"] == list(
            agent.tool_requirements[host]
        )
        assert record["question_capability"] == {
            "bounds_enforcement": capability.bounds_enforcement,
            "choice_max": capability.choice_max,
            "choice_min": capability.choice_min,
            "custom_answer_behavior": capability.custom_answer_behavior,
            "disabled_choice_policy": "omit",
            "evidence": capability.evidence,
            "multi_select": capability.multi_select,
            "mutual_exclusion": capability.mutual_exclusion,
            "permission_check": capability.permission_check,
            "sequential_fallback": True,
            "supported_modes": list(capability.supported_modes),
            "tool": capability.verified_tool,
            "transport": capability.transport,
        }
        assert record["git_tags"] == "forbidden"

    if agent_id == "plan-generator":
        assert "structured-choice-v1" in agent.invariant_ids
    elif agent_id == "flow-reconciler":
        assert agent.invariant_ids == (
            "flow-state-v1",
            "markdown-transaction-v1",
            "git-no-tags-v1",
        )
        assert all(
            requirements == ("file_read", "file_write")
            for requirements in agent.tool_requirements.values()
        )
    elif agent_id == "executor":
        assert "worksheet-execution-v1" in agent.invariant_ids
    else:
        assert "quality-review-mandatory-v1" in agent.invariant_ids
        assert all(
            "file_write" not in requirements
            for requirements in agent.tool_requirements.values()
        )


def test_seven_host_families_use_only_verified_question_transports(
    contract: FlowContract,
) -> None:
    expected = {
        "antigravity": ("conditional_native", "ask_question", 2, 4),
        "claude_code": ("conditional_native", "AskUserQuestion", 2, 4),
        "codex_cli": ("conditional_native", "request_user_input", 2, 3),
        "opencode": ("conditional_native", "question", 2, 4),
        "cursor": ("sequential_text", None, None, None),
        "vscode_copilot": ("sequential_text", None, None, None),
        "openclaw": ("sequential_text", None, None, None),
    }
    assert {
        host: (
            capability.transport,
            capability.verified_tool,
            capability.choice_min,
            capability.choice_max,
        )
        for host, capability in contract.harnesses.items()
    } == expected
    assert all(
        capability.disabled_choice_policy == "omit" and capability.sequential_fallback
        for capability in contract.harnesses.values()
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
def test_every_tagged_request_variant_round_trips(
    contract: FlowContract, mode: str, choice_ids: tuple[str, ...]
) -> None:
    request_data = _request(mode, choice_ids)
    request = parse_request(contract, request_data)
    if mode == "open":
        result_data = _result(
            request_data,
            "submitted",
            open_text="Keep the exact requested name.",
            transport="sequential_text",
            tool_name=None,
            fallback_reasons=["tool_absent"],
        )
    elif mode == "multi_select":
        result_data = _result(
            request_data, "selected", selected_choice_ids=list(choice_ids[:1])
        )
    else:
        result_data = _result(
            request_data, "selected", selected_choice_ids=[choice_ids[0]]
        )
    result = normalize_result(contract, request, result_data)
    assert result.decision_id == request.decision_id
    assert result.selection_mode == mode

    with pytest.raises(ContractError, match="correlate"):
        normalize_result(
            contract,
            request,
            {**result_data, "decision_id": "another_decision"},
        )


def test_transport_scenario_trace_preserves_fallback_boundaries(
    contract: FlowContract,
) -> None:
    request = parse_request(
        contract,
        _request("multi_select", ("source", "tests", "docs", "ci")),
    )
    for host in ("antigravity", "claude_code", "opencode"):
        native = select_transport(
            contract, host, request, tool_available=True, tool_allowed=True
        )
        assert native.transport == "native"
        assert native.fallback_reasons == ()

    absent = select_transport(
        contract, "codex_cli", request, tool_available=False, tool_allowed=True
    )
    denied = select_transport(
        contract, "codex_cli", request, tool_available=True, tool_allowed=False
    )
    assert absent.fallback_reasons == ("tool_absent",)
    assert denied.fallback_reasons == ("tool_denied",)

    incompatible = select_transport(
        contract, "codex_cli", request, tool_available=True, tool_allowed=True
    )
    assert incompatible.transport == "sequential_text"
    assert incompatible.fallback_reasons == (
        "mode_unsupported",
        "choice_count_unsupported",
        "bounds_unsupported",
    )

    for host in ("cursor", "vscode_copilot", "openclaw"):
        sequential = select_transport(
            contract, host, request, tool_available=False, tool_allowed=False
        )
        assert sequential.tool_name is None
        assert sequential.fallback_reasons == ("tool_absent",)


def test_pre_and_post_quality_gates_represent_revision_and_refinement(
    contract: FlowContract,
) -> None:
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
    assert contract.interaction.transition_effects["refine"] == (
        "ask_next_structured_gap",
        "update",
        "revalidate",
        "represent_gate",
    )

    for gate, choices in contract.interaction.planning_gates.items():
        request_data = _request("single_select", choices, decision_id=gate)
        request = parse_request(contract, request_data)
        selected = "refine"
        result = normalize_result(
            contract,
            request,
            _result(request_data, "selected", selected_choice_ids=[selected]),
        )
        assert result.selected_choice_ids == (selected,)

        revision_data = _request(
            "open",
            (),
            decision_id=f"{gate}_revision",
            free_form_reason="revision_details",
        )
        revision = parse_request(contract, revision_data)
        assert (
            normalize_result(
                contract,
                revision,
                _result(
                    revision_data,
                    "submitted",
                    open_text="Split the task at the ownership boundary.",
                    transport="sequential_text",
                    tool_name=None,
                    fallback_reasons=["tool_absent"],
                ),
            ).outcome
            == "submitted"
        )


def test_reconciler_and_state_commands_remain_file_tool_only(
    contract: FlowContract, command_generator: ModuleType, agent_generator: ModuleType
) -> None:
    command_outputs = command_generator.render_surfaces(CONTRACT_PATH, REPO_ROOT)
    for command in contract.commands.values():
        if command.state_operations:
            assert command.runtime_dependency == "agent_file_tools_only"
        for relative, content in command_outputs.items():
            record = _generated_record(relative, content)
            if record["canonical_id"] == command.id:
                assert record["runtime_dependency"] == "agent_file_tools_only"
                assert record["procedure_source"] == command.procedure_source

    reconciler = contract.agents["flow-reconciler"]
    assert all(
        requirements == ("file_read", "file_write")
        for requirements in reconciler.tool_requirements.values()
    )
    for relative, content in agent_generator.render_surfaces(
        CONTRACT_PATH, REPO_ROOT
    ).items():
        record = _generated_record(relative, content)
        if record["canonical_id"] == "flow-reconciler":
            assert record["tool_capability_requirements"] == [
                "file_read",
                "file_write",
            ]
            assert record["canonical_source"] == reconciler.canonical_source
