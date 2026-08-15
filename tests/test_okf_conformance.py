"""A canonical OKF v0.2 bundle must pass the validator end-to-end.

Fixture-based: the repo's own .agents/bundles/ is local-only dogfooding and is
never committed, so conformance is proven against a generated bundle instead.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

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
    shutil.copytree(
        REPO_ROOT / "tests" / "fixtures" / "okf" / "continuity",
        root,
        dirs_exist_ok=True,
    )
    return root / ".agents" / "bundles"


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
        task.read_text(encoding="utf-8").replace(
            "state: in_progress", "status: in_progress"
        ),
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle(bundles / "specs" / "demo-flow", tmp_path)
    assert any("OKF lifecycle" in v.message for v in violations)


def test_okf_concept_document_with_tags_and_provenance_passes(
    tmp_path: Path,
) -> None:
    """A concept document with tags, sources, resource, and description passes."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "orders.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
status: stable
stale_after: 2026-12-31
sources:
  - id: bq-schema
    resource: https://console.cloud.google.com/bigquery
    author: team:data-eng
    usage_count: 5000
    last_modified: 2026-05-30
---

# Customer Orders Schema
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert violations == [], "\n".join(str(v) for v in violations)


def test_okf_concept_document_missing_type_is_flagged(tmp_path: Path) -> None:
    """A non-reserved document without type field is flagged."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "bad.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
title: Missing Type Doc
tags: [test]
---

# Bad Document
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any(
        "missing required OKF frontmatter field: 'type'" in v.message
        for v in violations
    )


def test_okf_concept_document_invalid_tags_type_is_flagged(
    tmp_path: Path,
) -> None:
    """A concept document where tags is not a list is flagged."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "bad_tags.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
type: Pattern
title: Bad Tags
tags: "not-a-list"
---

# Bad Tags
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any("OKF field 'tags' must be a list" in v.message for v in violations)


def test_okf_concept_document_invalid_tags_items_flagged(
    tmp_path: Path,
) -> None:
    """A concept document where tags contains non-string items is flagged."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "bad_tags_items.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
type: Pattern
title: Bad Tag Items
tags: [123, 456]
---

# Bad Tag Items
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any(
        "OKF field 'tags' items must be strings" in v.message for v in violations
    )


def test_okf_concept_document_workflow_state_in_status_flagged(
    tmp_path: Path,
) -> None:
    """A concept document storing workflow state in status is flagged."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "bad_status.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
type: Guide
title: Bad Status
status: in_progress
---

# Bad Status
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert any("OKF lifecycle" in v.message for v in violations)


def test_okf_concept_document_unknown_type_and_custom_fields_tolerated(
    tmp_path: Path,
) -> None:
    """Unknown type values and custom producer fields are tolerated per OKF spec."""
    bundles = _build_canonical_bundle(tmp_path)
    concept_file = bundles / "knowledge" / "custom.md"
    concept_file.parent.mkdir(parents=True, exist_ok=True)
    concept_file.write_text(
        """---
type: CustomDomainConcept
title: Domain Entity
tags: [custom, domain]
confidence: 0.99
custom_owner: team-alpha
computation_target: bigquery
---

# Custom Concept
""",
        encoding="utf-8",
    )
    violations = validate.validate_okf_bundle_root(tmp_path)
    assert violations == [], "\n".join(str(v) for v in violations)


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
        "globs": [{"base": "bundle_root", "glob": "knowledge/**/*.md"}],
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


TRANSACTION_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "okf" / "continuity"


def _transaction_root(tmp_path: Path) -> Path:
    shutil.copytree(TRANSACTION_FIXTURE, tmp_path, dirs_exist_ok=True)
    task = tmp_path / ".agents/bundles/specs/demo-flow/tasks/1.2.md"
    task_text = task.read_text(encoding="utf-8")
    task.write_text(
        task_text.replace("state: in_progress", "state: open", 1)
        .replace("claimed_by: flow-executor", "claimed_by: null", 1)
        .replace("claimed_at: 2026-08-14T12:00:00Z", "claimed_at: null", 1)
        .replace(
            "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
            "last_operation: 20260814T115900Z-flow-reconciler-reconcile-spec-00",
            1,
        )
        .replace('operation_targets: ["1.2"]', "operation_targets: []", 1),
        encoding="utf-8",
    )
    spec = tmp_path / ".agents/bundles/specs/demo-flow/spec.md"
    spec_text = spec.read_text(encoding="utf-8")
    spec.write_text(
        spec_text.replace('current_task: "1.2"', "current_task: null", 1)
        .replace(
            "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
            "last_operation: 20260814T115900Z-flow-reconciler-reconcile-spec-00",
            1,
        )
        .replace('operation_targets: ["1.2"]', "operation_targets: []", 1)
        .replace("- [~] Task 1.2", "- [ ] Task 1.2", 1)
        .replace("Task `1.2`, claimed by `flow-executor`", "none", 1)
        .replace("execute the first numbered worksheet step", "claim Task 1.2", 1)
        .replace(
            "last_operation: 20260814T120000Z-flow-executor-claim-1-2-00",
            "last_operation: 20260814T115900Z-flow-reconciler-reconcile-spec-00",
            1,
        )
        .replace('operation_targets: ["1.2"]', "operation_targets: []", 1),
        encoding="utf-8",
    )
    return tmp_path


def _journal(operation_id: str, *, state: str = "prepared") -> dict:
    return {
        "type": "FlowTransaction",
        "version": 1,
        "operation_id": operation_id,
        "state": state,
        "applied_writes": [],
        "rolled_back_writes": [],
        "events": [
            {
                "sequence": 0,
                "kind": "prepared",
                "at": "2026-08-14T12:00:00Z",
                "observed_nonterminal_operation_ids": [],
            }
        ],
        "flow_id": "demo-flow",
        "configured_root": ".agents",
        "bundle_root": ".agents/bundles",
        "flow_root": ".agents/bundles/specs/demo-flow",
        "request": {
            "flow_id": "demo-flow",
            "operation": "claim",
            "actor": "flow-executor",
            "occurred_at": "2026-08-14T12:00:00Z",
            "expected_plan_revision": 2,
            "expected_plan_commit": None,
            "expected_state_revision": 3,
            "targets": ["1.2"],
            "payload": {"next_step": "execute the first numbered worksheet step"},
        },
        "ordered_writes": [
            {"base": "flow_root", "path": "tasks/1.2.md"},
            {"base": "flow_root", "path": "spec.md"},
        ],
        "read_set": [
            {
                "predicate": "no_other_unresolved_journal",
                "directory": {
                    "base": "configured_root",
                    "path": "tasks/transactions",
                },
                "excluding_operation_id": operation_id,
                "observed_operation_ids": [],
            },
            {
                "base": "flow_root",
                "path": "spec.md",
                "fields": {
                    "state": "active",
                    "state_revision": 3,
                    "current_task": None,
                    "plan_revision": 2,
                    "plan_commit": None,
                    "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                    "operation_targets": [],
                },
            },
            {
                "base": "flow_root",
                "path": "tasks/1.2.md",
                "fields": {
                    "id": "demo-flow:1.2",
                    "state": "open",
                    "state_revision": 3,
                    "plan_revision": 2,
                    "plan_commit": None,
                    "claimed_by": None,
                    "claimed_at": None,
                    "blocked_reason": None,
                    "unblock_condition": None,
                    "commit": None,
                },
            },
            {
                "predicate": "all_dependencies_closed",
                "target": {"base": "flow_root", "path": "tasks/1.2.md"},
                "dependency_paths": [{"base": "flow_root", "path": "tasks/1.1.md"}],
                "observed_states": {"1.1": "closed"},
            },
            {
                "predicate": "no_other_in_progress_claim",
                "scope": {"base": "flow_root", "glob": "tasks/*.md"},
                "excluding": {"base": "flow_root", "path": "tasks/1.2.md"},
                "observed_task_ids": [],
            },
        ],
        "fragments": [
            {
                "base": "flow_root",
                "path": "tasks/1.2.md",
                "anchor": "frontmatter",
                "before": {
                    "state": "open",
                    "state_revision": 3,
                    "claimed_by": None,
                    "claimed_at": None,
                    "blocked_reason": None,
                    "unblock_condition": None,
                    "next_step": "execute the first numbered worksheet step",
                    "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                    "operation_targets": [],
                    "updated_at": "2026-08-14T12:00:00Z",
                },
                "after": {
                    "state": "in_progress",
                    "state_revision": 4,
                    "claimed_by": "flow-executor",
                    "claimed_at": "2026-08-14T12:00:00Z",
                    "blocked_reason": None,
                    "unblock_condition": None,
                    "next_step": "execute the first numbered worksheet step",
                    "last_operation": operation_id,
                    "operation_targets": ["1.2"],
                    "updated_at": "2026-08-14T12:00:00Z",
                },
            },
            {
                "base": "flow_root",
                "path": "spec.md",
                "anchor": "frontmatter",
                "before": {
                    "state_revision": 3,
                    "current_task": None,
                    "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                    "operation_targets": [],
                    "updated_at": "2026-08-14T12:00:00Z",
                },
                "after": {
                    "state_revision": 4,
                    "current_task": "1.2",
                    "last_operation": operation_id,
                    "operation_targets": ["1.2"],
                    "updated_at": "2026-08-14T12:00:00Z",
                },
            },
            {
                "base": "flow_root",
                "path": "spec.md",
                "anchor": "implementation-plan-task-1.2",
                "before": {"checklist_marker": "[ ]", "commit_suffix": None},
                "after": {"checklist_marker": "[~]", "commit_suffix": None},
            },
            {
                "base": "flow_root",
                "path": "spec.md",
                "anchor": "continuity-snapshot",
                "before": {
                    "current_task_claim": None,
                    "last_verified_checkpoint": "task:1.1@abc1234",
                    "next_exact_step": "claim Task 1.2",
                    "state_identity": {
                        "revision": 3,
                        "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                        "operation_targets": [],
                    },
                },
                "after": {
                    "current_task_claim": {
                        "task": "1.2",
                        "claimed_by": "flow-executor",
                    },
                    "last_verified_checkpoint": "task:1.1@abc1234",
                    "next_exact_step": "execute the first numbered worksheet step",
                    "state_identity": {
                        "revision": 4,
                        "last_operation": operation_id,
                        "operation_targets": ["1.2"],
                    },
                },
            },
        ],
    }


