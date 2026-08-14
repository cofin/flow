---
name: flow-state
description: "Use when a Flow request reads, mutates, reconciles, completes, archives, or recovers Markdown lifecycle state and transaction journals."
---

# Flow State

Use this skill as the deterministic state boundary for Flow. The caller chooses a legal lifecycle operation and supplies a complete typed request; the `flow-reconciler` applies that request literally or refuses it. Read the [canonical state contract](../flow/references/state.md) before handling any request. It owns the exact payload schemas, read predicates, fragments, event grammar, and lifecycle effects.

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
```
<!-- flow-state-contract: end -->

## Workflow

1. Resolve the configured, bundle, and flow roots from live Markdown configuration. Validate repository-relative, nonsymlink paths. Read every nonterminal transaction journal before selecting a normal operation.
2. Require the exact request keyset above. `occurred_at` is canonical UTC; targets are explicit and sorted where required. Existing-flow mutations require the caller's exact expected plan and state identity. Only absent-flow creation uses null expected identity. Status uses its separate read-only request shape.
3. Load the operation-specific payload and predicate schemas from the canonical contract. Refuse unknown payload keys, implicit targets, missing identity, lifecycle violations, incomplete read sets, unresolved journals, and live/expected drift without changing tracked state.
4. Dispatch the accepted request to `flow-reconciler`. It prepares exact before/after images, creates the untracked Markdown journal, jointly arbitrates contenders, writes in canonical order, rereads every mutation, and records terminal validation.
5. Return the operation id, result, new shared state identity, explicit targets, and evidence. Status returns the filtered dashboard without an operation id, journal, or write.

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
