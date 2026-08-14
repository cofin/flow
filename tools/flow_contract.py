#!/usr/bin/env python3
"""Strict parser and interaction oracle for Flow's maintainer contract.

This module is repository-development support. Installed Flow procedures remain
Markdown- and file-tool-only and never import or execute it.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn, cast

import yaml
from yaml.tokens import AliasToken, AnchorToken

SCHEMA_VERSION = 1
SELECTION_MODES = ("binary", "single_select", "multi_select", "open")
FALLBACK_REASON_ORDER = (
    "tool_absent",
    "tool_denied",
    "mode_unsupported",
    "choice_count_unsupported",
    "bounds_unsupported",
    "custom_unsupported",
    "disabled_policy_unsupported",
)
STATE_OPERATIONS = (
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
HARNESS_IDS = (
    "antigravity",
    "claude_code",
    "codex_cli",
    "opencode",
    "cursor",
    "vscode_copilot",
    "openclaw",
)
COMMAND_IDS = tuple(
    f"flow/{name}"
    for name in (
        "setup prd plan refine sync research docs implement status revert validate revise archive refresh task finish review cleanup"
    ).split()
)

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_COMMAND_PATTERN = re.compile(r"flow/[a-z][a-z0-9-]*\Z")
_PROCEDURE_PATTERN = re.compile(
    r"skills/flow(?:-[a-z-]+)?/(?:SKILL\.md|references/[a-z-]+\.md)\Z"
)
_GENERATED_PATH_PATTERN = re.compile(
    r"(?:commands|templates|\.codex|\.opencode|\.github)/[^/].*\Z"
)


class ContractError(ValueError):
    """Raised when a contract, request, result, or generated target is invalid."""


@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class StructuredChoiceRequest:
    contract_id: str
    decision_id: str
    selection_mode: str
    question: str
    disabled_choice_policy: str
    choices: tuple[Choice, ...]
    recommended_choice_id: str | None
    allow_custom: bool
    min_selections: int | None
    max_selections: int | None
    free_form_reason: str | None
    input_guidance: str | None


@dataclass(frozen=True)
class ChoiceResult:
    decision_id: str
    selection_mode: str
    outcome: str
    selected_choice_ids: tuple[str, ...]
    custom_text: str | None
    open_text: str | None
    transport: str
    tool_name: str | None
    fallback_reasons: tuple[str, ...]


@dataclass(frozen=True)
class TransportDecision:
    transport: str
    tool_name: str | None
    fallback_reasons: tuple[str, ...]


@dataclass(frozen=True)
class InteractionContract:
    id: str
    procedure_source: str
    request_keys: tuple[str, ...]
    choice_keys: tuple[str, ...]
    result_keys: tuple[str, ...]
    free_form_reasons: tuple[str, ...]
    fallback_reason_order: tuple[str, ...]
    planning_gates: Mapping[str, tuple[str, ...]]
    transition_effects: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class HarnessCapability:
    id: str
    transport: str
    verified_tool: str | None
    permission_check: str
    supported_modes: tuple[str, ...]
    choice_min: int | None
    choice_max: int | None
    mutual_exclusion: bool
    multi_select: bool
    bounds_enforcement: str
    custom_answer_behavior: str
    disabled_choice_policy: str
    sequential_fallback: bool
    evidence: str
    command_surface: str
    plan_capability: str


@dataclass(frozen=True)
class Invocation:
    spelling: str
    fallback: str


@dataclass(frozen=True)
class ArgumentSchema:
    syntax: str
    required: tuple[str, ...]
    optional: tuple[str, ...]


@dataclass(frozen=True)
class CommandRecord:
    id: str
    lifecycle_owner: str
    agent: str | None
    shared_contracts: tuple[str, ...]
    state_operations: tuple[str, ...]
    procedure_source: str
    argument_schema: ArgumentSchema
    mutability: str
    interaction_mode: str
    question_capability: str | None
    plan_capability: str
    completion_gates: tuple[str, ...]
    runtime_dependency: str
    invocations: Mapping[str, Invocation]


@dataclass(frozen=True)
class AgentOutput:
    path: str
    format: str
    mode: str | None
    edit_permission: str | None
    bash_permission: str | None
    web_permission: str | None


@dataclass(frozen=True)
class AgentGeneration:
    description: str
    nickname_candidates: tuple[str, ...]
    outputs: Mapping[str, AgentOutput]


@dataclass(frozen=True)
class AgentRecord:
    id: str
    canonical_source: str
    supported_host_adapters: tuple[str, ...]
    invariant_ids: tuple[str, ...]
    interaction_requirement: str
    tool_requirements: Mapping[str, tuple[str, ...]]
    generation: AgentGeneration


@dataclass(frozen=True)
class SharedContract:
    id: str
    source: str
    runtime_dependency: str


@dataclass(frozen=True)
class FlowContract:
    schema_version: int
    git_policy: GitPolicy
    state_operations: tuple[str, ...]
    shared_contracts: Mapping[str, SharedContract]
    interaction: InteractionContract
    harnesses: Mapping[str, HarnessCapability]
    commands: Mapping[str, CommandRecord]
    agents: Mapping[str, AgentRecord]


@dataclass(frozen=True)
class GitPolicy:
    tags: str
    allowed_local_operations: tuple[str, ...]


def _fail(message: str) -> NoReturn:
    raise ContractError(message)


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        _fail(f"{context} keys must be strings")
    return cast("dict[str, Any]", value)


def _sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be a list")
    return cast("list[Any]", value)


def _exact_keys(
    value: Mapping[str, Any], expected: tuple[str, ...], context: str
) -> None:
    actual = set(value)
    required = set(expected)
    if actual != required:
        missing = sorted(required - actual)
        unknown = sorted(actual - required)
        _fail(f"{context} keys mismatch; missing={missing}, unknown={unknown}")


def _string(value: Any, context: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        _fail(f"{context} must be a non-empty string")
    return value


def _nullable_string(value: Any, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context)


def _bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{context} must be a boolean")
    return value


def _integer(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(f"{context} must be an integer")
    return value


def _string_tuple(value: Any, context: str, *, unique: bool = True) -> tuple[str, ...]:
    items = tuple(_string(item, f"{context}[]") for item in _sequence(value, context))
    if unique and len(items) != len(set(items)):
        _fail(f"{context} contains duplicates")
    return items


def _ordered_records(value: Any, context: str) -> list[dict[str, Any]]:
    return [
        _mapping(item, f"{context}[{index}]")
        for index, item in enumerate(_sequence(value, context))
    ]


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"unable to read {path}: {exc}") from exc
    try:
        if any(
            isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)
        ):
            _fail("YAML aliases and anchors are forbidden")
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid YAML: {exc}") from exc
    return _mapping(loaded, "contract")


def load_contract(path: str | Path) -> FlowContract:
    """Load and fully validate a Flow contract."""
    data = _load_yaml(Path(path))
    _exact_keys(
        data,
        (
            "schema_version",
            "git_policy",
            "state_operations",
            "shared_contracts",
            "interaction_contracts",
            "harnesses",
            "commands",
            "agents",
        ),
        "contract",
    )
    version = _integer(data["schema_version"], "schema_version")
    if version != SCHEMA_VERSION:
        _fail(f"unsupported schema_version {version}")
    git_policy_data = _mapping(data["git_policy"], "git_policy")
    _exact_keys(git_policy_data, ("tags", "allowed_local_operations"), "git_policy")
    tags = _string(git_policy_data["tags"], "git_policy.tags")
    allowed_local_operations = _string_tuple(
        git_policy_data["allowed_local_operations"],
        "git_policy.allowed_local_operations",
    )
    if tags != "forbidden" or allowed_local_operations != (
        "notes",
        "branches",
        "worktrees",
    ):
        _fail(
            "Git policy must forbid tags and allow only notes, branches, and worktrees"
        )
    git_policy = GitPolicy(tags, allowed_local_operations)
    state_operations = _string_tuple(data["state_operations"], "state_operations")
    if state_operations != STATE_OPERATIONS:
        _fail("state_operations must be the exact canonical operation vocabulary")
    shared_contracts = _parse_shared_contracts(data["shared_contracts"])
    interaction = _parse_interaction(data["interaction_contracts"])
    harnesses = _parse_harnesses(data["harnesses"])
    agents = _parse_agents(data["agents"])
    commands = _parse_commands(
        data["commands"],
        interaction,
        harnesses,
        agents,
        state_operations,
        shared_contracts,
    )
    return FlowContract(
        version,
        git_policy,
        state_operations,
        shared_contracts,
        interaction,
        harnesses,
        commands,
        agents,
    )


def _parse_shared_contracts(value: Any) -> Mapping[str, SharedContract]:
    result: dict[str, SharedContract] = {}
    for index, data in enumerate(_ordered_records(value, "shared_contracts")):
        context = f"shared_contracts[{index}]"
        _exact_keys(data, ("id", "source", "runtime_dependency"), context)
        contract_id = _string(data["id"], f"{context}.id")
        if not _ID_PATTERN.fullmatch(contract_id) or contract_id in result:
            _fail(f"invalid or duplicate shared contract id {contract_id}")
        source = _string(data["source"], f"{context}.source")
        if not _PROCEDURE_PATTERN.fullmatch(source):
            _fail(f"{contract_id} has invalid shared contract source")
        runtime = _string(data["runtime_dependency"], f"{context}.runtime_dependency")
        if runtime != "agent_file_tools_only":
            _fail(f"{contract_id} has forbidden runtime dependency {runtime}")
        result[contract_id] = SharedContract(contract_id, source, runtime)
    required = {"flow-state-v1", "structured-choice-v1", "worksheet-execution-v1"}
    if not required.issubset(result):
        _fail("required shared contracts are missing")
    return result


def _parse_interaction(value: Any) -> InteractionContract:
    contracts = _mapping(value, "interaction_contracts")
    _exact_keys(contracts, ("structured-choice-v1",), "interaction_contracts")
    data = _mapping(
        contracts["structured-choice-v1"], "interaction_contracts.structured-choice-v1"
    )
    _exact_keys(
        data,
        (
            "procedure_source",
            "request",
            "result",
            "fallback_reason_order",
            "planning_gates",
            "transition_effects",
        ),
        "structured-choice-v1",
    )
    procedure = _string(
        data["procedure_source"], "structured-choice-v1.procedure_source"
    )
    if procedure != "skills/flow/references/interaction.md":
        _fail(
            "structured-choice-v1 may link only to skills/flow/references/interaction.md"
        )

    request = _mapping(data["request"], "structured-choice-v1.request")
    _exact_keys(
        request,
        ("exact_keys", "exact_choice_keys", "variants"),
        "structured-choice-v1.request",
    )
    request_keys = _string_tuple(request["exact_keys"], "request.exact_keys")
    expected_request_keys = (
        "contract_id",
        "decision_id",
        "selection_mode",
        "question",
        "disabled_choice_policy",
        "choices",
        "recommended_choice_id",
        "allow_custom",
        "min_selections",
        "max_selections",
        "free_form_reason",
        "input_guidance",
    )
    if set(request_keys) != set(expected_request_keys):
        _fail("request.exact_keys is not the canonical request key set")
    choice_keys = _string_tuple(
        request["exact_choice_keys"], "request.exact_choice_keys"
    )
    if set(choice_keys) != {"id", "label", "description"}:
        _fail("request.exact_choice_keys must be exactly id,label,description")
    variants = _mapping(request["variants"], "request.variants")
    _exact_keys(variants, SELECTION_MODES, "request.variants")
    free_form_reasons: tuple[str, ...] = ()
    expected_counts = {
        "binary": (2, 2),
        "single_select": (2, 4),
        "multi_select": (2, 4),
        "open": (0, 0),
    }
    for mode in SELECTION_MODES:
        variant = _mapping(variants[mode], f"request.variants.{mode}")
        expected_keys: tuple[str, ...] = (
            "choice_count",
            "recommendation",
            "allow_custom",
            "bounds",
        )
        if mode == "open":
            expected_keys += ("free_form_reasons",)
        _exact_keys(variant, expected_keys, f"request.variants.{mode}")
        counts = tuple(
            _integer(item, f"{mode}.choice_count")
            for item in _sequence(variant["choice_count"], f"{mode}.choice_count")
        )
        if counts != expected_counts[mode]:
            _fail(f"{mode} has invalid choice cardinality")
        recommendation = variant["recommendation"]
        allow_custom = _bool(variant["allow_custom"], f"{mode}.allow_custom")
        bounds = _string(variant["bounds"], f"{mode}.bounds")
        if mode == "open":
            if recommendation is not None or allow_custom or bounds != "forbidden":
                _fail(
                    "open variant must forbid recommendation, custom input, and bounds"
                )
            free_form_reasons = _string_tuple(
                variant["free_form_reasons"], "open.free_form_reasons"
            )
            if free_form_reasons != (
                "user_defined_identifier",
                "revision_details",
                "other_constraint",
            ):
                _fail("open.free_form_reasons is not canonical")
        elif recommendation != "first_choice" or not allow_custom:
            _fail(f"{mode} must require first-choice recommendation and custom input")
        elif bounds != ("required" if mode == "multi_select" else "forbidden"):
            _fail(f"{mode} has invalid bounds policy")

    result = _mapping(data["result"], "structured-choice-v1.result")
    _exact_keys(result, ("exact_keys", "outcomes"), "structured-choice-v1.result")
    result_keys = _string_tuple(result["exact_keys"], "result.exact_keys")
    expected_result_keys = (
        "decision_id",
        "selection_mode",
        "outcome",
        "selected_choice_ids",
        "custom_text",
        "open_text",
        "transport",
        "tool_name",
        "fallback_reasons",
    )
    if set(result_keys) != set(expected_result_keys):
        _fail("result.exact_keys is not canonical")
    outcomes = _mapping(result["outcomes"], "result.outcomes")
    expected_outcomes = {
        "binary": ("selected", "custom", "cancelled"),
        "single_select": ("selected", "custom", "cancelled"),
        "multi_select": ("selected", "selected_with_custom", "cancelled"),
        "open": ("submitted", "cancelled"),
    }
    _exact_keys(outcomes, SELECTION_MODES, "result.outcomes")
    for mode, expected in expected_outcomes.items():
        if _string_tuple(outcomes[mode], f"result.outcomes.{mode}") != expected:
            _fail(f"result outcomes for {mode} are not canonical")

    fallback_order = _string_tuple(
        data["fallback_reason_order"], "fallback_reason_order"
    )
    if fallback_order != FALLBACK_REASON_ORDER:
        _fail("fallback_reason_order is not canonical")
    gates_data = _mapping(data["planning_gates"], "planning_gates")
    _exact_keys(gates_data, ("pre_quality", "post_quality"), "planning_gates")
    gates = {
        key: _string_tuple(value, f"planning_gates.{key}")
        for key, value in gates_data.items()
    }
    if gates != {
        "pre_quality": ("revise", "refine"),
        "post_quality": ("approve", "revise", "refine"),
    }:
        _fail(
            "planning gates must be exact Revise|Refine and Approve|Revise|Refine sets"
        )
    effects_data = _mapping(data["transition_effects"], "transition_effects")
    _exact_keys(
        effects_data, ("approve", "revise", "refine", "cancelled"), "transition_effects"
    )
    effects = {
        key: _string_tuple(value, f"transition_effects.{key}")
        for key, value in effects_data.items()
    }
    required_effects = {
        "approve": ("advance",),
        "revise": (
            "collect_open_revision_details",
            "apply_changes",
            "increment_plan_identity_if_plan_bearing",
            "revalidate",
            "represent_gate",
        ),
        "refine": ("ask_next_structured_gap", "update", "revalidate", "represent_gate"),
        "cancelled": ("stop_without_approval_or_mutation",),
    }
    if effects != required_effects:
        _fail("transition_effects are not canonical")
    return InteractionContract(
        "structured-choice-v1",
        procedure,
        request_keys,
        choice_keys,
        result_keys,
        free_form_reasons,
        fallback_order,
        gates,
        effects,
    )


def _parse_harnesses(value: Any) -> Mapping[str, HarnessCapability]:
    records = _ordered_records(value, "harnesses")
    result: dict[str, HarnessCapability] = {}
    keys = (
        "id",
        "transport",
        "verified_tool",
        "permission_check",
        "supported_modes",
        "choice_min",
        "choice_max",
        "mutual_exclusion",
        "multi_select",
        "bounds_enforcement",
        "custom_answer_behavior",
        "disabled_choice_policy",
        "sequential_fallback",
        "evidence",
        "command_surface",
        "plan_capability",
    )
    for index, data in enumerate(records):
        context = f"harnesses[{index}]"
        _exact_keys(data, keys, context)
        harness_id = _string(data["id"], f"{context}.id")
        if harness_id in result:
            _fail(f"duplicate harness id {harness_id}")
        transport = _string(data["transport"], f"{context}.transport")
        tool = _nullable_string(data["verified_tool"], f"{context}.verified_tool")
        permission = _string(data["permission_check"], f"{context}.permission_check")
        modes = _string_tuple(data["supported_modes"], f"{context}.supported_modes")
        if any(mode not in SELECTION_MODES for mode in modes):
            _fail(f"{harness_id} contains unsupported selection mode")
        choice_min = (
            data["choice_min"]
            if data["choice_min"] is None
            else _integer(data["choice_min"], f"{context}.choice_min")
        )
        choice_max = (
            data["choice_max"]
            if data["choice_max"] is None
            else _integer(data["choice_max"], f"{context}.choice_max")
        )
        mutual = _bool(data["mutual_exclusion"], f"{context}.mutual_exclusion")
        multi = _bool(data["multi_select"], f"{context}.multi_select")
        bounds = _string(data["bounds_enforcement"], f"{context}.bounds_enforcement")
        custom = _string(
            data["custom_answer_behavior"], f"{context}.custom_answer_behavior"
        )
        disabled = _string(
            data["disabled_choice_policy"], f"{context}.disabled_choice_policy"
        )
        fallback = _bool(data["sequential_fallback"], f"{context}.sequential_fallback")
        evidence = _string(data["evidence"], f"{context}.evidence")
        command_surface = _string(data["command_surface"], f"{context}.command_surface")
        plan_capability = _string(data["plan_capability"], f"{context}.plan_capability")
        if disabled != "omit" or not fallback:
            _fail(
                f"{harness_id} must omit disabled choices and support sequential fallback"
            )
        if tool is None:
            if (
                transport != "sequential_text"
                or modes
                or any(item is not None for item in (choice_min, choice_max))
                or mutual
                or multi
            ):
                _fail(f"{harness_id} makes impossible null-tool capability claims")
            if (
                permission != "not_applicable"
                or bounds != "unsupported"
                or custom != "sequential_text_only"
            ):
                _fail(f"{harness_id} has invalid null-tool behavior")
        else:
            if (
                transport != "conditional_native"
                or permission != "declared_and_allowed"
            ):
                _fail(
                    f"{harness_id} native tool must be conditional and permission checked"
                )
            if (
                choice_min is None
                or choice_max is None
                or choice_min < 2
                or choice_max < choice_min
            ):
                _fail(f"{harness_id} has invalid choice bounds")
            if "open" in modes or not mutual or custom != "native_custom_input":
                _fail(f"{harness_id} makes impossible native capability claims")
            if multi != ("multi_select" in modes):
                _fail(f"{harness_id} multi_select claim contradicts supported_modes")
            expected_bounds = "agent_validated" if multi else "unsupported"
            if bounds != expected_bounds:
                _fail(f"{harness_id} has invalid bounds enforcement")
        if command_surface not in {
            "skill_derived",
            "slash_command",
            "optional_slash_command",
            "natural_language",
        }:
            _fail(f"{harness_id} has invalid command_surface")
        if plan_capability not in {"native", "reasoning_only", "none"}:
            _fail(f"{harness_id} has invalid plan_capability")
        result[harness_id] = HarnessCapability(
            harness_id,
            transport,
            tool,
            permission,
            modes,
            choice_min,
            choice_max,
            mutual,
            multi,
            bounds,
            custom,
            disabled,
            fallback,
            evidence,
            command_surface,
            plan_capability,
        )
    if tuple(result) != HARNESS_IDS:
        _fail(
            "harness records must contain the exact seven families in canonical order"
        )
    expected_tools = {
        "antigravity": "ask_question",
        "claude_code": "AskUserQuestion",
        "codex_cli": "request_user_input",
        "opencode": "question",
        "cursor": None,
        "vscode_copilot": None,
        "openclaw": None,
    }
    if {key: item.verified_tool for key, item in result.items()} != expected_tools:
        _fail("verified host question tool mapping is not canonical")
    expected_command_surfaces = {
        "antigravity": "skill_derived",
        "claude_code": "slash_command",
        "codex_cli": "natural_language",
        "opencode": "optional_slash_command",
        "cursor": "natural_language",
        "vscode_copilot": "natural_language",
        "openclaw": "natural_language",
    }
    if {
        key: item.command_surface for key, item in result.items()
    } != expected_command_surfaces:
        _fail("host command surface mapping is not canonical")
    expected_plan_capabilities = {
        "antigravity": "native",
        "claude_code": "native",
        "codex_cli": "native",
        "opencode": "reasoning_only",
        "cursor": "reasoning_only",
        "vscode_copilot": "reasoning_only",
        "openclaw": "none",
    }
    if {
        key: item.plan_capability for key, item in result.items()
    } != expected_plan_capabilities:
        _fail("host plan capability mapping is not canonical")
    for key in ("antigravity", "claude_code", "opencode"):
        item = result[key]
        if item.supported_modes != ("binary", "single_select", "multi_select") or (
            item.choice_min,
            item.choice_max,
        ) != (2, 4):
            _fail(f"{key} must support binary/single/multi with 2-4 choices")
    codex = result["codex_cli"]
    if codex.supported_modes != ("binary", "single_select") or (
        codex.choice_min,
        codex.choice_max,
    ) != (2, 3):
        _fail("codex_cli must support binary/single with 2-3 choices")
    return result


def _parse_commands(
    value: Any,
    interaction: InteractionContract,
    harnesses: Mapping[str, HarnessCapability],
    agents: Mapping[str, AgentRecord],
    state_operations: tuple[str, ...],
    shared_contracts: Mapping[str, SharedContract],
) -> Mapping[str, CommandRecord]:
    records = _ordered_records(value, "commands")
    result: dict[str, CommandRecord] = {}
    invocation_spellings: set[tuple[str, str]] = set()
    keys = (
        "id",
        "lifecycle_owner",
        "agent",
        "shared_contracts",
        "state_operations",
        "procedure_source",
        "argument_schema",
        "mutability",
        "interaction_mode",
        "question_capability",
        "plan_capability",
        "completion_gates",
        "runtime_dependency",
        "invocations",
    )
    for index, data in enumerate(records):
        context = f"commands[{index}]"
        _exact_keys(data, keys, context)
        command_id = _string(data["id"], f"{context}.id")
        if not _COMMAND_PATTERN.fullmatch(command_id) or command_id in result:
            _fail(f"invalid or duplicate command id {command_id}")
        owner = _string(data["lifecycle_owner"], f"{context}.lifecycle_owner")
        agent = _nullable_string(data["agent"], f"{context}.agent")
        if agent is not None and agent not in agents:
            _fail(f"{command_id} references unknown agent {agent}")
        shared = _string_tuple(data["shared_contracts"], f"{context}.shared_contracts")
        if any(item not in shared_contracts for item in shared):
            _fail(f"{command_id} references unknown shared contract")
        operations = _string_tuple(
            data["state_operations"], f"{context}.state_operations"
        )
        if any(item not in state_operations for item in operations):
            _fail(f"{command_id} references unknown state operation")
        procedure = _string(data["procedure_source"], f"{context}.procedure_source")
        if not _PROCEDURE_PATTERN.fullmatch(procedure):
            _fail(f"{command_id} has invalid procedure source")
        arguments_data = _mapping(data["argument_schema"], f"{context}.argument_schema")
        _exact_keys(
            arguments_data,
            ("syntax", "required", "optional"),
            f"{context}.argument_schema",
        )
        arguments = ArgumentSchema(
            _string(arguments_data["syntax"], f"{context}.argument_schema.syntax"),
            _string_tuple(
                arguments_data["required"], f"{context}.argument_schema.required"
            ),
            _string_tuple(
                arguments_data["optional"], f"{context}.argument_schema.optional"
            ),
        )
        if set(arguments.required) & set(arguments.optional):
            _fail(f"{command_id} has overlapping required/optional arguments")
        mutability = _string(data["mutability"], f"{context}.mutability")
        if mutability not in {
            "read_only",
            "planning_write",
            "repository_write",
            "state_write",
        }:
            _fail(f"{command_id} has invalid mutability")
        if mutability == "read_only" and any(
            operation != "status" for operation in operations
        ):
            _fail(f"{command_id} claims read-only mutability for a state mutation")
        interaction_mode = _string(
            data["interaction_mode"], f"{context}.interaction_mode"
        )
        question = _nullable_string(
            data["question_capability"], f"{context}.question_capability"
        )
        if interaction_mode not in {"none", "structured_choice"}:
            _fail(f"{command_id} has invalid interaction_mode")
        if (interaction_mode == "structured_choice") != (question == interaction.id):
            _fail(f"{command_id} interaction and question capability contradict")
        if question is not None and interaction.id not in shared:
            _fail(f"{command_id} interactive command omits structured-choice-v1")
        plan = _string(data["plan_capability"], f"{context}.plan_capability")
        if plan not in {"required", "preferred", "none"}:
            _fail(f"{command_id} has invalid plan_capability")
        gates = _string_tuple(data["completion_gates"], f"{context}.completion_gates")
        runtime = _string(data["runtime_dependency"], f"{context}.runtime_dependency")
        if runtime not in {"none", "agent_file_tools_only"}:
            _fail(f"{command_id} has forbidden runtime dependency {runtime}")
        if operations and runtime != "agent_file_tools_only":
            _fail(f"state-mutating command {command_id} must use agent_file_tools_only")
        invocations_data = _mapping(data["invocations"], f"{context}.invocations")
        _exact_keys(invocations_data, HARNESS_IDS, f"{context}.invocations")
        invocations: dict[str, Invocation] = {}
        for harness_id in HARNESS_IDS:
            invocation_data = _mapping(
                invocations_data[harness_id], f"{context}.invocations.{harness_id}"
            )
            _exact_keys(
                invocation_data,
                ("spelling", "fallback"),
                f"{context}.invocations.{harness_id}",
            )
            spelling = _string(
                invocation_data["spelling"],
                f"{context}.invocations.{harness_id}.spelling",
            )
            fallback = _string(
                invocation_data["fallback"],
                f"{context}.invocations.{harness_id}.fallback",
            )
            if spelling.startswith("/") and harnesses[
                harness_id
            ].command_surface not in {
                "skill_derived",
                "slash_command",
                "optional_slash_command",
            }:
                _fail(
                    f"{command_id} promises unsupported slash spelling for {harness_id}"
                )
            spelling_key = (harness_id, spelling)
            if spelling_key in invocation_spellings:
                _fail(f"duplicate invocation spelling {spelling!r} for {harness_id}")
            invocation_spellings.add(spelling_key)
            invocations[harness_id] = Invocation(spelling, fallback)
        command_name = command_id.removeprefix("flow/")
        expected_slash = f"/flow-{command_name}"
        for harness_id in ("antigravity", "claude_code", "opencode"):
            if invocations[harness_id].spelling != expected_slash:
                _fail(f"{command_id} has invalid {harness_id} invocation spelling")
        for harness_id in ("codex_cli", "cursor", "vscode_copilot", "openclaw"):
            invocation = invocations[harness_id]
            if (
                invocation.spelling.startswith("/")
                or invocation.spelling != invocation.fallback
            ):
                _fail(
                    f"{command_id} has invalid natural-language invocation for {harness_id}"
                )
        if any(
            invocation.fallback.startswith("/") for invocation in invocations.values()
        ):
            _fail(f"{command_id} fallback invocations must be natural language")
        result[command_id] = CommandRecord(
            command_id,
            owner,
            agent,
            shared,
            operations,
            procedure,
            arguments,
            mutability,
            interaction_mode,
            question,
            plan,
            gates,
            runtime,
            invocations,
        )
    if tuple(result) != COMMAND_IDS:
        _fail("commands must contain the exact 18 lifecycle ids in canonical order")
    return result


def _parse_agents(value: Any) -> Mapping[str, AgentRecord]:
    records = _ordered_records(value, "agents")
    result: dict[str, AgentRecord] = {}
    output_paths: set[str] = set()
    keys = (
        "id",
        "canonical_source",
        "supported_host_adapters",
        "invariant_ids",
        "interaction_requirement",
        "tool_requirements",
        "generation",
    )
    for index, data in enumerate(records):
        context = f"agents[{index}]"
        _exact_keys(data, keys, context)
        agent_id = _string(data["id"], f"{context}.id")
        if not _ID_PATTERN.fullmatch(agent_id) or agent_id in result:
            _fail(f"invalid or duplicate agent id {agent_id}")
        source = _string(data["canonical_source"], f"{context}.canonical_source")
        if source != f"agents/{agent_id}.md":
            _fail(f"{agent_id} canonical source must be agents/{agent_id}.md")
        adapters = _string_tuple(
            data["supported_host_adapters"], f"{context}.supported_host_adapters"
        )
        if not adapters or any(item not in HARNESS_IDS for item in adapters):
            _fail(f"{agent_id} has invalid supported host adapters")
        invariants = _string_tuple(data["invariant_ids"], f"{context}.invariant_ids")
        if not invariants or any(
            not _ID_PATTERN.fullmatch(item) for item in invariants
        ):
            _fail(f"{agent_id} has invalid invariant ids")
        interaction = _string(
            data["interaction_requirement"], f"{context}.interaction_requirement"
        )
        if interaction not in {"none", "structured_choice_optional"}:
            _fail(f"{agent_id} has invalid interaction requirement")
        if (
            interaction == "structured_choice_optional"
            and "structured-choice-v1" not in invariants
        ):
            _fail(f"{agent_id} may ask but omits the structured-choice invariant")
        tools_data = _mapping(data["tool_requirements"], f"{context}.tool_requirements")
        _exact_keys(tools_data, adapters, f"{context}.tool_requirements")
        tools = {
            key: _string_tuple(item, f"{context}.tool_requirements.{key}")
            for key, item in tools_data.items()
        }
        generation_data = _mapping(data["generation"], f"{context}.generation")
        _exact_keys(
            generation_data,
            ("description", "nickname_candidates", "outputs"),
            f"{context}.generation",
        )
        description = _string(
            generation_data["description"], f"{context}.generation.description"
        )
        nicknames = _string_tuple(
            generation_data["nickname_candidates"],
            f"{context}.generation.nickname_candidates",
        )
        outputs_data = _mapping(
            generation_data["outputs"], f"{context}.generation.outputs"
        )
        outputs: dict[str, AgentOutput] = {}
        for harness_id, raw_output in outputs_data.items():
            if harness_id not in adapters:
                _fail(f"{agent_id} generates unsupported adapter {harness_id}")
            output = _mapping(raw_output, f"{context}.generation.outputs.{harness_id}")
            _exact_keys(
                output,
                (
                    "path",
                    "format",
                    "mode",
                    "edit_permission",
                    "bash_permission",
                    "web_permission",
                ),
                f"{context}.generation.outputs.{harness_id}",
            )
            path = _string(
                output["path"], f"{context}.generation.outputs.{harness_id}.path"
            )
            if (
                not _GENERATED_PATH_PATTERN.fullmatch(path)
                or path in output_paths
                or ".." in Path(path).parts
            ):
                _fail(f"invalid or duplicate generated agent path {path}")
            output_paths.add(path)
            fmt = _string(
                output["format"], f"{context}.generation.outputs.{harness_id}.format"
            )
            mode = _nullable_string(
                output["mode"], f"{context}.generation.outputs.{harness_id}.mode"
            )
            edit = _nullable_string(
                output["edit_permission"],
                f"{context}.generation.outputs.{harness_id}.edit_permission",
            )
            bash = _nullable_string(
                output["bash_permission"],
                f"{context}.generation.outputs.{harness_id}.bash_permission",
            )
            web = _nullable_string(
                output["web_permission"],
                f"{context}.generation.outputs.{harness_id}.web_permission",
            )
            if fmt not in {
                "antigravity_markdown",
                "codex_toml",
                "opencode_markdown",
                "vscode_markdown",
            }:
                _fail(f"{agent_id} has unsupported output format {fmt}")
            if fmt == "opencode_markdown":
                if mode != "subagent" or any(
                    item not in {"allow", "deny"} for item in (edit, bash, web)
                ):
                    _fail(f"{agent_id} OpenCode generation metadata is incomplete")
            elif any(item is not None for item in (mode, edit, bash, web)):
                _fail(f"{agent_id} non-OpenCode adapter has OpenCode-only metadata")
            outputs[harness_id] = AgentOutput(path, fmt, mode, edit, bash, web)
        if not outputs:
            _fail(f"{agent_id} has no generated outputs")
        expected_generated_adapters = set(adapters) - {"claude_code"}
        if set(outputs) != expected_generated_adapters:
            _fail(f"{agent_id} generated adapter coverage is incomplete")
        expected_paths = {
            "antigravity": f"templates/antigravity/agents/{agent_id}.md",
            "codex_cli": f".codex/agents/{agent_id}.toml",
            "opencode": f".opencode/agents/{agent_id}.md",
            "vscode_copilot": f".github/agents/{agent_id}.agent.md",
        }
        if {key: output.path for key, output in outputs.items()} != {
            key: expected_paths[key] for key in expected_generated_adapters
        }:
            _fail(f"{agent_id} generated adapter paths are not canonical")
        expected_formats = {
            "antigravity": "antigravity_markdown",
            "codex_cli": "codex_toml",
            "opencode": "opencode_markdown",
            "vscode_copilot": "vscode_markdown",
        }
        if {key: output.format for key, output in outputs.items()} != {
            key: expected_formats[key] for key in expected_generated_adapters
        }:
            _fail(f"{agent_id} generated adapter formats are not canonical")
        result[agent_id] = AgentRecord(
            agent_id,
            source,
            adapters,
            invariants,
            interaction,
            tools,
            AgentGeneration(description, nicknames, outputs),
        )
    return result


def parse_request(
    contract: FlowContract, value: Mapping[str, Any]
) -> StructuredChoiceRequest:
    """Validate and normalize one exact structured-choice request."""
    data = _mapping(dict(value), "request")
    _exact_keys(data, contract.interaction.request_keys, "request")
    if data["contract_id"] != contract.interaction.id:
        _fail("request contract_id does not match structured-choice-v1")
    decision_id = _string(data["decision_id"], "request.decision_id")
    mode = _string(data["selection_mode"], "request.selection_mode")
    if mode not in SELECTION_MODES:
        _fail(f"unsupported selection_mode {mode}")
    question = _string(data["question"], "request.question")
    if data["disabled_choice_policy"] != "omit":
        _fail("disabled_choice_policy must be omit")
    choices: list[Choice] = []
    choice_ids: list[str] = []
    for index, raw_choice in enumerate(_sequence(data["choices"], "request.choices")):
        choice_data = _mapping(raw_choice, f"request.choices[{index}]")
        _exact_keys(
            choice_data, contract.interaction.choice_keys, f"request.choices[{index}]"
        )
        choice_id = _string(choice_data["id"], f"request.choices[{index}].id")
        label = _string(choice_data["label"], f"request.choices[{index}].label")
        description = _string(
            choice_data["description"], f"request.choices[{index}].description"
        )
        if not _ID_PATTERN.fullmatch(choice_id):
            _fail(f"invalid choice id {choice_id}")
        if not 1 <= len(label) <= 60 or "(Recommended)" in label:
            _fail("choice label must be 1-60 characters and omit recommendation suffix")
        if not 1 <= len(description) <= 160:
            _fail("choice description must be 1-160 characters")
        choice_ids.append(choice_id)
        choices.append(Choice(choice_id, label, description))
    if len(choice_ids) != len(set(choice_ids)):
        _fail("choice ids must be unique")
    counts = {
        "binary": (2, 2),
        "single_select": (2, 4),
        "multi_select": (2, 4),
        "open": (0, 0),
    }
    minimum_count, maximum_count = counts[mode]
    if not minimum_count <= len(choices) <= maximum_count:
        _fail(f"{mode} requires {minimum_count}-{maximum_count} choices")
    recommendation = data["recommended_choice_id"]
    allow_custom = _bool(data["allow_custom"], "request.allow_custom")
    min_selections = data["min_selections"]
    max_selections = data["max_selections"]
    free_form_reason = data["free_form_reason"]
    input_guidance = data["input_guidance"]
    if mode == "open":
        if (
            recommendation is not None
            or allow_custom
            or min_selections is not None
            or max_selections is not None
        ):
            _fail("open requests forbid choices, recommendation, custom, and bounds")
        free_form_reason = _string(free_form_reason, "request.free_form_reason")
        if free_form_reason not in contract.interaction.free_form_reasons:
            _fail("invalid open free_form_reason")
        input_guidance = _string(input_guidance, "request.input_guidance")
    else:
        if recommendation != choice_ids[0] or not allow_custom:
            _fail(
                "structured requests require the first choice recommendation and custom input"
            )
        if free_form_reason is not None or input_guidance is not None:
            _fail("structured requests forbid open-input fields")
        if mode == "multi_select":
            min_selections = _integer(min_selections, "request.min_selections")
            max_selections = _integer(max_selections, "request.max_selections")
            if not 1 <= min_selections <= max_selections <= len(choices):
                _fail(
                    "multi_select bounds must satisfy 1 <= min <= max <= choice_count"
                )
        elif min_selections is not None or max_selections is not None:
            _fail(f"{mode} forbids selection bounds")
    return StructuredChoiceRequest(
        contract.interaction.id,
        decision_id,
        mode,
        question,
        "omit",
        tuple(choices),
        cast("str | None", recommendation),
        allow_custom,
        cast("int | None", min_selections),
        cast("int | None", max_selections),
        cast("str | None", free_form_reason),
        cast("str | None", input_guidance),
    )


def select_transport(
    contract: FlowContract,
    harness_id: str,
    request: StructuredChoiceRequest,
    *,
    tool_available: bool,
    tool_allowed: bool,
) -> TransportDecision:
    """Select native or sequential transport with canonical fallback reasons."""
    try:
        capability = contract.harnesses[harness_id]
    except KeyError as exc:
        raise ContractError(f"unknown harness {harness_id}") from exc
    if capability.verified_tool is None:
        return TransportDecision("sequential_text", None, ("tool_absent",))
    if not tool_available:
        return TransportDecision(
            "sequential_text", capability.verified_tool, ("tool_absent",)
        )
    if not tool_allowed:
        return TransportDecision(
            "sequential_text", capability.verified_tool, ("tool_denied",)
        )
    reasons: list[str] = []
    if request.selection_mode not in capability.supported_modes:
        reasons.append("mode_unsupported")
    if not (
        capability.choice_min is not None
        and capability.choice_max is not None
        and capability.choice_min <= len(request.choices) <= capability.choice_max
    ):
        reasons.append("choice_count_unsupported")
    if (
        request.selection_mode == "multi_select"
        and capability.bounds_enforcement != "agent_validated"
    ):
        reasons.append("bounds_unsupported")
    if (
        request.allow_custom
        and capability.custom_answer_behavior != "native_custom_input"
    ):
        reasons.append("custom_unsupported")
    if request.disabled_choice_policy != capability.disabled_choice_policy:
        reasons.append("disabled_policy_unsupported")
    ordered = tuple(
        reason
        for reason in contract.interaction.fallback_reason_order
        if reason in reasons
    )
    if ordered:
        return TransportDecision("sequential_text", capability.verified_tool, ordered)
    return TransportDecision("native", capability.verified_tool, ())


def normalize_result(
    contract: FlowContract,
    request: StructuredChoiceRequest,
    value: Mapping[str, Any],
) -> ChoiceResult:
    """Validate and correlate an exact structured-choice result union."""
    data = _mapping(dict(value), "result")
    _exact_keys(data, contract.interaction.result_keys, "result")
    if (
        data["decision_id"] != request.decision_id
        or data["selection_mode"] != request.selection_mode
    ):
        _fail("result does not correlate to the request decision and mode")
    outcome = _string(data["outcome"], "result.outcome")
    allowed_outcomes = {
        "binary": {"selected", "custom", "cancelled"},
        "single_select": {"selected", "custom", "cancelled"},
        "multi_select": {"selected", "selected_with_custom", "cancelled"},
        "open": {"submitted", "cancelled"},
    }[request.selection_mode]
    if outcome not in allowed_outcomes:
        _fail(f"outcome {outcome} is invalid for {request.selection_mode}")
    selected = _string_tuple(data["selected_choice_ids"], "result.selected_choice_ids")
    known_ids = tuple(choice.id for choice in request.choices)
    if any(item not in known_ids for item in selected):
        _fail("result contains an unknown selected choice id")
    if selected != tuple(item for item in known_ids if item in selected):
        _fail("selected choice ids must follow request order")
    custom_text = data["custom_text"]
    open_text = data["open_text"]
    if custom_text is not None and not isinstance(custom_text, str):
        _fail("result.custom_text must be a string or null")
    if open_text is not None and not isinstance(open_text, str):
        _fail("result.open_text must be a string or null")
    if outcome == "cancelled":
        if selected or custom_text is not None or open_text is not None:
            _fail("cancelled results must contain no selection or text")
    elif outcome == "selected":
        if custom_text is not None or open_text is not None:
            _fail("selected results forbid custom/open text")
        if request.selection_mode in {"binary", "single_select"} and len(selected) != 1:
            _fail("binary/single selected results require exactly one selected id")
        if request.selection_mode == "multi_select" and not cast(
            "int", request.min_selections
        ) <= len(selected) <= cast("int", request.max_selections):
            _fail("multi selected result violates request bounds")
    elif outcome == "custom":
        if (
            selected
            or not isinstance(custom_text, str)
            or not custom_text.strip()
            or open_text is not None
        ):
            _fail("custom result requires only non-empty custom_text")
    elif outcome == "selected_with_custom":
        if (
            not isinstance(custom_text, str)
            or not custom_text.strip()
            or open_text is not None
        ):
            _fail(
                "selected_with_custom requires non-empty custom_text and no open_text"
            )
        total = len(selected) + 1
        if (
            not cast("int", request.min_selections)
            <= total
            <= cast("int", request.max_selections)
        ):
            _fail("multi custom result violates request bounds")
    elif outcome == "submitted":
        if (
            selected
            or custom_text is not None
            or not isinstance(open_text, str)
            or not open_text.strip()
        ):
            _fail("submitted open result requires only non-empty open_text")
    transport = _string(data["transport"], "result.transport")
    tool_name = data["tool_name"]
    if tool_name is not None:
        tool_name = _string(tool_name, "result.tool_name")
    fallback_reasons = _string_tuple(
        data["fallback_reasons"], "result.fallback_reasons"
    )
    if any(reason not in FALLBACK_REASON_ORDER for reason in fallback_reasons):
        _fail("result has unknown fallback reason")
    if fallback_reasons != tuple(
        reason for reason in FALLBACK_REASON_ORDER if reason in fallback_reasons
    ):
        _fail("fallback reasons must be unique and in canonical order")
    if transport == "native":
        if tool_name is None or fallback_reasons:
            _fail("native results require a tool name and empty fallback reasons")
        native_matches = [
            capability
            for capability in contract.harnesses.values()
            if capability.verified_tool == tool_name
            and select_transport(
                contract,
                capability.id,
                request,
                tool_available=True,
                tool_allowed=True,
            ).transport
            == "native"
        ]
        if not native_matches:
            _fail("native result tool is unknown or incompatible with the request")
    elif transport == "sequential_text":
        if not fallback_reasons:
            _fail("sequential results require fallback reasons")
        if tool_name is None and fallback_reasons != ("tool_absent",):
            _fail("null-tool sequential results require exactly tool_absent")
        if (
            fallback_reasons[0] in {"tool_absent", "tool_denied"}
            and len(fallback_reasons) != 1
        ):
            _fail("availability and permission failures short-circuit compatibility")
        if tool_name is not None:
            matching_capability = next(
                (
                    capability
                    for capability in contract.harnesses.values()
                    if capability.verified_tool == tool_name
                ),
                None,
            )
            if matching_capability is None:
                _fail("sequential result names an unverified tool")
            if fallback_reasons[0] not in {"tool_absent", "tool_denied"}:
                expected = select_transport(
                    contract,
                    matching_capability.id,
                    request,
                    tool_available=True,
                    tool_allowed=True,
                )
                if (
                    expected.transport != "sequential_text"
                    or fallback_reasons != expected.fallback_reasons
                ):
                    _fail("sequential fallback reasons do not match tool capability")
    else:
        _fail("result.transport must be native or sequential_text")
    return ChoiceResult(
        request.decision_id,
        request.selection_mode,
        outcome,
        selected,
        cast("str | None", custom_text),
        cast("str | None", open_text),
        transport,
        cast("str | None", tool_name),
        fallback_reasons,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        contract = load_contract(args.contract)
    except ContractError as exc:
        print(f"contract invalid: {exc}", file=sys.stderr)
        return 1
    print(
        f"Flow contract schema {contract.schema_version}: "
        f"{len(contract.commands)} commands, {len(contract.agents)} agents, {len(contract.harnesses)} harnesses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