def _event(journal: dict, kind: str, write_index: int | None = None, **extra) -> None:
    item = {
        "sequence": len(journal["events"]),
        "kind": kind,
        "at": "2026-08-14T12:00:01Z",
        **extra,
    }
    if write_index is not None:
        item.update(journal["ordered_writes"][write_index])
        item["write_index"] = write_index
    journal["events"].append(item)


def _observe_journals(journal: dict, operation_ids: list[str]) -> None:
    journal["events"][0]["observed_nonterminal_operation_ids"] = operation_ids
    journal["read_set"][0]["observed_operation_ids"] = operation_ids


def _set_write_image(root: Path, journal: dict, write_index: int, image: str) -> None:
    write = journal["ordered_writes"][write_index]
    bases = {
        "configured_root": root / journal["configured_root"],
        "bundle_root": root / journal["bundle_root"],
        "flow_root": root / journal["flow_root"],
    }
    target = bases[write["base"]] / write["path"]
    for fragment in journal.get("file_fragments", []):
        if (fragment["base"], fragment["path"]) != (
            write["base"],
            write["path"],
        ):
            continue
        file_image = fragment[image]
        if file_image["exists"]:
            _write(target, file_image["content_utf8_lf"])
        elif target.exists():
            target.unlink()
    for fragment in journal["fragments"]:
        if (fragment["base"], fragment["path"]) != (
            write["base"],
            write["path"],
        ):
            continue
        values = fragment[image]
        text = target.read_text(encoding="utf-8")
        if fragment["anchor"] == "frontmatter":
            _, raw, body = text.split("---\n", 2)
            frontmatter = validate.yaml.safe_load(raw)
            frontmatter.update(values)
            text = (
                "---\n"
                + validate.yaml.safe_dump(frontmatter, sort_keys=False)
                + "---\n"
                + body
            )
        elif fragment["anchor"].startswith("implementation-plan-task-"):
            short_id = fragment["anchor"].removeprefix("implementation-plan-task-")
            suffix = (
                ""
                if values["commit_suffix"] is None
                else f" [{values['commit_suffix']}]"
            )
            text = re.sub(
                rf"(?m)^- \[[ ~x!-]\] Task {re.escape(short_id)}: ([^\n\[]+?)(?: \[[^\]]+\])?$",
                rf"- {values['checklist_marker']} Task {short_id}: \1{suffix}",
                text,
            )
        elif fragment["anchor"].startswith("implementation-plan-chapter-"):
            chapter_id = fragment["anchor"].removeprefix("implementation-plan-chapter-")
            heading = next(
                match
                for match in re.finditer(r"(?m)^(#{2,6})\s+(.+?)\s*$", text)
                if re.sub(r"[^a-z0-9]+", "-", match.group(2).lower()).strip("-")
                == chapter_id
            )
            level = len(heading.group(1))
            following = re.search(rf"(?m)^#{{2,{level}}}\s+.+$", text[heading.end() :])
            end = heading.end() + following.start() if following else len(text)
            section = text[heading.end() : end]
            section = re.sub(
                r"(?m)^- \[[ ~x!-]\] Task [^\n]+\n?",
                "",
                section,
            ).rstrip()
            checklist = "\n".join(values["checklist_items"])
            replacement = f"\n\n{checklist}"
            if section:
                replacement += f"\n\n{section.lstrip()}"
            text = text[: heading.end()] + replacement + text[end:]
        elif fragment["anchor"] == "continuity-snapshot":
            claim = values["current_task_claim"]
            claim_text = (
                "none"
                if claim is None
                else f"Task `{claim['task']}`, claimed by `{claim['claimed_by']}`"
            )
            checkpoint = values["last_verified_checkpoint"]
            state = values["state_identity"]
            replacements = {
                "Current task/claim": claim_text,
                "Last verified checkpoint": "none"
                if checkpoint is None
                else f"`{checkpoint}`",
                "Next exact step": values["next_exact_step"],
                "State identity": (
                    f"revision `{state['revision']}`; `last_operation: {state['last_operation']}`; "
                    f"`operation_targets: {json.dumps(state['operation_targets'])}`"
                ),
            }
            for label, rendered in replacements.items():
                text = re.sub(
                    rf"(?m)^- \*\*{re.escape(label)}:\*\* .+$",
                    f"- **{label}:** {rendered}",
                    text,
                )
        target.write_text(text, encoding="utf-8")


def _apply(journal: dict, write_index: int, root: Path | None = None) -> None:
    _event(journal, "write_started", write_index)
    if journal["state"] == "prepared":
        journal["state"] = "task_writes_started"
    if root is not None:
        _set_write_image(root, journal, write_index, "after")
    journal["applied_writes"].append(
        {"write_index": write_index, **journal["ordered_writes"][write_index]}
    )
    _event(journal, "write_applied", write_index)


def _select(journal: dict, action: str) -> None:
    _event(journal, "recovery_selected", action=action, actor="flow-executor")
    journal["state"] = (
        "rollback_in_progress" if action == "rollback" else "recovery_required"
    )


