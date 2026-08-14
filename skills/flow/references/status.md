# Flow Status Reference

Status is the specialized read-only state operation. It reconstructs authority from Markdown and journals and never creates transaction state. Read the [state contract](state.md) for direct-read continuity and ready-task rules.

<!-- flow-status-contract: start -->
```yaml
operation: status
request:
  required: [operation, flow_id, task_ids]
  flow_id: one_or_null
  task_ids: unique_sorted_empty_means_all
writes: none
operation_id: none
journal: none
ready_order: [priority, created_at, task_id]
```
<!-- flow-status-contract: end -->

## Discover

1. Resolve and validate the configured and bundle roots. Read every nonterminal transaction journal before requiring a resident spec. Jointly classify simultaneous journals; surface zero/applied/rollback/conflict outcomes rather than choosing by scan order.
2. Apply the optional flow/task filter. With no flow filter, read every planned, active, and completed resident spec plus its Continuity Snapshot. A removed flow is visible only through an unresolved archive journal.
3. Read all selected task frontmatter. Verify plan identity, state-revision bounds, current-task/claim agreement, dependencies, checklist projections, and snapshot state identity. Read complete task bodies only when needed for the selected current/ready task or requested details.

## Aggregate

For each flow report:

- lifecycle and exact plan/state identity;
- unresolved transaction classification and required recovery action;
- total, closed, skipped, and progress `closed / (total - skipped)` with the empty denominator reported explicitly;
- current task and claimant;
- ready tasks: open with all dependencies closed, sorted `(priority, created_at, task_id)` where priority is `P0` through `P4`;
- blocked tasks: explicit blocked state plus open tasks waiting on dependencies;
- the five newest timestamped Notes & Discoveries entries;
- malformed identity, duplicate claim, dependency, checklist, snapshot, and journal anomalies.

## Recommend

Recommend only a caller decision: recover a selected journal, resume the sole valid claim, claim the first ready task, address blockers, activate a planned flow, or archive a completed flow. Status itself never chooses or submits a mutation.

## Validate

Before returning the dashboard, reread any journal/spec/task whose value controls the recommendation. Confirm the request filter was applied exactly, ready ordering is stable, and no file, operation id, journal, or revision was created.
