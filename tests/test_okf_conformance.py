"""A canonical OKF v0.2 bundle must pass the validator end-to-end.

Fixture-based: the repo's own .agents/bundles/ is local-only dogfooding and is
never committed, so conformance is proven against a generated bundle instead.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_MODULE_PATH = REPO_ROOT / "tools" / "validate.py"


def _load_validate_module():
    spec = importlib.util.spec_from_file_location("validate_flow", VALIDATE_MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = _load_validate_module()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _yaml_contract_block(text: str, heading: str):
    assert heading in text, heading
    section = text.split(heading, maxsplit=1)[1]
    assert "```yaml\n" in section, heading
    raw_block = section.split("```yaml\n", maxsplit=1)[1].split("\n```", maxsplit=1)[0]
    return validate.yaml.safe_load(raw_block)


def _build_canonical_bundle(root: Path) -> Path:
    bundles = root / ".agents" / "bundles"
    _write(bundles / "index.md", '---\nokf_version: "0.2"\n---\n\n# Bundle\n')
    _write(
        bundles / "log.md",
        "# Bundle Log\n\n## 2026-08-12\n\n**Creation** Initial bundle.\n",
    )
    _write(
        bundles / "knowledge" / "patterns.md",
        "---\ntype: Pattern\ntitle: Patterns\n---\n\n# Patterns\n",
    )
    flow_dir = bundles / "specs" / "demo-flow"
    _write(
        flow_dir / "spec.md",
        """---
type: Spec
flow_id: demo-flow
title: Demo Flow
state: active
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
# Demo Flow

## Implementation Plan

### Phase 1
- [x] Task 1.1: Done task [abc1234]
- [ ] Task 1.2: Open task
""",
    )
    _write(
        flow_dir / "tasks" / "1.1.md",
        """---
type: Task
id: demo-flow:1.1
title: Done task
state: closed
depends_on: []
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: abc1234
---
# Task 1.1

## Notes & Discoveries
- [2026-08-11 12:00] Example note.
""",
    )
    _write(
        flow_dir / "tasks" / "1.2.md",
        """---