def _as_archive(journal: dict, root: Path | None = None) -> None:
    journal["request"]["operation"] = "archive"
    journal["request"]["targets"] = []
    journal["request"]["payload"] = {
        "knowledge_destinations": ["knowledge/workflow.md"],
        "synthesized_edits": [],
        "log_entry": {
            "date": "2026-08-14",
            "flow_id": journal["flow_id"],
            "outcome": "archived",
            "final_commit": "abc1234",
        },
        "notes_incorporation": [],
        "archive_candidate_manifest": {
            "base_commit": "abc1234",
            "head_commit": "def5678",
            "inventory": [],
            "file_fragments": [],
        },
        "quality_report": {
            "reviewer": "quality-reviewer",
            "base_commit": "abc1234",
            "head_commit": "def5678",
            "debloat_source": "packaged_skill",
            "findings": [],
        },
        "waivers": [],
    }
    journal["target_state_revision"] = 4
    journal["file_fragments"] = []
    journal["read_set"] = [
        {
            "predicate": "no_other_unresolved_journal",
            "directory": {"base": "configured_root", "path": "tasks/transactions"},
            "excluding_operation_id": journal["operation_id"],
            "observed_operation_ids": [],
        },
        {
            "base": "flow_root",
            "path": "spec.md",
            "fields": {
                "state": "completed" if root is not None else "active",
                "state_revision": 3,
                "current_task": None,
                "plan_revision": 2,
                "plan_commit": None,
                "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                "operation_targets": [],
            },
        },
        {
            "predicate": "archive_candidate_exact",
            "root": {"base": "flow_root", "glob": "**/*"},
            "destinations": {
                "paths": [{"base": "bundle_root", "path": "log.md"}],
                "globs": [{"base": "bundle_root", "glob": "knowledge/*.md"}],
            },
            "manifest": journal["request"]["payload"]["archive_candidate_manifest"],
        },
        {
            "predicate": "archive_evidence_valid",
            "candidate": journal["request"]["payload"]["archive_candidate_manifest"],
            "quality": journal["request"]["payload"]["quality_report"],
            "waivers": [],
        },
    ]
    if root is not None:
        bundle = root / journal["bundle_root"]
        spec = root / journal["flow_root"] / "spec.md"
        spec.write_text(
            spec.read_text(encoding="utf-8")
            .replace("state: active", "state: completed", 1)
            .replace("(`active`)", "(`completed`)", 1),
            encoding="utf-8",
        )
        knowledge = bundle / "knowledge/workflow.md"
        _write(knowledge, "# Workflow\n\nBefore.\n")
        journal["ordered_writes"] = [
            {"base": "bundle_root", "path": "knowledge/workflow.md"},
            {"base": "bundle_root", "path": "log.md"},
            {"base": "bundle_root", "path": "specs/demo-flow/tasks/1.1.md"},
            {"base": "bundle_root", "path": "specs/demo-flow/tasks/1.2.md"},
            {"base": "bundle_root", "path": "specs/demo-flow/spec.md"},
        ]
        journal["fragments"] = []
        for item in journal["ordered_writes"]:
            bases = {
                "bundle_root": bundle,
                "flow_root": root / journal["flow_root"],
            }
            target = bases[item["base"]] / item["path"]
            before = target.read_text(encoding="utf-8")
            after = (
                before + "\nReviewed.\n"
                if item["path"].startswith("knowledge/")
                else before + "\n- 2026-08-14: archived demo-flow\n"
                if item["path"] == "log.md"
                else None
            )
            journal["file_fragments"].append(
                {
                    **item,
                    "before": {"exists": True, "content_utf8_lf": before},
                    "after": {"exists": after is not None, "content_utf8_lf": after},
                }
            )
        journal["archive_inventory"] = {
            "base": "bundle_root",
            "root": "specs/demo-flow",
            "directories": [".", "tasks"],
            "files": ["spec.md", "tasks/1.1.md", "tasks/1.2.md"],
        }


def _restore(
    journal: dict,
    write_index: int,
    *,
    confirmed: bool = True,
    root: Path | None = None,
) -> None:
    _event(journal, "rollback_started", write_index)
    if root is not None:
        _set_write_image(root, journal, write_index, "before")
    if confirmed:
        journal["rolled_back_writes"].append(
            {"write_index": write_index, **journal["ordered_writes"][write_index]}
        )
        _event(journal, "rollback_applied", write_index)


def _validate_rollback(journal: dict) -> None:
    _event(
        journal,
        "rollback_validated",
        actor="flow-executor",
        direction="rollback",
        validation_attempt_id=f"{journal['operation_id']}:rollback:v00",
        checks=[
            {"check_id": check_id, "result": "passed", "observed": "exact"}
            for check_id in (
                "transaction_arbitration",
                "stage_read_set",
                "rolled_back_mutations",
                "before_fragments",
                "rollback_postconditions",
            )
        ],
    )


def _validate_forward(journal: dict, suffix: int = 0) -> None:
    _event(
        journal,
        "validation_recorded",
        actor="flow-executor",
        direction="forward",
        validation_attempt_id=f"{journal['operation_id']}:forward:v{suffix:02d}",
        checks=[
            {"check_id": check_id, "result": "passed", "observed": "exact"}
            for check_id in (
                "transaction_arbitration",
                "complete_read_set",
                "ordered_mutations",
                "after_fragments",
                "operation_postconditions",
            )
        ],
    )


def _write_journal(root: Path, journal: dict, configured_root: str = ".agents") -> Path:
    path = (
        root
        / configured_root
        / "tasks"
        / "transactions"
        / journal["operation_id"]
        / "journal.md"
    )
    _write(
        path,
        "---\n" + validate.yaml.safe_dump(journal, sort_keys=False) + "---\n",
    )
    return path


