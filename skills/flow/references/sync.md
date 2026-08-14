# Flow Sync

Sync is the canonical `reconcile` state operation. It projects authoritative task-file state into derived spec checklist and Continuity Snapshot fields through a revision-guarded, spec-only Markdown transaction. Read the canonical [`skills/flow/references/state.md`](state.md) contract for the exact request, payload, predicate, fragment, journal, and validation schemas.

<!-- flow-sync-contract: start -->
```yaml
operation: reconcile
mutation_authority: flow-reconciler_via_flow-state
targets: []
payload:
  required: [mismatches, affected_task_ids]
  affected_task_ids: unique_sorted
identity:
  expected_plan_revision: exact_live_value
  expected_plan_commit: exact_live_value_or_null
  expected_state_revision: exact_live_value
effects:
  tasks: unchanged
  plan_identity: unchanged
  spec: derived_checklist_snapshot_status_only
  operation_targets: []
  evidence: typed_affected_task_ids
```
<!-- flow-sync-contract: end -->

## Prepare

1. Resolve and validate the configured, bundle, and flow roots. Read all nonterminal transaction journals before the spec; unresolved work blocks reconcile.
2. Read the complete spec and every task frontmatter. Verify plan identity agreement, state-revision bounds, unique current claim, dependency references, checklist task ids, and snapshot identity.
3. Compare each task with its checklist/snapshot projection. Record every mismatch as the exact canonical `{path, field, spec_value, task_value}` payload item and collect affected task ids in sorted unique order.
4. Missing task files, orphan tasks, malformed frontmatter, incomplete worksheets, identity drift, and lifecycle inconsistencies are reported as anomalies. Reconcile does not scaffold, repair, or infer them; use a separately authorized operation after refinement.

## Apply

Submit the complete typed request to the `flow-reconciler`. Its read set includes the spec identity, all task identities, transaction-directory predicate, and exact mismatch predicate. It prepares only spec fragments, uses empty targets, increments the global state revision once, and records affected ids as typed evidence. The task files remain byte-for-byte unchanged and may retain older state revisions.

The reconciler updates only derived values:

- checklist marker from task state: `open -> [ ]`, `in_progress -> [~]`, `closed -> [x]` plus its commit, `blocked -> [!]`, `skipped -> [-]`;
- checklist task title only when it is already a derived projection covered by the recorded mismatch;
- Continuity Snapshot fields that are direct projections of current task truth;
- spec `state_revision`, `last_operation`, `operation_targets: []`, and `updated_at`.

It never changes task metadata, worksheet content, task lifecycle, plan revision/commit, flow lifecycle, approval, or verification evidence.

## Validate

Reread the journal, spec, and all task frontmatter. Require every recorded mismatch resolved to task truth, no unrecorded derived change, exact spec-only identity, unchanged tasks/plan, stable transaction arbitration, and the canonical terminal validation event before committed. Any new mismatch or contender invalidates the attempt and requires fresh arbitration.