type: Task
id: demo-flow:1.2
title: Open task
state: open
depends_on: ["1.1"]
files: []
tests: []
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: null
---
# Task 1.2
""",
    )
    return bundles


def test_canonical_bundle_root_passes(tmp_path: Path) -> None:
    _build_canonical_bundle(tmp_path)
    assert validate.validate_okf_bundle_root(tmp_path) == []


def test_canonical_spec_bundle_passes(tmp_path: Path) -> None:
    bundles = _build_canonical_bundle(tmp_path)
    bundle_dirs = list(validate.iter_okf_bundles(tmp_path))
    assert bundle_dirs == [bundles / "specs" / "demo-flow"]
    violations = validate.validate_okf_bundle(bundle_dirs[0], tmp_path)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_missing_okf_version_is_flagged(tmp_path: Path) -> None:
    _build_canonical_bundle(tmp_path)
    (tmp_path / ".agents" / "bundles" / "index.md").write_text(
        "# Bundle\n", encoding="utf-8"
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any("okf_version" in v.message for v in violations)


def test_workflow_state_in_status_is_flagged(tmp_path: Path) -> None:
    bundles = _build_canonical_bundle(tmp_path)
    task = bundles / "specs" / "demo-flow" / "tasks" / "1.2.md"
    task.write_text(
        task.read_text(encoding="utf-8").replace("state: open", "status: open"),
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle(bundles / "specs" / "demo-flow", tmp_path)
    assert any("OKF lifecycle" in v.message for v in violations)


def test_flow_lifecycle_references_share_closed_state_enums_and_defaults() -> None:
    state_contract = REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    assert state_contract.is_file()

    contract_text = state_contract.read_text(encoding="utf-8")
    enums = _yaml_contract_block(contract_text, "## Contract enums and defaults")
    assert enums == {
        "spec_states": ["planned", "active", "completed"],
        "task_states": ["open", "in_progress", "closed", "blocked", "skipped"],
        "priorities": ["P0", "P1", "P2", "P3", "P4"],
        "default_priority": "P2",
        "recoverable_journal_states": [
            "prepared",
            "task_writes_started",
            "recovery_required",
            "rollback_in_progress",
        ],
        "nonterminal_journal_states": [
            "prepared",
            "task_writes_started",
            "recovery_required",
            "contended",
            "rollback_in_progress",
        ],
        "terminal_journal_states": ["committed", "rolled_back", "superseded"],
    }

    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    spec_schema = agents_text.split("### Spec File Schema (`spec.md`)", maxsplit=1)[
        1
    ].split("### Task File Schema", maxsplit=1)[0]
    spec_example = spec_schema.split("```yaml\n", maxsplit=1)[1].split(
        "\n```", maxsplit=1
    )[0]
    assert "archived" not in spec_example
    assert "`planned`, `active`, `completed`, `archived`" not in spec_schema

    for relative_path in (
        "AGENTS.md",
        "skills/flow/references/plan.md",
        "skills/flow/references/refine.md",
        "skills/flow/references/sync.md",
    ):
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "skills/flow/references/state.md" in text, relative_path


def test_flow_transaction_contract_has_constructible_exact_shapes() -> None:
    contract_text = (
        REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    ).read_text(encoding="utf-8")
    journal = _yaml_contract_block(contract_text, "### Claim journal minimum shape")

    assert set(journal) == {
        "type",
        "version",
        "operation_id",
        "state",
        "applied_writes",
        "rolled_back_writes",
        "events",
        "flow_id",
        "configured_root",
        "bundle_root",
        "flow_root",
        "request",
        "ordered_writes",
        "read_set",
        "fragments",
    }
    assert journal["type"] == "FlowTransaction"
    assert journal["version"] == 1
    assert journal["state"] == "prepared"
    request = journal["request"]
    assert set(request) == {
        "flow_id",
        "operation",
        "actor",
        "occurred_at",
        "expected_plan_revision",
        "expected_plan_commit",
        "expected_state_revision",
        "targets",
        "payload",
    }
    assert request["flow_id"] == journal["flow_id"]
    assert request["operation"] == "claim"
    assert request["targets"] == ["1.1"]
    assert request["payload"] == {
        "next_step": "execute Task 1.1 exactly from its worksheet"
    }
    assert journal["ordered_writes"] == [
        {"base": "flow_root", "path": "tasks/1.1.md"},
        {"base": "flow_root", "path": "spec.md"},
    ]

    read_set = journal["read_set"]
    predicates = {item["predicate"]: item for item in read_set if "predicate" in item}
    assert set(predicates) == {
        "no_other_unresolved_journal",
        "all_dependencies_closed",
        "no_other_in_progress_claim",
    }
    assert predicates["no_other_unresolved_journal"]["directory"] == {
        "base": "configured_root",
        "path": "tasks/transactions",
    }
    assert predicates["all_dependencies_closed"]["target"]["base"] == "flow_root"
    assert predicates["no_other_in_progress_claim"]["scope"] == {
        "base": "flow_root",
        "glob": "tasks/*.md",
    }
    assert any(item.get("path") == "spec.md" and "fields" in item for item in read_set)
    assert any(
        item.get("path") == "tasks/1.1.md" and "fields" in item for item in read_set
    )

    fragments = journal["fragments"]
    assert {fragment["anchor"] for fragment in fragments} == {
        "frontmatter",
        "implementation-plan-task-1.1",
        "continuity-snapshot",
    }
    for fragment in fragments:
        assert fragment["base"] == "flow_root"
        assert set(fragment) == {"base", "path", "anchor", "before", "after"}
        assert set(fragment["before"]) == set(fragment["after"])

    provenance = _yaml_contract_block(contract_text, "### Event and write-entry shapes")
    write_entry = {"write_index": 0, "base": "flow_root", "path": "tasks/1.1.md"}
    assert provenance["applied_writes"] == [write_entry]
    assert provenance["rolled_back_writes"] == [write_entry]
    assert {event["kind"] for event in provenance["events"]} == {
        "prepared",
        "write_started",
        "write_applied",
        "write_not_applied",
        "recovery_selected",
        "rollback_started",
        "rollback_applied",
        "validation_recorded",
        "rollback_validated",
    }
    assert [event["kind"] for event in provenance["contention_events"]] == [
        "prepared",
        "contended_before_write",
    ]

    archive = _yaml_contract_block(
        contract_text, "#### Archive inventory minimum shape"
    )
    assert set(archive) == {
        "target_state_revision",
        "archive_inventory",
        "file_fragments",
    }
    assert archive["archive_inventory"]["base"] == "bundle_root"
    assert archive["archive_inventory"]["files"] == ["spec.md", "tasks/1.1.md"]
    assert all(
        fragment["base"] == "bundle_root" for fragment in archive["file_fragments"]
    )
    deleted = [
        fragment
        for fragment in archive["file_fragments"]
        if not fragment["after"]["exists"]
    ]
    assert {fragment["path"] for fragment in deleted} == {
        "specs/conductor-flow-continuity/spec.md",
        "specs/conductor-flow-continuity/tasks/1.1.md",
    }


def test_flow_operation_payload_and_predicate_contracts_are_complete() -> None:
    contract_text = (
        REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    ).read_text(encoding="utf-8")
    payloads = _yaml_contract_block(contract_text, "### Operation payload schemas")
    assert set(payloads) == {
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
    }
    assert set(payloads["create"]) == {"flow", "task"}
    assert set(payloads["note"]) == {"normal", "git_note_attachment"}
    assert set(payloads["checkpoint"]) == {"task", "phase", "plan"}

    schemas = [
        schema
        for operation in payloads.values()
        for schema in (
            operation.values() if "required" not in operation else [operation]
        )
    ]
    for schema in schemas:
        assert set(schema) == {"required", "optional", "constraints"}
        assert len(schema["required"]) == len(set(schema["required"]))
        assert not set(schema["required"]) & set(schema["optional"])
        assert schema["constraints"]

    status = _yaml_contract_block(contract_text, "### Status request schema")
    assert status["required"] == ["operation", "flow_id", "task_ids"]
    assert status["optional"] == []
    assert any(
        "no operation id or journal" in constraint
        for constraint in status["constraints"]
    )
    assert set(payloads) | {"status"} == {
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

    matrix = _yaml_contract_block(
        contract_text, "### Operation read/precondition matrix"
    )
    operations = matrix["operations"]
    assert set(operations) == {
        "create.flow",
        "create.task",
        "activate",
        "claim",
        "release",
        "note.normal",
        "note.git_note_attachment",
        "discover",
        "block",
        "unblock",
        "checkpoint.task",
        "checkpoint.phase",
        "checkpoint.plan",
        "close",
        "skip",
        "reopen",
        "revise",
        "reconcile",
        "complete",
        "archive",
        "recover",
    }
    defined_predicates = set(matrix["predicate_shapes"])
    assert all(set(required) <= defined_predicates for required in operations.values())

    claim_only_guards = {
        "all_dependencies_closed",
        "no_other_in_progress_claim",
        "sole_current_claim",
    }
    assert claim_only_guards.isdisjoint(operations["note.normal"])
    assert claim_only_guards.isdisjoint(operations["discover"])
    assert claim_only_guards.isdisjoint(operations["block"])
    assert "in_progress_target_is_current" in operations["block"]
    for operation in ("release", "checkpoint.task", "close"):
        assert "sole_current_claim" in operations[operation]
    assert "transaction_directory_clear" not in operations["recover"]
    assert set(operations["recover"]) == {
        "selected_journal_recoverable",
        "journal_arbitration_single_candidate",
        "stage_read_set_matches",
    }

    revise_scope = matrix["predicate_shapes"]["revise_diff_and_adjustments_legal"][
        "scope"
    ]
    assert revise_scope == {
        "paths": [{"base": "flow_root", "path": "spec.md"}],
        "globs": [{"base": "flow_root", "glob": "tasks/*.md"}],
    }
    archive_destinations = matrix["predicate_shapes"]["archive_candidate_exact"][
        "destinations"
    ]
    assert archive_destinations == {
        "paths": [{"base": "bundle_root", "path": "log.md"}],
        "globs": [{"base": "bundle_root", "glob": "knowledge/*.md"}],
    }
    assert all(
        "|" not in entry["glob"]
        for entry in revise_scope["globs"] + archive_destinations["globs"]
    )


def test_flow_create_uses_complete_reversible_file_fragments() -> None:
    contract_text = (
        REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    ).read_text(encoding="utf-8")
    creates = _yaml_contract_block(contract_text, "### Create complete-file fragments")

    flow_create = creates["flow_create"]
    assert flow_create["ordered_directories"] == [
        {"directory_index": 0, "base": "flow_root", "path": "."},
        {"directory_index": 1, "base": "flow_root", "path": "tasks"},
    ]
    assert flow_create["applied_directories"] == []
    assert flow_create["rolled_back_directories"] == []
    assert flow_create["fragments"] == []
    assert flow_create["ordered_writes"] == [{"base": "flow_root", "path": "spec.md"}]
    flow_file = flow_create["file_fragments"][0]
    assert flow_file["before"] == {"exists": False, "content_utf8_lf": None}
    assert flow_file["after"]["exists"] is True
    assert flow_file["after"]["content_utf8_lf"]

    task_create = creates["task_create"]
    assert task_create["ordered_directories"] == []
    assert task_create["applied_directories"] == []
    assert task_create["rolled_back_directories"] == []
    assert task_create["file_fragments"][0]["before"] == {
        "exists": False,
        "content_utf8_lf": None,
    }
    assert task_create["ordered_writes"][-1] == {"base": "flow_root", "path": "spec.md"}
    assert task_create["ordered_writes"][:-1] == sorted(
        task_create["ordered_writes"][:-1], key=lambda item: item["path"]
    )
    assert {fragment["anchor"] for fragment in task_create["fragments"]} == {
        "frontmatter",
        "implementation-plan-chapter-phase-2",
        "continuity-snapshot",
    }
    spec_frontmatter = next(
        fragment
        for fragment in task_create["fragments"]
        if fragment["path"] == "spec.md" and fragment["anchor"] == "frontmatter"
    )
    required_state_identity = {
        "plan_revision",
        "plan_commit",
        "state_revision",
        "last_operation",
        "operation_targets",
        "updated_at",
    }
    assert set(spec_frontmatter["before"]) == required_state_identity
    assert set(spec_frontmatter["after"]) == required_state_identity
    assert any(
        fragment["anchor"] == "continuity-snapshot"
        for fragment in task_create["fragments"]
    )

    recovery = creates["recovery_rules"]
    assert "delete_created_file_when_before_exists_false" in recovery["rollback"]
    assert "restore_applied_writes_in_exact_reverse" in recovery["rollback"]
    assert (
        "rollback_applied_directories_deepest_first_with_provenance"
        in recovery["rollback"]
    )
    assert recovery["terminal_before"] == [
        "all_create_file_fragments_absent",
        "all_anchor_fragments_at_before",
        "all_applied_directories_rolled_back",
    ]

    directory_events = creates["directory_event_schemas"]
    namespaced_event_keys = [
        "sequence",
        "kind",
        "at",
        "directory_index",
        "directory_attempt_index",
        "base",
        "path",
    ]
    assert directory_events["entry_required"] == [
        "directory_index",
        "directory_attempt_index",
        "base",
        "path",
    ]
    for kind in (
        "directory_started",
        "directory_applied",
        "directory_not_applied",
        "directory_rollback_started",
        "directory_rollback_applied",
    ):
        assert directory_events[kind] == namespaced_event_keys
    assert directory_events["optional"] == []
    assert "unknown keys forbidden" in directory_events["constraints"]

    attempt_grammar = creates["directory_attempt_grammar"]
    assert attempt_grammar["closed_not_applied_prefix"].startswith("zero or more")
    assert "no maximum" in attempt_grammar["started_attempt_indices"]
    assert attempt_grammar["max_unmatched_started"] == 1
    assert attempt_grammar["max_applied_attempts"] == 1
    assert attempt_grammar["applied_attempt_must_be_final"] is True
    assert attempt_grammar["start_after_applied"] == "conflict"
    assert attempt_grammar["directory_not_applied_contributes_applied_entry"] is False
    unmatched = attempt_grammar["unmatched_directory_started_at_live_before"]
    assert unmatched == {
        "classification": "unresolved_attempt",
        "zero_applied": False,
        "proven_zero_write": False,
        "supersession": "forbidden",
        "required_action": "append_directory_not_applied",
    }
    closed = attempt_grammar["closed_not_applied_prefix_at_live_before"]
    assert closed["classification"] == "zero_applied"
    assert closed["zero_applied"] is True
    assert closed["proven_zero_eligible"] is True
    assert closed["supersession"] == "allowed"
    assert closed["finish"] == "start_next_gap_free_attempt"
    assert attempt_grammar["two_crashes_apply_then_rollback"] == [
        "directory_started(0)",
        "directory_not_applied(0)",
        "directory_started(1)",
        "directory_not_applied(1)",
        "directory_started(2)",
        "directory_applied(2)",
        "directory_rollback_started(2)",
        "directory_rollback_applied(2)",
    ]
    assert (
        "sole applied directory_attempt_index" in attempt_grammar["rollback_reference"]
    )

    faults = creates["directory_fault_cases"]
    assert faults == {
        "before_directory_started": {
            "live": "absent",
            "classification": "zero_applied",
            "finish": "start_directory",
            "rollback": "terminal_without_directory_write",
            "supersession": "allowed",
        },
        "after_directory_started_before_mkdir": {
            "live": "absent",
            "classification": "unmatched_directory_not_applied",
            "finish": "append_directory_not_applied_then_restart",
            "rollback": "append_directory_not_applied_then_validate",
            "supersession": "forbidden_until_start_closed",
        },
        "after_directory_not_applied": {
            "live": "absent",
            "classification": "zero_applied_closed_start",
            "finish": "restart_directory",
            "rollback": "continue_validation",
            "supersession": "allowed",
        },
        "after_mkdir_before_directory_applied": {
            "live": "empty_directory",
            "classification": "partially_applied_directory",
            "finish": "append_applied_entry_and_directory_applied",
            "rollback": "append_applied_entry_then_remove_with_rollback_events",
            "supersession": "forbidden",
        },
        "after_directory_applied": {
            "live": "directory_with_only_recorded_descendants",
            "classification": "partially_applied_directory",
            "finish": "continue_next_mutation",
            "rollback": "reverse_later_mutations_then_remove_directory",
            "supersession": "forbidden",
        },
        "after_directory_rollback_started_before_rmdir": {
            "live": "empty_directory",
            "classification": "rollback_in_progress",
            "finish": "forbidden",
            "rollback": "retry_rmdir",
            "supersession": "forbidden",
        },
        "after_rmdir_before_directory_rollback_applied": {
            "live": "absent",
            "classification": "rollback_in_progress",
            "finish": "forbidden",
            "rollback": "append_rolled_back_entry_and_directory_rollback_applied",
            "supersession": "forbidden",
        },
        "after_directory_rollback_applied": {
            "live": "absent",
            "classification": "rollback_in_progress",
            "finish": "forbidden",
            "rollback": "continue_next_reverse_or_validate",
            "supersession": "forbidden",
        },
    }


def test_flow_terminal_validation_events_are_strict_and_resumable() -> None:
    contract_text = (
        REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    ).read_text(encoding="utf-8")
    validation = _yaml_contract_block(
        contract_text, "### Terminal validation event schemas"
    )

    assert set(validation) == {
        "check_record",
        "validation_recorded",
        "rollback_validated",
        "validation_invalidated",
        "terminal_rules",
        "validation_fault_cases",
    }
    assert validation["check_record"]["required"] == ["check_id", "result", "observed"]
    event_keys = [
        "sequence",
        "kind",
        "at",
        "actor",
        "direction",
        "validation_attempt_id",
        "checks",
    ]
    assert validation["validation_recorded"]["required"] == event_keys
    assert validation["rollback_validated"]["required"] == event_keys
    assert validation["validation_recorded"]["optional"] == []
    assert validation["rollback_validated"]["optional"] == []
    assert validation["validation_recorded"]["required_check_ids"] == [
        "transaction_arbitration",
        "complete_read_set",
        "ordered_mutations",
        "after_fragments",
        "operation_postconditions",
    ]
    assert validation["rollback_validated"]["required_check_ids"] == [
        "transaction_arbitration",
        "stage_read_set",
        "rolled_back_mutations",
        "before_fragments",
        "rollback_postconditions",
    ]

    provenance = _yaml_contract_block(contract_text, "### Event and write-entry shapes")
    catalogue = {event["kind"]: event for event in provenance["events"]}
    forward_example = catalogue["validation_recorded"]
    rollback_example = catalogue["rollback_validated"]
    assert set(forward_example) == set(event_keys)
    assert set(rollback_example) == set(event_keys)
    assert [check["check_id"] for check in forward_example["checks"]] == validation[
        "validation_recorded"
    ]["required_check_ids"]
    assert [check["check_id"] for check in rollback_example["checks"]] == validation[
        "rollback_validated"
    ]["required_check_ids"]
    assert all(
        set(check) == {"check_id", "result", "observed"}
        for check in forward_example["checks"]
    )
    assert all(
        set(check) == {"check_id", "result", "observed"}
        for check in rollback_example["checks"]
    )
    assert validation["validation_invalidated"]["required"] == [
        "sequence",
        "kind",
        "at",
        "actor",
        "direction",
        "validation_attempt_id",
        "reason",
        "observed_nonterminal_operation_ids",
        "failed_checks",
    ]
    assert validation["validation_invalidated"]["optional"] == []

    terminal_rules = validation["terminal_rules"]
    assert terminal_rules["committed_requires"] == "validation_recorded"
    assert terminal_rules["rolled_back_requires"] == "rollback_validated"
    assert terminal_rules["append_only"] is True
    assert terminal_rules["duplicate_event"] == "forbidden"
    assert terminal_rules["latest_validation_must_be"] == [
        "uninvalidated",
        "final_event",
        "exact_live_checks_passed",
    ]
    assert "apply only terminal journal state" in terminal_rules["resume_after_event"]
    assert (
        "do not duplicate invalidation" in terminal_rules["resume_after_invalidation"]
    )
    assert "all v00..v99" in terminal_rules["attempt_exhaustion"]
    assert (
        "without a new event or tracked write" in terminal_rules["attempt_exhaustion"]
    )
    assert "never wrap or reuse" in terminal_rules["attempt_exhaustion"]
    assert terminal_rules["terminal_without_event"] == "conflict"
    assert terminal_rules["event_after_terminal"] == "forbidden"

    faults = validation["validation_fault_cases"]
    assert faults == {
        "after_validation_before_terminal_clean": {
            "live": "exact_validated_state",
            "action": "apply_terminal_state_only",
            "append_event": "none",
        },
        "after_validation_before_terminal_contender": {
            "live": "contender_present",
            "action": "append_validation_invalidated_then_arbitrate",
            "terminal": "forbidden",
        },
        "after_validation_before_terminal_drift": {
            "live": "reread_mismatch",
            "action": "append_validation_invalidated_then_recover",
            "terminal": "forbidden",
        },
        "after_invalidation_before_recovery_state": {
            "live": "invalidation_is_final_event",
            "action": "retain_invalidation_and_enter_recovery",
            "duplicate_invalidation": "forbidden",
        },
        "after_recovery_before_revalidation": {
            "live": "stable_nonterminal_state",
            "action": "append_fresh_validation_attempt",
            "terminal": "forbidden",
        },
        "after_fresh_validation_before_terminal": {
            "live": "exact_revalidated_state",
            "action": "apply_terminal_state_only",
            "append_event": "none",
        },
        "after_terminal": {
            "live": "terminal_state",
            "action": "none",
            "append_event": "forbidden",
        },
    }


def test_plan_bind_uses_typed_live_markdown_evidence_without_runtime_inspection() -> (
    None
):
    contract_text = (
        REPO_ROOT / "skills" / "flow" / "references" / "state.md"
    ).read_text(encoding="utf-8")
    evidence = _yaml_contract_block(contract_text, "### Plan-bind evidence schema")

    assert evidence["required"] == [
        "evidence_id",
        "commit",
        "inventory",
        "documents",
        "verifier",
    ]
    assert evidence["optional"] == []
    assert evidence["inventory"]["item_schema"]["required"] == ["base", "path"]
    assert evidence["documents"]["item_schema"]["required"] == [
        "base",
        "path",
        "plan_revision",
        "plan_commit",
        "content_utf8_lf",
    ]
    assert evidence["verifier"]["required"] == ["actor", "verified_at", "result"]
    initial = evidence["initial_bind"]
    assert "complete exact journal request" in initial["request_identity"]
    assert initial["journal_file_fragment_schema"]["required"] == [
        "base",
        "path",
        "before",
        "after",
    ]
    assert initial["journal_file_fragment_schema"]["before_after_required"] == [
        "exists",
        "content_utf8_lf",
    ]
    assert (
        "before content equals evidence document" in initial["journal_file_fragments"]
    )
    assert initial["after_images"]["every_target_frontmatter_keys"] == [
        "plan_commit",
        "state_revision",
        "last_operation",
        "operation_targets",
        "updated_at",
    ]
    assert initial["after_images"]["spec_body_anchors"] == ["verification_evidence"]
    assert initial["terminal_result_projection"]["required"] == [
        "operation_id",
        "state",
        "flow_id",
        "targets",
        "plan_revision",
        "plan_commit",
        "state_revision",
    ]

    assert evidence["replay"] == {
        "replay_key": "evidence_id",
        "lookup": "exactly one terminal committed plan-bind journal with this flow/evidence_id",
        "exact_request_match": "current complete request equals original journal request recursively with identical keysets and values",
        "exact_after_image_match": "inventory and every live target equal journal file_fragments after exists/content image",
        "success": "return_original_terminal_result_without_journal_or_revision",
        "same_key_different_request_or_payload": "conflict_without_writes",
        "missing_or_noncommitted_original_journal": "refuse_without_writes",
        "live_after_image_or_inventory_drift": "refuse_without_writes",
        "pre_bind_documents_on_replay": "never_revalidated",
        "different_evidence_after_plan_commit_bound": "refuse_without_writes",
        "failed_or_missing_verifier_result": "refuse_without_writes",
    }

    payloads = _yaml_contract_block(contract_text, "### Operation payload schemas")
    assert payloads["checkpoint"]["plan"]["required"] == ["scope", "plan_bind_evidence"]
    matrix = _yaml_contract_block(
        contract_text, "### Operation read/precondition matrix"
    )
    assert "exact_plan_tree_at_commit" not in matrix["predicate_shapes"]
    assert (
        matrix["operations"]["checkpoint.plan"][-1] == "plan_bind_evidence_matches_live"
    )
    plan_bind_predicate = matrix["predicate_shapes"]["plan_bind_evidence_matches_live"]
    assert plan_bind_predicate["paths"] == [{"base": "flow_root", "path": "spec.md"}]
    assert plan_bind_predicate["globs"] == [{"base": "flow_root", "glob": "tasks/*.md"}]
    assert plan_bind_predicate["runtime_inspection"] == "forbidden"


def test_agents_sync_contract_has_no_consumer_python_helper() -> None:
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    task_mandate = agents_text.split("## The Task-First Mandate", maxsplit=1)[1].split(
        "## Auto-Activation", maxsplit=1
    )[0]
    assert "python3 tools/sync.py" not in task_mandate
    assert "/flow:sync" in task_mandate
    assert "skills/flow/references/state.md" in task_mandate