def test_late_contender_is_proven_zero_after_winner_spec_last(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    winner = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(winner, 0, root)
    _apply(winner, 1, root)
    contender = _journal("20260814T120001Z-agent-claim-1-2-00", state="contended")
    _observe_journals(contender, [winner["operation_id"]])
    _event(
        contender,
        "contended_before_write",
        observed_nonterminal_operation_ids=[winner["operation_id"]],
    )
    _write_journal(root, winner)
    _write_journal(root, contender)
    assert validate.assess_markdown_transactions(root) == {
        winner["operation_id"]: "sole_recovery_candidate",
        contender["operation_id"]: "superseded_proven_zero",
    }


def test_all_zero_journals_supersede_and_retry(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journals = [_journal(f"20260814T12000{i}Z-agent-claim-1-2-00") for i in range(2)]
    for journal in journals:
        _write_journal(root, journal)
    assert set(validate.assess_markdown_transactions(root).values()) == {
        "superseded_proven_zero"
    }


def test_one_applied_journal_is_sole_recovery_candidate(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    applied = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(applied, 0, root)
    zero = _journal("20260814T120001Z-agent-claim-1-2-00")
    _observe_journals(zero, [applied["operation_id"]])
    _write_journal(root, applied)
    _write_journal(root, zero)
    assert validate.assess_markdown_transactions(root)[applied["operation_id"]] == (
        "sole_recovery_candidate"
    )


def test_two_applied_journals_hard_conflict(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journals = [_journal(f"20260814T12000{i}Z-agent-claim-1-2-00") for i in range(2)]
    for journal in journals:
        _apply(journal, 0, root)
        _write_journal(root, journal)
    assert set(validate.assess_markdown_transactions(root).values()) == {
        "hard_conflict"
    }


@pytest.mark.parametrize("restored_count", [0, 1, 2, 3])
def test_regular_rollback_resumes_after_each_restore(
    tmp_path: Path, restored_count: int
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    _select(journal, "rollback")
    for index in [1, 0][:restored_count]:
        _restore(journal, index, root=root)
    if restored_count == 3:
        _validate_rollback(journal)
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "resumable_rollback"
    )


@pytest.mark.parametrize("restored_count", [0, 1, 2, 3, 4, 5, 6])
def test_archive_rollback_resumes_after_each_restore(
    tmp_path: Path, restored_count: int
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-archive-spec-00")
    _as_archive(journal, root)
    for index in range(len(journal["ordered_writes"])):
        _apply(journal, index, root)
    _select(journal, "rollback")
    for index in reversed(range(len(journal["ordered_writes"]))):
        if len(journal["rolled_back_writes"]) >= restored_count:
            break
        _restore(journal, index, root=root)
    if restored_count == len(journal["ordered_writes"]) + 1:
        _validate_rollback(journal)
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "resumable_rollback"
    )


def _assert_unmatched_forward_start_before_image_recovery(
    tmp_path: Path, action: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _event(journal, "write_started", 1)
    _event(journal, "write_not_applied", 1)
    _select(journal, action)
    if action == "finish":
        _event(journal, "write_started", 1)
    else:
        _restore(journal, 0, confirmed=False, root=root)
    _write_journal(root, journal)
    expected = "finishable" if action == "finish" else "resumable_rollback"
    assert (
        validate.assess_markdown_transactions(root)[journal["operation_id"]] == expected
    )


def test_unmatched_forward_start_before_image_can_finish(tmp_path: Path) -> None:
    _assert_unmatched_forward_start_before_image_recovery(tmp_path, "finish")


def test_unmatched_forward_start_before_image_can_rollback(tmp_path: Path) -> None:
    _assert_unmatched_forward_start_before_image_recovery(tmp_path, "rollback")


@pytest.mark.parametrize(
    "corrupt",
    ["direction", "duplicate_start", "event_order", "rollback_prefix"],
)
def test_transaction_provenance_corruption_is_conflict(
    tmp_path: Path, corrupt: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _select(journal, "rollback")
    if corrupt == "direction":
        _event(journal, "recovery_selected", action="finish", actor="flow-executor")
    elif corrupt == "duplicate_start":
        _event(journal, "write_started", 1)
        _event(journal, "write_started", 1)
    elif corrupt == "event_order":
        journal["events"][1]["sequence"] = 9
    else:
        journal["rolled_back_writes"] = [
            {"write_index": 1, **journal["ordered_writes"][1]}
        ]
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "hard_conflict"
    )


def test_journal_rejects_illegal_transition_and_payload_keyset(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    journal["request"]["payload"]["unexpected"] = True
    journal["fragments"][0]["before"]["state"] = "blocked"
    journal["fragments"][0]["after"]["state"] = "closed"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "exact operation keyset" in messages
    assert "illegal claim transition blocked -> closed" in messages


def test_quality_evidence_requires_exact_range_and_debloat_source() -> None:
    report = {
        "reviewer": "quality-reviewer",
        "base_commit": "abc1234",
        "head_commit": "def5678",
        "debloat_source": "packaged_skill",
        "findings": [],
    }
    assert validate._quality_report(report, "abc1234", "def5678")
    assert not validate._quality_report(
        {key: value for key, value in report.items() if key != "debloat_source"},
        "abc1234",
        "def5678",
    )
    assert not validate._quality_report(report, "abc1234", "feedface")
    assert not validate._range_bound_command_evidence(
        [
            {
                "command": "uv run pytest",
                "result": "passed",
                "base_commit": "abc1234",
                "head_commit": "feedface",
            }
        ],
        "abc1234",
        "def5678",
    )
    finding = {
        "finding_id": "Q-1",
        "severity": "Critical",
        "file": "tools/validate.py",
        "symbol": "quality",
        "evidence": "missing gate",
        "preserved_invariant": "quality must be fresh",
        "remediation_target": "validator",
        "reverification": "pytest",
    }
    report["findings"] = [finding]
    assert validate._quality_report(report, "abc1234", "def5678")
    invalid_range_report = dict(report, base_commit="not-a-sha")
    assert not validate._quality_report(invalid_range_report, "not-a-sha", "def5678")
    assert not validate._quality_waivers([], "abc1234", "def5678", report["findings"])
    assert not validate._quality_waivers(
        [
            {
                "finding_id": "Q-2",
                "rationale": "x",
                "approval_text": "x",
                "approved_at": "2026-08-14T00:00:00Z",
                "compensating_evidence": "x",
                "base_commit": "abc1234",
                "head_commit": "def5678",
            }
        ],
        "abc1234",
        "def5678",
        report["findings"],
    )


@pytest.mark.parametrize(
    "location",
    [
        "fragment",
        "ordered_write",
        "read_target",
        "dependency_path",
        "transaction_directory",
        "inventory",
        "glob_scope",
    ],
)
@pytest.mark.parametrize("bad_base", [None, "wrong_root", "flow_root/../../escape"])
def test_journal_rejects_missing_wrong_or_escaping_bases(
    tmp_path: Path, location: str, bad_base: str | None
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    journal["archive_inventory"] = {
        "base": "bundle_root",
        "root": "specs/demo-flow",
        "directories": ["."],
        "files": ["spec.md"],
    }
    records = {
        "fragment": journal["fragments"][0],
        "ordered_write": journal["ordered_writes"][0],
        "read_target": journal["read_set"][3]["target"],
        "dependency_path": journal["read_set"][3]["dependency_paths"][0],
        "transaction_directory": journal["read_set"][0]["directory"],
        "inventory": journal["archive_inventory"],
        "glob_scope": journal["read_set"][4]["scope"],
    }
    record = records[location]
    if bad_base is None:
        record.pop("base")
    elif bad_base == "flow_root/../../escape":
        record["base"] = "flow_root"
        record[
            "path" if "path" in record else "glob" if "glob" in record else "root"
        ] = "../../escape"
    else:
        record["base"] = bad_base
    path = _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert path.relative_to(root).as_posix() in "\n".join(
        item.path.relative_to(root).as_posix()
        for item in validate.validate_markdown_transactions(root)
    )
    assert "base" in messages or "escapes" in messages


def test_custom_root_nondefault_bundle_and_deleted_archive_are_discovered(
    tmp_path: Path,
) -> None:
    configured = tmp_path / ".flow-local"
    configured.mkdir()
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"root_directory": ".flow-local"}), encoding="utf-8"
    )
    (configured / "config.json").write_text(
        json.dumps({"bundles_dir": "okf-data"}), encoding="utf-8"
    )
    (configured / "okf-data" / "specs").mkdir(parents=True)
    journal = _journal("20260814T120000Z-agent-archive-spec-00")
    _as_archive(journal)
    journal["flow_id"] = "deleted-flow"
    journal["configured_root"] = ".flow-local"
    journal["bundle_root"] = ".flow-local/okf-data"
    journal["flow_root"] = ".flow-local/okf-data/specs/deleted-flow"
    journal["request"]["flow_id"] = "deleted-flow"
    journal["request"]["payload"]["log_entry"]["flow_id"] = "deleted-flow"
    journal["read_set"][1]["fields"]["state"] = "completed"
    journal["ordered_writes"] = [
        {"base": "bundle_root", "path": "log.md"},
        {"base": "bundle_root", "path": "specs/deleted-flow/spec.md"},
    ]
    journal["fragments"] = []
    journal["file_fragments"] = [
        {
            "base": "bundle_root",
            "path": "log.md",
            "before": {"exists": False, "content_utf8_lf": None},
            "after": {
                "exists": True,
                "content_utf8_lf": "# Log\n\nArchived deleted-flow.\n",
            },
        },
        {
            "base": "bundle_root",
            "path": "specs/deleted-flow/spec.md",
            "before": {"exists": True, "content_utf8_lf": "---\ntype: Spec\n---\n"},
            "after": {"exists": False, "content_utf8_lf": None},
        },
    ]
    journal["archive_inventory"] = {
        "base": "bundle_root",
        "root": "specs/deleted-flow",
        "directories": ["."],
        "files": ["spec.md"],
    }
    _apply(journal, 0, tmp_path)
    _apply(journal, 1, tmp_path)
    journal["state"] = "recovery_required"
    _write_journal(tmp_path, journal, ".flow-local")
    layout = validate.resolve_okf_layout(tmp_path)
    assert layout.configured_root == configured
    assert layout.bundle_root == configured / "okf-data"
    assert list(validate.iter_okf_bundles(tmp_path)) == []
    assert validate.assess_markdown_transactions(tmp_path) == {
        journal["operation_id"]: "recoverable_deleted_archive"
    }


def test_recorded_applied_write_requires_exact_live_after_image(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0)
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "hard_conflict"
    }


def test_live_after_prefix_is_the_sole_recovery_candidate(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "sole_recovery_candidate"
    }


def test_unexplained_live_fragment_drift_is_a_hard_conflict(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    task = root / journal["flow_root"] / "tasks/1.2.md"
    task.write_text(
        task.read_text(encoding="utf-8").replace(
            "state_revision: 3", "state_revision: 99", 1
        ),
        encoding="utf-8",
    )
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "hard_conflict"
    }


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing_predicate", "read_set predicates"),
        ("target_path_disagreement", "targets/path"),
        ("fragment_unknown_key", "fragment keyset"),
        ("wrong_write_order", "task-before-spec"),
        ("committed_without_validation", "validation_recorded"),
        ("rolled_back_without_validation", "rollback_validated"),
        ("expected_identity_mismatch", "expected plan/state identity"),
    ],
)
def test_journal_exact_grammar_rejects_semantic_gaps(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    if mutation == "missing_predicate":
        journal["read_set"] = [
            item
            for item in journal["read_set"]
            if item.get("predicate") != "all_dependencies_closed"
        ]
    elif mutation == "target_path_disagreement":
        journal["request"]["targets"] = ["1.1"]
    elif mutation == "fragment_unknown_key":
        journal["fragments"][0]["summary"] = "not exact"
    elif mutation == "wrong_write_order":
        journal["ordered_writes"].reverse()
    elif mutation == "committed_without_validation":
        journal["state"] = "committed"
    elif mutation == "expected_identity_mismatch":
        journal["request"]["expected_state_revision"] = 99
    else:
        journal["state"] = "rolled_back"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert expected in messages


def test_journal_rejects_invalid_nested_payload_values_and_lifecycle(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-close-1-2-00")
    journal["request"]["operation"] = "close"
    journal["request"]["payload"] = {
        "commit": "NOT-A-SHA",
        "verification_evidence": [{"command": "pytest", "unexpected": "passed"}],
        "acceptance_criteria_checked": [],
    }
    journal["read_set"] = journal["read_set"][:3] + [
        {
            "predicate": "sole_current_claim",
            "spec": {"base": "flow_root", "path": "spec.md"},
            "target": {"base": "flow_root", "path": "tasks/1.2.md"},
            "claimant": "flow-executor",
        },
        {
            "predicate": "verification_bound_to_commit",
            "target": {"base": "flow_root", "path": "tasks/1.2.md"},
            "commit": "NOT-A-SHA",
            "evidence": journal["request"]["payload"]["verification_evidence"],
        },
        {
            "predicate": "acceptance_criteria_satisfied",
            "target": {"base": "flow_root", "path": "tasks/1.2.md"},
            "checked_ids": [],
        },
    ]
    journal["read_set"][1]["fields"]["state"] = "completed"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "commit" in messages
    assert "verification_evidence" in messages
    assert "acceptance_criteria_checked" in messages
    assert "lifecycle" in messages


def test_plan_bind_requires_typed_evidence_inventory_and_complete_images(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-checkpoint-plan-00")
    journal["request"]["operation"] = "checkpoint"
    journal["request"]["targets"] = ["1.1", "1.2"]
    journal["request"]["payload"] = {
        "scope": "plan",
        "plan_bind_evidence": {"evidence_id": "bind-1"},
    }
    journal["read_set"] = journal["read_set"][:2] + [
        {
            "predicate": "all_task_identities",
            "scope": {"base": "flow_root", "glob": "tasks/*.md"},
            "fields": [],
        },
        {
            "predicate": "plan_bind_evidence_matches_live",
            "paths": [{"base": "flow_root", "path": "spec.md"}],
            "globs": [{"base": "flow_root", "glob": "tasks/*.md"}],
            "evidence": journal["request"]["payload"]["plan_bind_evidence"],
            "runtime_inspection": "forbidden",
        },
    ]
    journal["file_fragments"] = []
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "plan_bind_evidence must use the exact keyset" in messages
    assert "complete file_fragments must agree with ordered_writes" in messages


def test_create_requires_complete_files_and_directory_provenance(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-create-task-00")
    journal["request"].update(
        {
            "operation": "create",
            "targets": ["1.3"],
            "payload": {
                "variant": "task",
                "short_id": "1.3",
                "chapter_id": "phase-1",
                "worksheet": {
                    "Objective": "Create the next task",
                    "Context": "Use the current plan",
                    "Steps": ["Write the task"],
                    "Verification": ["validate bundle"],
                    "Acceptance Criteria": ["Task is executable"],
                },
                "priority": "P2",
                "verification_strategy": "static_validation",
                "depends_on": [],
                "files": [],
                "tests": [],
            },
        }
    )
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "file_fragments" in messages
    assert "ordered_directories" in messages


def _task_create_journal(root: Path) -> dict:
    operation_id = "20260814T120000Z-agent-create-1-3-00"
    journal = _journal(operation_id)
    spec_path = root / journal["flow_root"] / "spec.md"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "## Implementation Plan\n\n",
            "## Implementation Plan\n\n### Phase 1\n\n",
            1,
        ),
        encoding="utf-8",
    )
    journal["request"].update(
        {
            "operation": "create",
            "targets": ["1.3"],
            "payload": {
                "variant": "task",
                "short_id": "1.3",
                "chapter_id": "phase-1",
                "worksheet": {
                    "Objective": "Add a concrete third task.",
                    "Context": "Edit src/third.py using current patterns.",
                    "Steps": [
                        "1. Add the failing scenario.",
                        "2. Implement the behavior.",
                    ],
                    "Verification": [
                        "Run pytest tests/test_third.py and require pass."
                    ],
                    "Acceptance Criteria": ["The third behavior is observable."],
                },
                "priority": "P2",
                "verification_strategy": "behavior_tdd",
                "depends_on": ["1.2"],
                "files": ["src/third.py"],
                "tests": ["tests/test_third.py"],
            },
        }
    )
    target_fields = [
        "id",
        "state",
        "state_revision",
        "plan_revision",
        "plan_commit",
        "claimed_by",
        "claimed_at",
        "blocked_reason",
        "unblock_condition",
        "commit",
    ]
    journal["read_set"] = journal["read_set"][:2] + [
        {
            "predicate": "all_task_identities",
            "scope": {"base": "flow_root", "glob": "tasks/*.md"},
            "fields": target_fields,
        },
        {
            "predicate": "target_absent",
            "target": {"base": "flow_root", "path": "tasks/1.3.md"},
        },
        {
            "predicate": "dependencies_exist_and_acyclic",
            "target": {"base": "flow_root", "path": "tasks/1.3.md"},
            "dependency_paths": [{"base": "flow_root", "path": "tasks/1.2.md"}],
            "observed_states": {"1.2": "open"},
        },
    ]
    task_content = (
        "---\n"
        "type: Task\n"
        "id: demo-flow:1.3\n"
        "title: Add third behavior\n"
        "state: open\n"
        "priority: P2\n"
        "verification_strategy: behavior_tdd\n"
        'depends_on: ["1.2"]\n'
        "files: [src/third.py]\n"
        "tests: [tests/test_third.py]\n"
        "plan_revision: 3\n"
        "plan_commit: null\n"
        "state_revision: 4\n"
        "claimed_by: null\nclaimed_at: null\nblocked_reason: null\n"
        "unblock_condition: null\nnext_step: null\n"
        f"last_operation: {operation_id}\n"
        'operation_targets: ["1.3"]\n'
        "last_verified_at: null\nlast_verified_commit: null\n"
        "verification_evidence: null\ncreated_at: 2026-08-14T12:00:00Z\n"
        "updated_at: 2026-08-14T12:00:00Z\ncommit: null\n---\n"
        "# Task 1.3: Add third behavior\n\n"
        "## Objective\nAdd a concrete third task.\n\n"
        "## Context\nEdit `src/third.py`.\n\n"
        "## Steps\n1. Add the failing scenario.\n2. Implement it.\n\n"
        "## Verification\nRun `pytest tests/test_third.py` and require pass.\n\n"
        "## Acceptance Criteria\n- The third behavior is observable.\n\n"
        "## Notes & Discoveries\n"
    )
    journal["ordered_directories"] = []
    journal["applied_directories"] = []
    journal["rolled_back_directories"] = []
    journal["file_fragments"] = [
        {
            "base": "flow_root",
            "path": "tasks/1.3.md",
            "before": {"exists": False, "content_utf8_lf": None},
            "after": {"exists": True, "content_utf8_lf": task_content},
        }
    ]
    journal["fragments"] = [
        {
            "base": "flow_root",
            "path": f"tasks/{short_id}.md",
            "anchor": "frontmatter",
            "before": {"plan_revision": 2, "plan_commit": None},
            "after": {"plan_revision": 3, "plan_commit": None},
        }
        for short_id in ("1.1", "1.2")
    ] + [
        {
            "base": "flow_root",
            "path": "spec.md",
            "anchor": "frontmatter",
            "before": {
                "plan_revision": 2,
                "plan_commit": None,
                "state_revision": 3,
                "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                "operation_targets": [],
                "updated_at": "2026-08-14T12:00:00Z",
            },
            "after": {
                "plan_revision": 3,
                "plan_commit": None,
                "state_revision": 4,
                "last_operation": operation_id,
                "operation_targets": ["1.3"],
                "updated_at": "2026-08-14T12:00:00Z",
            },
        },
        {
            "base": "flow_root",
            "path": "spec.md",
            "anchor": "implementation-plan-chapter-phase-1",
            "before": {
                "checklist_items": [
                    "- [x] Task 1.1: Foundation [abc1234]",
                    "- [ ] Task 1.2: Continue work",
                ]
            },
            "after": {
                "checklist_items": [
                    "- [x] Task 1.1: Foundation [abc1234]",
                    "- [ ] Task 1.2: Continue work",
                    "- [ ] Task 1.3: Add third behavior",
                ]
            },
        },
        {
            "base": "flow_root",
            "path": "spec.md",
            "anchor": "continuity-snapshot",
            "before": {
                "current_task_claim": None,
                "last_verified_checkpoint": "task:1.1@abc1234",
                "next_exact_step": "claim Task 1.2",
                "state_identity": {
                    "revision": 3,
                    "last_operation": "20260814T115900Z-flow-reconciler-reconcile-spec-00",
                    "operation_targets": [],
                },
            },
            "after": {
                "current_task_claim": None,
                "last_verified_checkpoint": "task:1.1@abc1234",
                "next_exact_step": "claim Task 1.2",
                "state_identity": {
                    "revision": 4,
                    "last_operation": operation_id,
                    "operation_targets": ["1.3"],
                },
            },
        },
    ]
    journal["ordered_writes"] = [
        {"base": "flow_root", "path": f"tasks/{short_id}.md"}
        for short_id in ("1.1", "1.2", "1.3")
    ] + [{"base": "flow_root", "path": "spec.md"}]
    return journal


def test_task_create_golden_mixes_existing_anchors_and_new_complete_file(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _task_create_journal(root)
    _write_journal(root, journal)
    assert validate.validate_markdown_transactions(root) == []
    assert validate.assess_markdown_transactions(root) == {
        journal["operation_id"]: "finishable"
    }


@pytest.mark.parametrize(
    "mutation", ["existing_complete_file", "new_task_anchor", "wrong_chapter_anchor"]
)
def test_task_create_rejects_incorrect_fragment_roles(
    tmp_path: Path, mutation: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _task_create_journal(root)
    if mutation == "existing_complete_file":
        journal["file_fragments"].append(
            {
                "base": "flow_root",
                "path": "tasks/1.1.md",
                "before": {"exists": False, "content_utf8_lf": None},
                "after": {"exists": True, "content_utf8_lf": "invalid"},
            }
        )
    elif mutation == "new_task_anchor":
        journal["file_fragments"] = []
        journal["fragments"].insert(
            2,
            {
                "base": "flow_root",
                "path": "tasks/1.3.md",
                "anchor": "frontmatter",
                "before": {"plan_revision": 2, "plan_commit": None},
                "after": {"plan_revision": 3, "plan_commit": None},
            },
        )
    else:
        chapter = next(
            item
            for item in journal["fragments"]
            if item["anchor"].startswith("implementation-plan-chapter-")
        )
        chapter["anchor"] = "implementation-plan-task-1.3"
    _write_journal(root, journal)
    assert "create.task" in "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )


def _create_directory_journal() -> dict:
    journal = _journal("20260814T120000Z-agent-create-flow-00")
    journal["request"] = {
        "flow_id": "new-flow",
        "operation": "create",
        "actor": "flow-executor",
        "occurred_at": "2026-08-14T12:00:00Z",
        "expected_plan_revision": None,
        "expected_plan_commit": None,
        "expected_state_revision": None,
        "targets": [],
        "payload": {"variant": "flow", "title": "Demo", "description": "Demo flow"},
    }
    journal["flow_id"] = "new-flow"
    journal["flow_root"] = ".agents/bundles/specs/new-flow"
    journal["read_set"] = [
        {
            "predicate": "no_other_unresolved_journal",
            "directory": {"base": "configured_root", "path": "tasks/transactions"},
            "excluding_operation_id": journal["operation_id"],
            "observed_operation_ids": [],
        },
        {
            "predicate": "flow_absent",
            "target": {"base": "bundle_root", "path": "specs/new-flow"},
        },
    ]
    journal["ordered_directories"] = [
        {"directory_index": 0, "base": "flow_root", "path": "."},
        {"directory_index": 1, "base": "flow_root", "path": "tasks"},
    ]
    journal["applied_directories"] = []
    journal["rolled_back_directories"] = []
    journal["file_fragments"] = [
        {
            "base": "flow_root",
            "path": "spec.md",
            "before": {"exists": False, "content_utf8_lf": None},
            "after": {
                "exists": True,
                "content_utf8_lf": (
                    "---\n"
                    "type: Spec\n"
                    "flow_id: new-flow\n"
                    "title: Demo\n"
                    "state: planned\n"
                    "plan_revision: 1\n"
                    "plan_commit: null\n"
                    "state_revision: 0\n"
                    "current_task: null\n"
                    "last_operation: null\n"
                    "operation_targets: []\n"
                    "last_verified_checkpoint: null\n"
                    "created_at: 2026-08-14T12:00:00Z\n"
                    "updated_at: 2026-08-14T12:00:00Z\n"
                    "description: Demo flow\n"
                    "---\n"
                    "# Demo\n\n"
                    "## Implementation Plan\n\n"
                    "## Continuity Snapshot\n\n"
                    "- **Lifecycle:** `new-flow` (`planned`)\n"
                    "- **Current task/claim:** none\n"
                    "- **Last verified checkpoint:** none\n"
                    "- **Decisions:** none\n"
                    "- **Recent discoveries:** none\n"
                    "- **Blockers:** none\n"
                    "- **Next exact step:** refine the first task\n"
                    "- **Plan identity:** revision `1`; `plan_commit: null`\n"
                    "- **State identity:** revision `0`; `last_operation: null`; "
                    "`operation_targets: []`\n"
                    "- **Relevant paths:** `skills/flow/references/state.md`\n"
                ),
            },
        }
    ]
    journal["ordered_writes"] = [{"base": "flow_root", "path": "spec.md"}]
    journal["fragments"] = []
    return journal


@pytest.mark.parametrize("terminal_state", ["committed", "rolled_back"])
def test_terminal_journal_requires_exact_live_terminal_image(
    tmp_path: Path, terminal_state: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    if terminal_state == "committed":
        _validate_forward(journal)
    else:
        _select(journal, "rollback")
        _restore(journal, 1, root=root)
        _restore(journal, 0, root=root)
        _validate_rollback(journal)
    journal["state"] = terminal_state
    _set_write_image(
        root,
        journal,
        0,
        "before" if terminal_state == "committed" else "after",
    )
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "terminal live image" in messages


def test_terminal_journal_rechecks_dependency_predicates_after_validation(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    _validate_forward(journal)
    journal["state"] = "committed"
    dependency = root / journal["flow_root"] / "tasks/1.1.md"
    dependency.write_text(
        dependency.read_text(encoding="utf-8").replace(
            "state: closed", "state: open", 1
        ),
        encoding="utf-8",
    )
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "terminal semantic read_set" in messages


@pytest.mark.parametrize("stage", ["prepared", "applied"])
def test_archive_inventory_rejects_unrecorded_live_markdown(
    tmp_path: Path, stage: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-archive-spec-00")
    _as_archive(journal, root)
    surprise = root / journal["flow_root"] / "tasks/surprise.md"
    _write(surprise, "---\ntype: Task\n---\n# Surprise\n")
    if stage == "applied":
        _apply(journal, 0, root)
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "archive inventory omits live path" in messages


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("null_payload", "next_step"),
        ("false_dependency", "all_dependencies_closed"),
        ("incomplete_identity", "target_identity"),
    ],
)
def test_journal_rejects_invalid_payload_values_and_predicate_bodies(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    if mutation == "null_payload":
        journal["request"]["payload"]["next_step"] = None
    elif mutation == "false_dependency":
        journal["read_set"][3]["observed_states"] = {"1.1": "open"}
    else:
        journal["read_set"][2]["fields"].pop("state_revision")
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert expected in messages


@pytest.mark.parametrize("observation", [["ghost-operation"], []])
def test_prepared_observation_must_be_complete_and_consistent(
    tmp_path: Path, observation: list[str]
) -> None:
    root = _transaction_root(tmp_path)
    first = _journal("20260814T120000Z-agent-claim-1-2-00")
    second = _journal("20260814T120001Z-agent-note-1-2-00")
    second["request"]["operation"] = "note"
    second["request"]["payload"] = {"category": "finding", "text": "found"}
    second["read_set"] = second["read_set"][:3]
    if observation:
        first["events"][0]["observed_nonterminal_operation_ids"] = observation
    else:
        second["events"][0]["observed_nonterminal_operation_ids"] = [
            first["operation_id"]
        ]
        second["read_set"][0]["observed_operation_ids"] = []
    _write_journal(root, first)
    _write_journal(root, second)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "prepared observation" in messages


@pytest.mark.parametrize(
    "mutation", ["missing_tasks_directory", "duplicate_directory", "incomplete_spec"]
)
def test_create_flow_requires_complete_contents_effects_and_unique_directories(
    tmp_path: Path, mutation: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _create_directory_journal()
    if mutation == "missing_tasks_directory":
        journal["ordered_directories"] = journal["ordered_directories"][:1]
    elif mutation == "duplicate_directory":
        journal["ordered_directories"].append(
            {"directory_index": 2, "base": "flow_root", "path": "tasks"}
        )
    else:
        journal["file_fragments"][0]["after"]["content_utf8_lf"] = (
            "---\ntype: Spec\nflow_id: new-flow\n---\n# Demo\n"
        )
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "create.flow" in messages


def test_namespaced_record_rejects_both_path_and_glob(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    journal["read_set"][4]["scope"]["path"] = "tasks/1.2.md"
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "exactly one of path or glob" in messages


def test_configured_root_symlink_is_rejected(tmp_path: Path) -> None:
    real_root = tmp_path / ".flow-real"
    real_root.mkdir()
    (tmp_path / ".flow-link").symlink_to(real_root, target_is_directory=True)
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "setup-state.json").write_text(
        json.dumps({"root_directory": ".flow-link"}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="symlink"):
        validate.resolve_okf_layout(tmp_path)


def test_glob_rejects_wildcard_matched_symlink_ancestor(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    flow_root = root / journal["flow_root"]
    (flow_root / "linked").symlink_to(flow_root / "tasks", target_is_directory=True)
    journal["read_set"][4]["scope"]["glob"] = "*/1.2.md"
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "symlink" in messages


def test_directory_attempt_chain_allows_retries_then_apply_and_rollback(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _create_directory_journal()
    for attempt in range(2):
        _event(
            journal,
            "directory_started",
            directory_index=0,
            directory_attempt_index=attempt,
            base="flow_root",
            path=".",
        )
        _event(
            journal,
            "directory_not_applied",
            directory_index=0,
            directory_attempt_index=attempt,
            base="flow_root",
            path=".",
        )
    _event(
        journal,
        "directory_started",
        directory_index=0,
        directory_attempt_index=2,
        base="flow_root",
        path=".",
    )
    (root / journal["flow_root"]).mkdir(parents=True)
    _event(
        journal,
        "directory_applied",
        directory_index=0,
        directory_attempt_index=2,
        base="flow_root",
        path=".",
    )
    journal["applied_directories"] = [
        {
            "directory_index": 0,
            "directory_attempt_index": 2,
            "base": "flow_root",
            "path": ".",
        }
    ]
    journal["state"] = "task_writes_started"
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "sole_recovery_candidate"
    )


@pytest.mark.parametrize("live_created", [False, True])
def test_unmatched_directory_start_is_recoverable_but_not_supersedable(
    tmp_path: Path, live_created: bool
) -> None:
    root = _transaction_root(tmp_path)
    journal = _create_directory_journal()
    _event(
        journal,
        "directory_started",
        directory_index=0,
        directory_attempt_index=0,
        base="flow_root",
        path=".",
    )
    if live_created:
        (root / journal["flow_root"]).mkdir(parents=True)
    contender = _journal("20260814T120001Z-agent-note-1-2-00")
    _observe_journals(contender, [journal["operation_id"]])
    _write_journal(root, journal)
    _write_journal(root, contender)
    results = validate.assess_markdown_transactions(root)
    assert results[journal["operation_id"]] == "sole_recovery_candidate"
    assert results[contender["operation_id"]] == "superseded_proven_zero"


def test_closed_directory_not_applied_retries_are_proven_zero(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journals = []
    for sequence in range(2):
        journal = _create_directory_journal()
        journal["operation_id"] = f"20260814T12000{sequence}Z-agent-create-flow-00"
        journal["request"]["actor"] = f"agent-{sequence}"
        journal["read_set"][0]["excluding_operation_id"] = journal["operation_id"]
        for attempt in range(2):
            _event(
                journal,
                "directory_started",
                directory_index=0,
                directory_attempt_index=attempt,
                base="flow_root",
                path=".",
            )
            _event(
                journal,
                "directory_not_applied",
                directory_index=0,
                directory_attempt_index=attempt,
                base="flow_root",
                path=".",
            )
        journals.append(journal)
        _write_journal(root, journal)
    assert set(validate.assess_markdown_transactions(root).values()) == {
        "superseded_proven_zero"
    }


@pytest.mark.parametrize(
    "mutation", ["child_before_root", "root_before_child_rollback", "surprise_file"]
)
def test_created_directory_provenance_rejects_order_and_descendant_drift(
    tmp_path: Path, mutation: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _create_directory_journal()

    def apply_directory(index: int) -> None:
        entry = {
            "directory_index": index,
            "directory_attempt_index": 0,
            "base": "flow_root",
            "path": journal["ordered_directories"][index]["path"],
        }
        _event(journal, "directory_started", **entry)
        (root / journal["flow_root"] / entry["path"]).mkdir(parents=True, exist_ok=True)
        journal["applied_directories"].append(entry)
        _event(journal, "directory_applied", **entry)

    if mutation == "child_before_root":
        apply_directory(1)
    else:
        apply_directory(0)
        apply_directory(1)
        if mutation == "root_before_child_rollback":
            _select(journal, "rollback")
            root_entry = journal["applied_directories"][0]
            _event(journal, "directory_rollback_started", **root_entry)
        else:
            _write(root / journal["flow_root"] / "surprise.txt", "unrecorded\n")
    _write_journal(root, journal)

    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "hard_conflict"
    )


@pytest.mark.parametrize("rollback_stage", ["started", "removed", "confirmed"])
def test_applied_directory_rollback_is_resumable(
    tmp_path: Path, rollback_stage: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _create_directory_journal()
    entry = {
        "directory_index": 0,
        "directory_attempt_index": 0,
        "base": "flow_root",
        "path": ".",
    }
    _event(journal, "directory_started", **entry)
    (root / journal["flow_root"]).mkdir(parents=True)
    journal["applied_directories"] = [entry]
    _event(journal, "directory_applied", **entry)
    _select(journal, "rollback")
    _event(journal, "directory_rollback_started", **entry)
    if rollback_stage in {"removed", "confirmed"}:
        (root / journal["flow_root"]).rmdir()
    if rollback_stage == "confirmed":
        journal["rolled_back_directories"] = [entry]
        _event(journal, "directory_rollback_applied", **entry)
    _write_journal(root, journal)
    assert validate.assess_markdown_transactions(root)[journal["operation_id"]] == (
        "resumable_rollback"
    )


def test_terminal_validation_event_requires_exact_checks_and_fresh_ids(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _event(
        journal,
        "validation_recorded",
        actor="flow-executor",
        direction="forward",
        validation_attempt_id=f"{journal['operation_id']}:forward:v00",
        checks=[
            {"check_id": "transaction_arbitration", "result": "passed", "observed": []}
        ],
    )
    journal["state"] = "committed"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "exact validation checks" in messages


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        (
            ".opencode/plugins/flow.js",
            'import { spawn } from "child_process"; spawn("python3", ["state.py"]);',
        ),
        ("hooks/session-start", "#!/bin/sh\npython3 tools/priming.py\n"),
        ("hooks/session-start.ps1", "pwsh -File tools/state.ps1\n"),
        ("hooks/session-start.cmd", "flow status\r\n"),
        ("commands/flow/status.toml", 'prompt = """```bash\npython3 state.py\n```"""'),
    ],
)
def test_installed_runtime_scan_detects_structural_invocations(
    tmp_path: Path, relative: str, content: str
) -> None:
    _write(tmp_path / relative, content)
    violations = validate.validate_installed_runtime_dependencies(tmp_path)
    violation_paths = [
        item.path.relative_to(tmp_path).as_posix() for item in violations
    ]
    assert relative in violation_paths


def test_installed_runtime_scan_allows_explicit_maintainer_surfaces(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "tools/validate.py", "subprocess.run(['python3', 'generator.py'])\n"
    )
    _write(tmp_path / "tests/test_runtime.py", "python3 tools/validate.py\n")
    assert validate.validate_installed_runtime_dependencies(tmp_path) == []


def test_runtime_transition_allowlist_is_exact_and_stale_sensitive(
    tmp_path: Path,
) -> None:
    assert (
        validate.validate_installed_runtime_dependencies(
            REPO_ROOT,
            transition_allowlist=validate._RUNTIME_TRANSITION_ALLOWLIST,
        )
        == []
    )
    violations = validate.validate_installed_runtime_dependencies(
        tmp_path,
        transition_allowlist={"hooks/session-start.sh:hook_script"},
    )
    assert len(violations) == 1
    assert "stale runtime transition allowlist entry" in violations[0].message


def test_static_opencode_runtime_needs_no_transition_allowlist(
    tmp_path: Path,
) -> None:
    relative = ".opencode/plugins/flow.js"
    source = REPO_ROOT / relative
    _write(tmp_path / relative, source.read_text(encoding="utf-8"))
    exact_entries = {
        item
        for item in validate._RUNTIME_TRANSITION_ALLOWLIST
        if item.startswith(f"{relative}:")
    }
    assert exact_entries == set()
    assert (
        validate.validate_installed_runtime_dependencies(
            tmp_path, transition_allowlist=set()
        )
        == []
    )

    with (tmp_path / relative).open("a", encoding="utf-8") as file:
        file.write('\nspawn("python3", ["arbitrary.py"]);\n')
    violations = validate.validate_installed_runtime_dependencies(
        tmp_path, transition_allowlist=set()
    )
    assert any("forbidden runtime process" in item.message for item in violations)


def test_validation_invalidation_requires_fresh_revalidation_before_terminal(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    _validate_forward(journal)
    _event(
        journal,
        "validation_invalidated",
        actor="flow-executor",
        direction="forward",
        validation_attempt_id=f"{journal['operation_id']}:forward:v00",
        reason="contender_appeared",
        observed_nonterminal_operation_ids=["20260814T120001Z-other-note-1-1-00"],
        failed_checks=[
            {
                "check_id": "transaction_arbitration",
                "expected": [],
                "observed": ["20260814T120001Z-other-note-1-1-00"],
            }
        ],
    )
    journal["state"] = "committed"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "final validation_recorded" in messages

    journal["state"] = "recovery_required"
    _validate_forward(journal, 1)
    journal["state"] = "committed"
    _write_journal(root, journal)
    assert validate.validate_markdown_transactions(root) == []


def test_validation_invalidation_requires_a_concrete_failed_check(
    tmp_path: Path,
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    _validate_forward(journal)
    _event(
        journal,
        "validation_invalidated",
        actor="flow-executor",
        direction="forward",
        validation_attempt_id=f"{journal['operation_id']}:forward:v00",
        reason="mutation_drift",
        observed_nonterminal_operation_ids=[],
        failed_checks=[],
    )
    journal["state"] = "recovery_required"
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "validation_invalidated event is not exact" in messages


@pytest.mark.parametrize(
    "mutation", ["terminal_after_rollback", "reason_check_mismatch"]
)
def test_terminal_validation_and_invalidation_direction_grammar_is_exact(
    tmp_path: Path, mutation: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    _apply(journal, 1, root)
    _validate_forward(journal)
    if mutation == "terminal_after_rollback":
        journal["events"].pop()
        _select(journal, "rollback")
        _validate_forward(journal)
        journal["state"] = "committed"
    else:
        _event(
            journal,
            "validation_invalidated",
            actor="flow-executor",
            direction="forward",
            validation_attempt_id=f"{journal['operation_id']}:forward:v00",
            reason="contender_appeared",
            observed_nonterminal_operation_ids=[],
            failed_checks=[
                {
                    "check_id": "after_fragments",
                    "expected": "after",
                    "observed": "drift",
                }
            ],
        )
        journal["state"] = "recovery_required"
    _write_journal(root, journal)

    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "validation direction grammar" in messages


def test_validation_attempt_suffix_exhaustion_is_a_hard_stop(tmp_path: Path) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    _apply(journal, 0, root)
    for suffix in range(100):
        _validate_forward(journal, suffix)
        _event(
            journal,
            "validation_invalidated",
            actor="flow-executor",
            direction="forward",
            validation_attempt_id=f"{journal['operation_id']}:forward:v{suffix:02d}",
            reason="read_set_drift",
            observed_nonterminal_operation_ids=[],
            failed_checks=[
                {
                    "check_id": "complete_read_set",
                    "expected": "exact",
                    "observed": "drift",
                }
            ],
        )
    journal["state"] = "recovery_required"
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "validation attempts exhausted" in messages


@pytest.mark.parametrize(
    "location",
    [
        "fragment",
        "ordered_write",
        "read_target",
        "dependency_path",
        "transaction_directory",
        "inventory",
        "glob_scope",
    ],
)
def test_journal_rejects_symlink_traversal_in_every_namespace(
    tmp_path: Path, location: str
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal("20260814T120000Z-agent-claim-1-2-00")
    journal["archive_inventory"] = {
        "base": "bundle_root",
        "root": "specs/demo-flow",
        "directories": ["."],
        "files": ["spec.md"],
    }
    flow_root = root / journal["flow_root"]
    configured_root = root / journal["configured_root"]
    bundle_root = root / journal["bundle_root"]
    (flow_root / "linked").symlink_to(flow_root / "tasks", target_is_directory=True)
    (configured_root / "linked-transactions").symlink_to(
        configured_root / "tasks/transactions", target_is_directory=True
    )
    (bundle_root / "linked-flow").symlink_to(flow_root, target_is_directory=True)
    records = {
        "fragment": (journal["fragments"][0], "path", "linked/1.2.md"),
        "ordered_write": (journal["ordered_writes"][0], "path", "linked/1.2.md"),
        "read_target": (journal["read_set"][3]["target"], "path", "linked/1.2.md"),
        "dependency_path": (
            journal["read_set"][3]["dependency_paths"][0],
            "path",
            "linked/1.1.md",
        ),
        "transaction_directory": (
            journal["read_set"][0]["directory"],
            "path",
            "linked-transactions",
        ),
        "inventory": (journal["archive_inventory"], "root", "linked-flow"),
        "glob_scope": (journal["read_set"][4]["scope"], "glob", "linked/*.md"),
    }
    record, key, value = records[location]
    record[key] = value
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "symlink" in messages


@pytest.mark.parametrize(
    ("operation", "payload", "extra_predicate"),
    [
        ("note", {"category": "observation", "text": "record it"}, None),
        ("discover", {"text": "found", "impact": "none", "next_step": None}, None),
        (
            "block",
            {
                "blocked_reason": "waiting",
                "unblock_condition": "reply",
                "next_step": "resume",
            },
            {
                "predicate": "in_progress_target_is_current",
                "spec": {"base": "flow_root", "path": "spec.md"},
                "target": {"base": "flow_root", "path": "tasks/1.2.md"},
            },
        ),
    ],
)
def test_noncurrent_note_discover_and_open_block_need_no_claim_guards(
    tmp_path: Path, operation: str, payload: dict, extra_predicate: dict | None
) -> None:
    root = _transaction_root(tmp_path)
    journal = _journal(f"20260814T120000Z-agent-{operation}-1-2-00")
    journal["request"]["operation"] = operation
    journal["request"]["payload"] = payload
    journal["read_set"] = journal["read_set"][:3]
    if extra_predicate is not None:
        journal["read_set"].append(extra_predicate)
    _write_journal(root, journal)
    messages = "\n".join(
        item.message for item in validate.validate_markdown_transactions(root)
    )
    assert "read_set predicates" not in messages
