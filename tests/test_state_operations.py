from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "flow-state" / "SKILL.md"
TEMPLATE_PATH = REPO_ROOT / "templates" / "agent" / "skills" / "flow-state" / "SKILL.md"
AGENT_PATH = REPO_ROOT / "agents" / "flow-reconciler.md"
SYNC_SKILL_PATH = REPO_ROOT / "skills" / "flow-sync-status" / "SKILL.md"
SYNC_REFERENCE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "sync.md"
STATUS_REFERENCE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "status.md"

OPERATIONS = {
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
}


def _contract(path: Path, name: str = "flow-state-contract") -> dict[str, Any]:
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


def _request_outcome(contract: dict[str, Any], request: dict[str, Any]) -> str:
    operation = request.get("operation")
    if operation not in contract["operations"]:
        return "refuse"
    schema = (
        contract["status_request"]
        if operation == "status"
        else contract["mutation_request"]
    )
    if set(request) != set(schema["required"]):
        return "refuse"
    if operation != "status" and not isinstance(request["targets"], list):
        return "refuse"
    target_mode = request.get("payload", {}).get("variant") or request.get(
        "payload", {}
    ).get("scope")
    target_key = f"{operation}.{target_mode}" if target_mode else operation
    target_rule = contract["target_modes"].get(target_key)
    if target_rule == "empty" and request.get("targets") != []:
        return "refuse"
    if target_rule == "one" and len(request.get("targets", [])) != 1:
        return "refuse"
    if target_rule == "all_tasks_sorted" and request.get("targets") != sorted(
        request.get("targets", [])
    ):
        return "refuse"
    return "accept"


def _mutation_request(
    operation: str, *, targets: list[str], payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "flow_id": "sample-flow",
        "operation": operation,
        "actor": "flow-executor",
        "occurred_at": "2026-08-14T18:40:00Z",
        "expected_plan_revision": 3,
        "expected_plan_commit": None,
        "expected_state_revision": 7,
        "targets": targets,
        "payload": payload,
    }


def _lifecycle_outcome(contract: dict[str, Any], operation: str, state: str) -> str:
    allowed_states: set[str] = set()
    for route, states in contract["lifecycle_guards"].items():
        if route == "active_allowed" and operation in states:
            allowed_states.add("active")
        elif route == "completed_allowed" and operation in states:
            allowed_states.add("completed")
        elif route == "removed_allowed" and operation in states:
            allowed_states.add("removed")
        elif route == operation:
            allowed_states.update(states)
    return "accept" if state in allowed_states else "refuse"


