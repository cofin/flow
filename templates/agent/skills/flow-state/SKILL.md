---
name: flow-state
description: "Use when a Flow request reads, mutates, reconciles, completes, archives, or recovers Markdown lifecycle state and transaction journals."
---

# Flow State

Use this skill as the deterministic state boundary for Flow. The caller chooses a legal lifecycle operation and supplies a complete typed request; the `flow-reconciler` applies that request literally or refuses it. Read the packaged [canonical state contract](references/state.md) before handling any request. It owns the exact payload schemas, read predicates, fragments, event grammar, and lifecycle effects.

<!-- flow-state-contract: start -->
```yaml
operations: [create, activate, claim, release, note, discover, block, unblock, checkpoint, close, skip, reopen, revise, reconcile, complete, archive, recover, status]
mutation_request:
  required: [flow_id, operation, actor, occurred_at, expected_plan_revision, expected_plan_commit, expected_state_revision, targets, payload]
  unknown_fields: refuse
  missing_fields: refuse
  identity_mismatch: refuse_without_writes
  payload_schema: canonical_state_contract
status_request:
  required: [operation, flow_id, task_ids]
  unknown_fields: refuse
  writes: none
target_modes:
  create.flow: empty
  create.task: one
  activate: empty
  claim: one
  release: one
  note: one
  discover: one
  block: one
  unblock: one
  checkpoint.task: one
  checkpoint.phase: empty
  checkpoint.plan: all_tasks_sorted
  close: one
  skip: one
  reopen: one
  revise: all_tasks_sorted
  reconcile: empty
  complete: empty
  archive: empty
  recover: empty
lifecycle_guards:
  create.flow: [absent]
  create.task: [planned, active]
  activate: [planned]
  active_allowed: [claim, release, note.normal, discover, block, unblock, checkpoint.task, checkpoint.phase, close, skip, reopen, reconcile, complete]
  checkpoint.plan: [planned, active]
  revise: [planned, active]
  archive: [completed]
  status: [planned, active, completed]
  recover: [planned, active, completed, removed]
  completed_allowed: [status, recover, archive, note.git_note_attachment]
  removed_allowed: [recover]
identity_routes:
  task_target: [create.task, claim, release, note, discover, block, unblock, checkpoint.task, close, skip, reopen]
  all_tasks_then_spec: [checkpoint.plan, revise]
  spec_only_empty_targets: [activate, checkpoint.phase, reconcile, complete, archive]
  untouched_tasks: may_lag_state_revision
snapshot_effects:
  current_target: apply_operation_effects
  non_current_target: bounded_summary_only
  spec_only: typed_affected_ids_not_operation_targets
roots:
  configured: setup_state_or_default
  bundle: config_or_default
  flow: bundle_specs_flow_id
  paths: namespaced_relative_no_symlink_or_escape
result_union:
  additional_fields: forbidden
  keyset: [outcome, operation, flow_id, operation_id, plan_revision, plan_commit, state_revision, targets, journal, evidence, refusal]
  outcome_enum: [committed, replayed, rolled_back, recovery_required, contended, refused, status]
  field_types:
    operation: contract_operation_or_null
    flow_id: non_empty_flow_id_or_null
    operation_id: canonical_operation_id_or_null
    plan_revision: integer_at_least_one_or_null
    plan_commit: lowercase_7_to_40_hex_or_null
    state_revision: non_negative_integer_or_null
    targets: unique_sorted_task_id_array
    journal: journal_record_or_null
    evidence: selected_evidence_record_or_null
    refusal: refusal_record_or_null
  journal_record:
    keyset: [operation_id, state, path]
    state_enum: [committed, rolled_back, prepared, task_writes_started, recovery_required, rollback_in_progress, contended]
    constraints: [operation_id equals result operation_id, path is namespaced configured-root transaction journal, additional fields forbidden]
  evidence_records:
    committed: [actor, occurred_at, validation_attempt_id, checks]
    replayed: [source_operation_id, replay_key, checks]
    rolled_back: [actor, occurred_at, validation_attempt_id, checks]
    recovery_required: [classification, observed_operation_ids, applied_prefix, next_action]
    contended: [classification, observed_operation_ids, applied_prefix, next_action]
    status: [flows, current, ready, blocked, conflicts]
    constraints: [selected record has exactly its listed keys, checks and ids preserve canonical order, additional fields forbidden]
  refusal_record:
    keyset: [code, stage, field, predicate, path, expected, observed, message]
    nullability: {code: required, stage: required, field: nullable, predicate: nullable, path: nullable, expected: nullable, observed: nullable, message: required}
    constraints: [additional fields forbidden, code and stage use canonical refusal identifiers, message non-empty]
  variants:
    committed:
      outcome: committed
      operation: mutating_operation
      journal_state: committed
      evidence_schema: committed
      nullability: {operation: required, flow_id: required, operation_id: required, plan_revision: required, plan_commit: nullable, state_revision: required, targets: required, journal: required, evidence: required, refusal: null}
    replayed:
      outcome: replayed
      operation: replayable_operation
      journal_state: committed
      evidence_schema: replayed
      nullability: {operation: required, flow_id: required, operation_id: required, plan_revision: required, plan_commit: nullable, state_revision: required, targets: required, journal: required, evidence: required, refusal: null}
    rolled_back:
      outcome: rolled_back
      operation: original_mutating_operation
      journal_state: rolled_back
      evidence_schema: rolled_back
      nullability: {operation: required, flow_id: required, operation_id: required, plan_revision: required, plan_commit: nullable, state_revision: required, targets: required, journal: required, evidence: required, refusal: null}
    recovery_required:
      outcome: recovery_required
      operation: original_mutating_operation
      journal_state: prepared_or_task_writes_started_or_recovery_required_or_rollback_in_progress
      evidence_schema: recovery_required
      nullability: {operation: required, flow_id: required, operation_id: required, plan_revision: required, plan_commit: nullable, state_revision: required, targets: required, journal: required, evidence: required, refusal: null}
    contended:
      outcome: contended
      operation: original_mutating_operation
      journal_state: contended
      evidence_schema: contended
      nullability: {operation: required, flow_id: required, operation_id: required, plan_revision: required, plan_commit: nullable, state_revision: required, targets: required, journal: required, evidence: required, refusal: null}
    refused:
      outcome: refused
      operation: requested_operation_or_null_when_unparseable
      journal_state: existing_journal_or_null
      evidence_schema: null
      nullability: {operation: nullable, flow_id: nullable, operation_id: nullable, plan_revision: nullable, plan_commit: nullable, state_revision: nullable, targets: required, journal: nullable, evidence: null, refusal: required}
    status:
      outcome: status
      operation: status
      journal_state: null
      evidence_schema: status
      nullability: {operation: required, flow_id: nullable, operation_id: null, plan_revision: null, plan_commit: null, state_revision: null, targets: required, journal: null, evidence: required, refusal: null}
```
<!-- flow-state-contract: end -->

