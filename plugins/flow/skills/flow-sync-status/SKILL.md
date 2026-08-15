---
name: flow-sync-status
description: "Use when reconciling Flow task truth into a spec, displaying status queues, refreshing project context, or checking bundle state anomalies."
---

# Flow Sync And Status

<!-- lifecycle-ownership: owner=flow-sync-status; operations=sync,status,refresh -->

## Trigger

Use for `sync|status|refresh`.

<!-- flow-sync-status-routing: start -->
```yaml
sync: typed_reconcile_request
status: typed_read_only_status_request
state_mutations: flow-reconciler_via_flow-state
```
<!-- flow-sync-status-routing: end -->

## Workflow

1. Resolve configured roots and read nonterminal journals before normal work.
2. For sync, compare task truth with checklist/snapshot projections, submit one
   exact `reconcile` request, then reread the result.
3. For status, submit the read-only status request and render current, ready,
   blocked, and conflict queues in priority/creation/id order.
4. For refresh, rescan live project context, update only derived knowledge, and
   preserve active plan/task state.

## Guardrails

- Task files are authoritative; only reconcile projects them into the spec.
- Status performs no write, revision, journal, or operation-id allocation.
- Use ordinary file tools; never infer targets, scaffold worksheets, mutate plan
  content, or stage/commit automatically.

## Output

Return exact mismatches and new state identity for sync, sorted queues for
status, or changed context and preserved state identity for refresh.

## Validation

Reread every affected projection and require task agreement, unchanged plan
identity, typed affected ids, and a valid terminal journal. Status proves a
complete read with no writes.

## Conditional References

- [Sync](../flow/references/sync.md)
- [Status](../flow/references/status.md)
- [Refresh](../flow/references/refresh.md)
- [State](../flow/references/state.md)

## Example

For a marker mismatch, reconcile from task truth and reread. For “show status,”
return sorted queues without changing Markdown.