def _load_validator():
    module_path = REPO_ROOT / "tools" / "validate.py"
    spec = importlib.util.spec_from_file_location(
        "state_operation_validate", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_skill_and_consumer_template_are_identical() -> None:
    assert SKILL_PATH.read_bytes() == TEMPLATE_PATH.read_bytes()


def test_request_contract_is_closed_and_supports_every_operation() -> None:
    contract = _contract(SKILL_PATH)

    assert set(contract["operations"]) == OPERATIONS
    assert contract["mutation_request"] == {
        "required": [
            "flow_id",
            "operation",
            "actor",
            "occurred_at",
            "expected_plan_revision",
            "expected_plan_commit",
            "expected_state_revision",
            "targets",
            "payload",
        ],
        "unknown_fields": "refuse",
        "missing_fields": "refuse",
        "identity_mismatch": "refuse_without_writes",
        "payload_schema": "canonical_state_contract",
    }
    assert contract["status_request"]["required"] == [
        "operation",
        "flow_id",
        "task_ids",
    ]
    assert contract["status_request"]["writes"] == "none"


@pytest.mark.parametrize(
    ("input_request", "outcome"),
    [
        (
            _mutation_request(
                "claim", targets=["1.1"], payload={"next_step": "run the worksheet"}
            ),
            "accept",
        ),
        (
            _mutation_request(
                "activate",
                targets=[],
                payload={"approval_evidence": "reviewed", "next_step": "claim 1.1"},
            ),
            "accept",
        ),
        (
            _mutation_request("checkpoint", targets=[], payload={"scope": "phase"}),
            "accept",
        ),
        (
            _mutation_request(
                "checkpoint", targets=["1.1", "1.2"], payload={"scope": "plan"}
            ),
            "accept",
        ),
        (
            _mutation_request("reconcile", targets=[], payload={"mismatches": ["1.1"]}),
            "accept",
        ),
        (
            _mutation_request(
                "claim", targets=[], payload={"next_step": "run the worksheet"}
            ),
            "refuse",
        ),
        (_mutation_request("complete", targets=["1.1"], payload={}), "refuse"),
        (_mutation_request("revise", targets=["1.2", "1.1"], payload={}), "refuse"),
        (
            {
                **_mutation_request("claim", targets=["1.1"], payload={}),
                "implicit_target": "1.1",
            },
            "refuse",
        ),
        (
            {
                key: value
                for key, value in _mutation_request(
                    "claim", targets=["1.1"], payload={}
                ).items()
                if key != "expected_state_revision"
            },
            "refuse",
        ),
        ({"operation": "status", "flow_id": None, "task_ids": []}, "accept"),
        (
            {"operation": "status", "flow_id": None, "task_ids": [], "actor": "agent"},
            "refuse",
        ),
    ],
)
def test_request_scenarios(input_request: dict[str, Any], outcome: str) -> None:
    assert _request_outcome(_contract(SKILL_PATH), input_request) == outcome


@pytest.mark.parametrize(
    ("operation", "targets", "payload"),
    [
        ("create", [], {"variant": "flow"}),
        ("create", ["1.1"], {"variant": "task"}),
        ("activate", [], {}),
        ("claim", ["1.1"], {}),
        ("release", ["1.1"], {}),
        ("note", ["1.1"], {}),
        ("discover", ["1.1"], {}),
        ("block", ["1.1"], {}),
        ("unblock", ["1.1"], {}),
        ("checkpoint", ["1.1"], {"scope": "task"}),
        ("checkpoint", [], {"scope": "phase"}),
        ("checkpoint", ["1.1", "1.2"], {"scope": "plan"}),
        ("close", ["1.1"], {}),
        ("skip", ["1.1"], {}),
        ("reopen", ["1.1"], {}),
        ("revise", ["1.1", "1.2"], {}),
        ("reconcile", [], {}),
        ("complete", [], {}),
        ("archive", [], {}),
        ("recover", [], {}),
    ],
)
def test_every_mutation_has_an_explicit_accepted_target_shape(
    operation: str, targets: list[str], payload: dict[str, Any]
) -> None:
    request = _mutation_request(operation, targets=targets, payload=payload)

    assert _request_outcome(_contract(SKILL_PATH), request) == "accept"


def test_lifecycle_and_identity_routes_are_explicit() -> None:
    contract = _contract(SKILL_PATH)

    assert contract["lifecycle_guards"] == {
        "create.flow": ["absent"],
        "create.task": ["planned", "active"],
        "activate": ["planned"],
        "active_allowed": [
            "claim",
            "release",
            "note.normal",
            "discover",
            "block",
            "unblock",
            "checkpoint.task",
            "checkpoint.phase",
            "close",
            "skip",
            "reopen",
            "reconcile",
            "complete",
        ],
        "checkpoint.plan": ["planned", "active"],
        "revise": ["planned", "active"],
        "archive": ["completed"],
        "status": ["planned", "active", "completed"],
        "recover": ["planned", "active", "completed", "removed"],
        "completed_allowed": [
            "status",
            "recover",
            "archive",
            "note.git_note_attachment",
        ],
        "removed_allowed": ["recover"],
    }
    assert contract["identity_routes"]["task_target"] == [
        "create.task",
        "claim",
        "release",
        "note",
        "discover",
        "block",
        "unblock",
        "checkpoint.task",
        "close",
        "skip",
        "reopen",
    ]
    assert contract["identity_routes"]["all_tasks_then_spec"] == [
        "checkpoint.plan",
        "revise",
    ]
    assert contract["identity_routes"]["spec_only_empty_targets"] == [
        "activate",
        "checkpoint.phase",
        "reconcile",
        "complete",
        "archive",
    ]
    assert contract["identity_routes"]["untouched_tasks"] == "may_lag_state_revision"
    assert contract["snapshot_effects"] == {
        "current_target": "apply_operation_effects",
        "non_current_target": "bounded_summary_only",
        "spec_only": "typed_affected_ids_not_operation_targets",
    }


@pytest.mark.parametrize(
    ("operation", "state", "outcome"),
    [
        ("create.flow", "absent", "accept"),
        ("create.flow", "planned", "refuse"),
        ("create.task", "planned", "accept"),
        ("create.task", "completed", "refuse"),
        ("activate", "planned", "accept"),
        ("activate", "active", "refuse"),
        ("claim", "active", "accept"),
        ("release", "active", "accept"),
        ("note.normal", "active", "accept"),
        ("discover", "active", "accept"),
        ("block", "active", "accept"),
        ("unblock", "active", "accept"),
        ("checkpoint.task", "active", "accept"),
        ("checkpoint.phase", "active", "accept"),
        ("close", "active", "accept"),
        ("skip", "active", "accept"),
        ("reopen", "active", "accept"),
        ("reconcile", "active", "accept"),
        ("complete", "active", "accept"),
        ("checkpoint.plan", "planned", "accept"),
        ("revise", "planned", "accept"),
        ("archive", "completed", "accept"),
        ("note.git_note_attachment", "completed", "accept"),
        ("status", "completed", "accept"),
        ("recover", "removed", "accept"),
        ("claim", "completed", "refuse"),
        ("archive", "active", "refuse"),
    ],
)
def test_lifecycle_guard_scenarios(operation: str, state: str, outcome: str) -> None:
    assert _lifecycle_outcome(_contract(SKILL_PATH), operation, state) == outcome


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        ("all_zero", "supersede_lexicographically_then_retry"),
        ("sole_applied", "supersede_zero_then_require_explicit_recovery"),
        (
            "late_zero_shared_drift_explained",
            "supersede_zero_then_require_explicit_recovery",
        ),
        ("multiple_applied", "hard_stop"),
        ("conflict", "hard_stop"),
    ],
)
def test_joint_arbitration_scenarios(scenario: str, outcome: str) -> None:
    protocol = _contract(AGENT_PATH, "flow-sidecar-protocol")

    assert protocol["arbitration"][scenario] == outcome
    assert protocol["authority"] == "joint_classification_never_scan_order"
    assert protocol["reread_boundaries"] == [
        "after_journal_creation",
        "before_each_directory_or_file_write",
        "after_each_directory_or_file_write",
        "before_validation",
        "before_terminal_state",
    ]


