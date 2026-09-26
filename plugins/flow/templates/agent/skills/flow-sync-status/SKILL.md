---
name: flow-sync-status
description: "Use when reorienting a Flow across machines or harnesses, reconciling task truth into a spec, displaying status queues, or checking bundle drift."
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
refresh: cross_session_reorient_and_align
state_mutations: lifecycle_owner_via_flow-state
```
<!-- flow-sync-status-routing: end -->

## Workflow

1. **Direct Frontmatter Sync (`/flow:sync`)**: Load `flow-state`, inspect each `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`, prepare the typed `reconcile` request and journal, map frontmatter `state` to checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), update `spec.md`, and reread the result; follow [../flow/references/sync.md](../flow/references/sync.md).
2. **Status Dashboard (`/flow:status`)**: Render current, ready, in-progress, and blocked task queues across active specs without mutating files; follow [../flow/references/status.md](../flow/references/status.md).
3. **Cross-Machine & Cross-Harness Reorientation (`/flow:refresh`)**: Reorient the session after switching machines (`git pull` without untracked local journals) or switching harnesses by recovering any local nonterminal journal, pruning obsolete terminal journals, auditing Git commits and working tree changes against `spec.md` and `tasks/*.md`, releasing stale cross-harness `claimed_by` locks, reconciling spec/task revisions and checklists via `flow-state`, refreshing drifted `product/tech-stack.md` or `knowledge/workflow.md`, and outputting an actionable status and next-task handoff report; follow [../flow/references/refresh.md](../flow/references/refresh.md).

## Guardrails

- Task files are authoritative; `sync` and `refresh` route all state mutations through `flow-state`.
- `status` is strictly read-only and performs no file or journal mutations.
- Treat absent `<configured-root>/transactions/` on a new machine as normal untracked state; rely on tracked Markdown and Git history while recovering any present local nonterminal journal first.
- Reconcile and reorient with standard file tools; no daemon or external runtime is required.

## Output

Return the reorientation alignment summary, active status dashboard queues, and exact next task handoff.

## Validation

Reread `spec.md` and `tasks/*.md` to confirm checklist markers, `plan_revision`, `state_revision`, and active claims match live repository truth.

## Example

When switching from Claude Code on one machine to Antigravity or Codex CLI on another after `git pull`, `/flow:refresh` reconciles tasks whose commits already landed, releases stale `claimed_by` locks from the prior harness, syncs `spec.md` checklists and revisions, and lists the exact next ready task to implement.

<!-- project-customization: start -->
## Custom Sync Nuances
<!-- project-customization: end -->