## Workflow

1. Resolve the configured, bundle, and flow roots from live Markdown configuration. Validate repository-relative, nonsymlink paths. Read every nonterminal transaction journal before selecting a normal operation.
2. Require the exact request keyset above. `occurred_at` is canonical UTC; targets are explicit and sorted where required. Existing-flow mutations require the caller's exact expected plan and state identity. Only absent-flow creation uses null expected identity. Status uses its separate read-only request shape.
3. Load the operation-specific payload and predicate schemas from the canonical contract. Refuse unknown payload keys, implicit targets, missing identity, lifecycle violations, incomplete read sets, unresolved journals, and live/expected drift without changing tracked state.
4. Dispatch the accepted request to `flow-reconciler`. It prepares exact before/after images, creates the untracked Markdown journal, jointly arbitrates contenders, writes in canonical order, rereads every mutation, and records terminal validation.
5. Return exactly one tagged `result_union` variant. Never omit a key or substitute prose for a nullable field. Status returns its typed dashboard evidence without an operation id, journal, revision, or write.

## Recovery

Recovery begins from the selected journal, never a conversation summary. Resolve a final unmatched start against its exact live before/after image, retain one immutable finish-or-rollback direction, and resume the append-only provenance grammar. Joint arbitration chooses authority; directory scan order never does. A conflict or unexplained value stops without a tracked write.

## Guardrails

- Lifecycle decisions remain with the planner, executor, reviewer, or user. The state sidecar does not choose a transition, invent evidence, infer targets, or weaken a guard.
- Consumer execution uses ordinary file read/write/edit tools only. Never invoke Python, `uv`, a shell, PowerShell, a Flow executable, a helper program, a database, daemon, or service.
- Mutations may touch only Flow Markdown plus the untracked Markdown transaction journal. Never edit source files, hide authority in runtime state, delete a journal, or leave a resident archived spec.
- Install the consumer skill at `.agents/skills/flow-state/`; never create `.agents/bundles/skills/`.

## Validation

Before reporting success, reread the transaction directory, complete semantic read set, mutation prefixes, target fragments, checklist, snapshot, and operation postconditions. The latest uninvalidated validation event must be final before a terminal journal state. Report exact conflicts and paths on refusal.

## Example

A caller that has read an active spec and an open ready task submits a `claim` request with the exact observed plan/state identities, target task id, actor/time, and canonical claim payload. The sidecar either commits the journaled task-first/spec-last transition or returns a no-write refusal describing the mismatched predicate.
