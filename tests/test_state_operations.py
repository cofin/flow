from __future__ import annotations

import importlib.util
import json
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "flow-state" / "SKILL.md"
TEMPLATE_PATH = REPO_ROOT / "templates" / "agent" / "skills" / "flow-state" / "SKILL.md"
SOURCE_STATE_REFERENCE_PATH = REPO_ROOT / "skills" / "flow" / "references" / "state.md"
PACKAGED_STATE_REFERENCE_PATH = (
    REPO_ROOT / "skills" / "flow-state" / "references" / "state.md"
)
TEMPLATE_STATE_REFERENCE_PATH = (
    REPO_ROOT
    / "templates"
    / "agent"
    / "skills"
    / "flow-state"
    / "references"
    / "state.md"
)
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


def _yaml_block(path: Path, heading: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    section = content.split(heading, maxsplit=1)[1]
    raw = section.split("```yaml\n", maxsplit=1)[1].split("\n```", maxsplit=1)[0]
    parsed = yaml.safe_load(raw)
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
    if operation == "checkpoint":
        scope = request["payload"].get("scope")
        checkpoint = _yaml_block(
            PACKAGED_STATE_REFERENCE_PATH, "### Operation payload schemas"
        )["checkpoint"].get(scope)
        if checkpoint is None or set(request["payload"]) != set(checkpoint["required"]):
            return "refuse"
        if scope in {"task", "phase"} and not request["payload"].get(
            "verification_evidence"
        ):
            return "refuse"
        if scope == "plan":
            evidence = request["payload"].get("plan_bind_evidence")
            if not isinstance(evidence, dict) or set(evidence) != {
                "evidence_id",
                "commit",
                "inventory",
                "documents",
                "verifier",
            }:
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


def _checkpoint_payload(scope: str) -> dict[str, Any]:
    if scope == "task":
        return {
            "scope": "task",
            "commit": "abc1234",
            "verification_evidence": [
                {"command": "project test command", "result": "passed"}
            ],
            "summary": "task behavior verified",
        }
    if scope == "phase":
        return {
            "scope": "phase",
            "phase_id": "phase-1",
            "affected_task_ids": ["1.1", "1.2"],
            "last_functional_commit": "abc1234",
            "verification_evidence": [
                {"command": "project phase command", "result": "passed"}
            ],
        }
    return {
        "scope": "plan",
        "plan_bind_evidence": {
            "evidence_id": "plan-bind-17",
            "commit": "abc1234",
            "inventory": [
                {"base": "flow_root", "path": "spec.md"},
                {"base": "flow_root", "path": "tasks/1.1.md"},
                {"base": "flow_root", "path": "tasks/1.2.md"},
            ],
            "documents": [],
            "verifier": {
                "actor": "code-reviewer",
                "verified_at": "2026-08-14T18:40:00Z",
                "result": "verified_against_commit",
            },
        },
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


def _load_trace_oracle():
    module_path = REPO_ROOT / "tests" / "test_okf_conformance.py"
    spec = importlib.util.spec_from_file_location("state_trace_oracle", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def trace_oracle():
    return _load_trace_oracle()


def test_state_skill_and_consumer_template_are_identical() -> None:
    assert SKILL_PATH.read_bytes() == TEMPLATE_PATH.read_bytes()


def test_packaged_state_reference_is_self_contained_and_in_sync() -> None:
    source = SOURCE_STATE_REFERENCE_PATH.read_bytes()

    assert PACKAGED_STATE_REFERENCE_PATH.read_bytes() == source
    assert TEMPLATE_STATE_REFERENCE_PATH.read_bytes() == source
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "(references/state.md)" in skill
    assert "../flow/references/state.md" not in skill

    for heading in [
        "### Operation payload schemas",
        "### Operation read/precondition matrix",
        "### Create complete-file fragments",
        "### Event and write-entry shapes",
        "### Terminal validation event schemas",
    ]:
        assert heading in PACKAGED_STATE_REFERENCE_PATH.read_text(encoding="utf-8")


def test_sidecar_result_union_is_closed_and_shared() -> None:
    skill_union = _contract(SKILL_PATH)["result_union"]
    agent_union = _contract(AGENT_PATH, "flow-sidecar-protocol")["result_union"]

    assert agent_union == skill_union
    assert skill_union["keyset"] == [
        "outcome",
        "operation",
        "flow_id",
        "operation_id",
        "plan_revision",
        "plan_commit",
        "state_revision",
        "targets",
        "journal",
        "evidence",
        "refusal",
    ]
    assert set(skill_union["variants"]) == {
        "committed",
        "replayed",
        "rolled_back",
        "recovery_required",
        "contended",
        "refused",
        "status",
    }
    assert skill_union["field_types"] == {
        "operation": "contract_operation_or_null",
        "flow_id": "non_empty_flow_id_or_null",
        "operation_id": "canonical_operation_id_or_null",
        "plan_revision": "integer_at_least_one_or_null",
        "plan_commit": "lowercase_7_to_40_hex_or_null",
        "state_revision": "non_negative_integer_or_null",
        "targets": "unique_sorted_task_id_array",
        "journal": "journal_record_or_null",
        "evidence": "selected_evidence_record_or_null",
        "refusal": "refusal_record_or_null",
    }
    for name, variant in skill_union["variants"].items():
        assert variant["outcome"] == name
        assert set(variant["nullability"]) == set(skill_union["keyset"]) - {"outcome"}


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
            _mutation_request(
                "checkpoint", targets=[], payload=_checkpoint_payload("phase")
            ),
            "accept",
        ),
        (
            _mutation_request(
                "checkpoint",
                targets=["1.1", "1.2"],
                payload=_checkpoint_payload("plan"),
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
        ("checkpoint", ["1.1"], _checkpoint_payload("task")),
        ("checkpoint", [], _checkpoint_payload("phase")),
        ("checkpoint", ["1.1", "1.2"], _checkpoint_payload("plan")),
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


@pytest.mark.parametrize(
    ("targets", "payload"),
    [
        (["1.1"], {"scope": "task"}),
        (
            ["1.1"],
            {
                **_checkpoint_payload("task"),
                "verification_evidence": [],
            },
        ),
        ([], {"scope": "phase"}),
        (
            [],
            {
                **_checkpoint_payload("phase"),
                "verification_evidence": [],
            },
        ),
        (["1.1", "1.2"], {"scope": "plan"}),
        (
            ["1.1", "1.2"],
            {
                "scope": "plan",
                "plan_bind_evidence": {"evidence_id": "incomplete"},
            },
        ),
    ],
)
def test_checkpoint_requires_typed_task_phase_or_plan_evidence(
    targets: list[str], payload: dict[str, Any]
) -> None:
    request = _mutation_request("checkpoint", targets=targets, payload=payload)

    assert _request_outcome(_contract(SKILL_PATH), request) == "refuse"


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


def test_live_claim_trace_is_task_first_spec_last_and_terminal(
    tmp_path: Path, trace_oracle
) -> None:
    oracle = trace_oracle
    interrupted_root = oracle._transaction_root(tmp_path / "before-write")
    interrupted = oracle._journal("20260814T184000Z-agent-claim-1-2-00")

    oracle._event(interrupted, "write_started", 0)
    oracle._write_journal(interrupted_root, interrupted)
    assert oracle.validate.assess_markdown_transactions(interrupted_root) == {
        interrupted["operation_id"]: "sole_recovery_candidate"
    }

    root = oracle._transaction_root(tmp_path / "successful")
    journal = oracle._journal("20260814T184001Z-agent-claim-1-2-00")
    oracle._apply(journal, 0, root)
    oracle._write_journal(root, journal)
    spec = root / journal["flow_root"] / "spec.md"
    assert "current_task: null" in spec.read_text(encoding="utf-8")
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "sole_recovery_candidate"
    }

    oracle._apply(journal, 1, root)
    oracle._validate_forward(journal)
    journal["state"] = "committed"
    oracle._write_journal(root, journal)
    assert oracle.validate.validate_markdown_transactions(root) == []
    assert oracle.validate.assess_markdown_transactions(root) == {}


def test_live_late_zero_contender_is_explained_by_winner(
    tmp_path: Path, trace_oracle
) -> None:
    oracle = trace_oracle
    root = oracle._transaction_root(tmp_path)
    winner = oracle._journal("20260814T184000Z-agent-claim-1-2-00")
    oracle._apply(winner, 0, root)
    oracle._apply(winner, 1, root)
    contender = oracle._journal(
        "20260814T184001Z-agent-claim-1-2-00", state="contended"
    )
    oracle._observe_journals(contender, [winner["operation_id"]])
    oracle._event(
        contender,
        "contended_before_write",
        observed_nonterminal_operation_ids=[winner["operation_id"]],
    )
    oracle._write_journal(root, winner)
    oracle._write_journal(root, contender)

    assert oracle.validate.assess_markdown_transactions(root) == {
        winner["operation_id"]: "sole_recovery_candidate",
        contender["operation_id"]: "superseded_proven_zero",
    }


@pytest.mark.parametrize(
    ("action", "expected"),
    [("finish", "finishable"), ("rollback", "resumable_rollback")],
)
def test_live_recovery_direction_is_immutable(
    tmp_path: Path, trace_oracle, action: str, expected: str
) -> None:
    oracle = trace_oracle
    root = oracle._transaction_root(tmp_path)
    journal = oracle._journal("20260814T184000Z-agent-claim-1-2-00")
    oracle._apply(journal, 0, root)
    oracle._event(journal, "write_started", 1)
    oracle._event(journal, "write_not_applied", 1)
    oracle._select(journal, action)
    if action == "finish":
        oracle._event(journal, "write_started", 1)
    else:
        oracle._restore(journal, 0, confirmed=False, root=root)
    oracle._write_journal(root, journal)
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: expected
    }

    changed = deepcopy(journal)
    oracle._event(
        changed,
        "recovery_selected",
        action="rollback" if action == "finish" else "finish",
        actor="flow-executor",
    )
    oracle._write_journal(root, changed)
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "hard_conflict"
    }


def test_live_custom_root_and_bundle_are_authoritative(
    tmp_path: Path, trace_oracle
) -> None:
    oracle = trace_oracle
    root = oracle._transaction_root(tmp_path)
    configured = root / ".flow-local"
    (root / ".agents").rename(configured)
    (root / ".agents").mkdir()
    (root / ".agents" / "setup-state.json").write_text(
        json.dumps({"root_directory": ".flow-local"}), encoding="utf-8"
    )
    (configured / "bundles").rename(configured / "okf-data")
    (configured / "config.json").write_text(
        json.dumps({"bundles_dir": "okf-data"}), encoding="utf-8"
    )
    journal = oracle._journal("20260814T184000Z-agent-claim-1-2-00")
    journal["configured_root"] = ".flow-local"
    journal["bundle_root"] = ".flow-local/okf-data"
    journal["flow_root"] = ".flow-local/okf-data/specs/demo-flow"
    oracle._write_journal(root, journal, ".flow-local")

    layout = oracle.validate.resolve_okf_layout(root)
    assert layout.configured_root == configured
    assert layout.bundle_root == configured / "okf-data"
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "finishable"
    }


def test_live_archive_deletion_and_per_file_rollback_resume(
    tmp_path: Path, trace_oracle
) -> None:
    oracle = trace_oracle
    root = oracle._transaction_root(tmp_path)
    journal = oracle._journal("20260814T184000Z-agent-archive-spec-00")
    oracle._as_archive(journal, root)
    for index in range(len(journal["ordered_writes"])):
        oracle._apply(journal, index, root)
    oracle._write_journal(root, journal)
    spec = root / journal["flow_root"] / "spec.md"
    assert not spec.exists()
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "sole_recovery_candidate"
    }

    oracle._select(journal, "rollback")
    oracle._restore(journal, len(journal["ordered_writes"]) - 1, root=root)
    oracle._write_journal(root, journal)
    assert spec.exists()
    assert oracle.validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "resumable_rollback"
    }
