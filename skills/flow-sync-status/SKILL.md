---
name: flow-sync-status
description: "Use when reconciling Flow task truth into a spec, displaying status queues, or checking bundle state anomalies."
---

# Flow Sync And Status

Use this lifecycle skill for reconciliation and read-only dashboards. Read the [sync](../flow/references/sync.md), [status](../flow/references/status.md), and [state](../flow/references/state.md) references. All state mutations cross the `flow-state`/`flow-reconciler` boundary; status remains a direct read-only request.

After compaction, handoff, or session loss, reconstruct authority by following the [normative state contract](../flow/references/state.md) directly before sync or status. Hook/plugin context is static routing only.

<!-- flow-sync-status-routing: start -->
```yaml
sync: typed_reconcile_request
status: typed_read_only_status_request
state_mutations: flow-reconciler_via_flow-state
```
<!-- flow-sync-status-routing: end -->

## Workflow

### Sync

1. Resolve configured, bundle, and flow roots; read nonterminal journals first. Read the chosen spec, every task frontmatter, its implementation checklist, and Continuity Snapshot.
2. Build the exact mismatch records and sorted affected task ids. Missing or malformed task files are anomalies, not permission to invent a worksheet or task state.
3. Submit a closed `reconcile` request with exact observed plan/state identity, empty targets, actor/time, and the canonical payload. The reconciler journals a spec-only transaction, updates derived checklist/snapshot fields, and records affected ids as typed evidence.
4. Reread the spec/tasks and report the new state identity or exact refusal. Never flip a marker independently.

### Status

1. Submit the closed read-only `status` request with an optional flow id and sorted unique task filter.
2. Read specs, task frontmatter, snapshots, and journals. Report progress, current claims, ready tasks, blocked tasks, and transaction conflicts. Ready tasks sort by priority, creation time, then task id.
3. Offer a next lifecycle action; do not execute a mutation until the caller supplies its explicit typed state request.

## Guardrails

- Task files are authoritative, but only `reconcile` may project their state into the spec checklist and snapshot.
- Status never creates an operation id, journal, revision, or write.
- Never invoke Python, `uv`, a shell, PowerShell, a Flow executable, or a helper. Use ordinary file tools and the Markdown sidecar protocol.
- Never scaffold a missing worksheet during reconcile, infer identity/targets, mutate plan content, or stage/commit automatically.

## Validation

After reconcile, require every affected checklist marker/snapshot field to equal task truth, unchanged task and plan identity, empty operation targets, exact typed affected ids, and one valid terminal journal. Status validation requires a complete read with no writes.

## Example

For a task/spec marker mismatch, read both documents and submit one explicit `reconcile` request containing the exact mismatch and affected task id. For “show status,” submit the specialized status request and render the sorted queues without changing Markdown.

## References Index

- [Sync](../flow/references/sync.md)
- [Status](../flow/references/status.md)
- [State contract](../flow/references/state.md)
- [Cleanup](../flow/references/cleanup.md)