@pytest.mark.parametrize(
    ("live_value", "resolution"),
    [
        ("exact_after", "record_applied_entry_then_write_applied"),
        ("exact_before", "write_not_applied_then_fresh_attempt_allowed"),
        ("other", "refuse"),
    ],
)
def test_unmatched_forward_start_recovery(live_value: str, resolution: str) -> None:
    protocol = _contract(AGENT_PATH, "flow-sidecar-protocol")

    assert protocol["recovery"]["unmatched_forward_start"][live_value] == resolution


def test_recovery_and_fault_boundaries_are_deterministic() -> None:
    protocol = _contract(AGENT_PATH, "flow-sidecar-protocol")

    assert protocol["recovery"]["direction"] == "one_immutable_recovery_selected_event"
    assert protocol["recovery"]["rollback"] == {
        "order": "reverse_applied_prefix",
        "events": ["rollback_started", "rollback_applied"],
        "entries": "namespaced_indexed_duplicate_free",
        "closed_not_applied_attempts": "ignored",
        "confirmed_restores": "live_before",
        "remaining_applied": "live_after",
        "resume": "same_direction_after_every_boundary",
    }
    assert protocol["recovery"]["refuse"] == [
        "changed_direction",
        "duplicate_or_unclosed_start",
        "event_gap_or_reordering",
        "invalid_prefix",
        "unexplained_live_value",
        "journal_or_fragment_tamper",
    ]
    assert protocol["terminal_validation"] == {
        "forward": "validation_recorded_then_reread_then_committed",
        "rollback": "rollback_validated_then_reread_then_rolled_back",
        "interruption": "rerun_exact_checks_without_duplicate_event",
    }
    assert protocol["recovery"]["restore_modes"] == [
        "regular_fragment",
        "archive_file_fragment",
        "created_directory",
    ]
    assert protocol["recovery"]["fault_boundaries"] == [
        "after_each_restore",
        "before_terminal_state",
    ]


