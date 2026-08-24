---
name: flow-sync-status
description: "Use when reconciling Flow task truth into a spec, displaying status queues, refreshing project context, or checking bundle state anomalies."
disable-model-invocation: true
---

# Flow Sync & Status

<!-- lifecycle-ownership: owner=flow-sync-status; operations=sync,status,refresh -->

## Trigger

Use for `sync|status|refresh`.

<!-- flow-sync-status-routing: start -->
```yaml
sync: typed_reconcile_request
status: typed_read_only_status_request
state_mutations: lifecycle_owner_via_flow-state
```
<!-- flow-sync-status-routing: end -->

## Workflow

1. **Direct Frontmatter Sync (`/flow:sync`)**: Load `flow-state`, inspect each `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`, prepare the typed reconcile request and journal, map frontmatter `state` to checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), update `spec.md`, and reread the result.
2. **Status Dashboard (`/flow:status`)**: Render current, ready, in-progress, and blocked task queues across active specs.
3. **Context Refresh (`/flow:refresh`)**: Rescan repository configuration and update `product/tech-stack.md` and `knowledge/workflow.md` without modifying active specs.

## Guardrails

- Task files are authoritative; only reconcile projects them into the spec.
- Status performs no file mutations.
- Reconcile with standard file tools; no daemon or external CLI is required.

## Output

Return the reconciliation summary and active status dashboard queues.

## Validation

Reread `spec.md` and confirm that all checklist markers match task frontmatter states.

## Example

For a completed task, run `/flow:sync` to project `state: closed` and commit SHA into the `spec.md` checklist item.

<!-- project-customization: start -->
## Custom Sync Nuances
<!-- project-customization: end -->