def test_interleaving_provenance_and_archive_recovery_are_explicit() -> None:
    protocol = _contract(AGENT_PATH, "flow-sidecar-protocol")

    assert protocol["contention"] == {
        "contender_before_any_applied_mutation": "contended_before_write_then_stop",
        "contender_after_applied_prefix": "recovery_required_then_stop",
    }
    assert protocol["provenance"] == {
        "events": "append_only_gap_free_namespaced_indexed",
        "writes": "applied_and_rolled_back_lists_match_live_prefixes",
        "directories": "shallowest_forward_deepest_rollback",
    }
    assert protocol["archive"] == {
        "inventory": "complete_sorted_regular_utf8_markdown_files_and_directories",
        "deletion": "recorded_files_then_empty_directories",
        "rollback": "directories_shallowest_then_files_reverse_deletion_order",
        "per_file_resume": "exact_before_after_image",
    }


def test_sidecar_scope_and_runtime_are_file_tool_only() -> None:
    contract = _contract(SKILL_PATH)
    protocol = _contract(AGENT_PATH, "flow-sidecar-protocol")

    assert contract["roots"] == {
        "configured": "setup_state_or_default",
        "bundle": "config_or_default",
        "flow": "bundle_specs_flow_id",
        "paths": "namespaced_relative_no_symlink_or_escape",
    }
    assert protocol["scope"] == {
        "allowed": ["flow_markdown", "untracked_markdown_transaction_journal"],
        "forbidden": ["source_files", "tracked_runtime_state", "database", "service"],
        "consumer_execution": "ordinary_file_read_write_edit_tools_only",
    }
    assert protocol["ready_order"] == ["priority", "created_at", "task_id"]
    assert protocol["write_order"] == "directories_then_tasks_sorted_then_spec_last"
    assert protocol["namespaces"] == {
        "configured_root": "transaction_journals",
        "bundle_root": "knowledge_log_archive",
        "flow_root": "spec_tasks",
        "custom_roots": "resolve_from_live_setup_and_config",
        "path_rule": "exactly_one_relative_path_or_glob_no_symlink_or_escape",
    }


def test_sync_and_status_route_through_the_sidecar_contract() -> None:
    sync_contract = _contract(SYNC_REFERENCE_PATH, "flow-sync-contract")
    status_contract = _contract(STATUS_REFERENCE_PATH, "flow-status-contract")
    skill_contract = _contract(SYNC_SKILL_PATH, "flow-sync-status-routing")

    assert sync_contract["operation"] == "reconcile"
    assert sync_contract["targets"] == []
    assert sync_contract["mutation_authority"] == "flow-reconciler_via_flow-state"
    assert status_contract["operation"] == "status"
    assert status_contract["writes"] == "none"
    assert status_contract["ready_order"] == ["priority", "created_at", "task_id"]
    assert skill_contract["sync"] == "typed_reconcile_request"
    assert skill_contract["status"] == "typed_read_only_status_request"
    assert skill_contract["state_mutations"] == "flow-reconciler_via_flow-state"


def test_owned_consumer_surfaces_have_zero_runtime_dependencies(tmp_path: Path) -> None:
    for source in [
        AGENT_PATH,
        SKILL_PATH,
        SYNC_SKILL_PATH,
        SYNC_REFERENCE_PATH,
        STATUS_REFERENCE_PATH,
    ]:
        relative = source.relative_to(REPO_ROOT)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    validate = _load_validator()
    assert validate.validate_installed_runtime_dependencies(tmp_path) == []
