---
name: flow-sync-status
description: "Project-tailored Flow sync and status skill. Use for fast direct frontmatter reconciliation, status queue dashboarding, and context refresh."
---

# Flow Sync & Status (Project-Tailored)

<!-- lifecycle-ownership: owner=flow-sync-status; operations=sync,status,refresh -->

## Trigger

Use for `sync|status|refresh`.

## Direct Frontmatter Sync (`/flow:sync`)

Reconciles `spec.md` checklist markers directly from task file frontmatter:

1. **Read Task Authority**: Inspect each `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`.
2. **Marker Projection**:
   - `state: open` &rarr; `[ ]`
   - `state: in_progress` &rarr; `[~]`
   - `state: closed` &rarr; `[x]` (with `[<sha>]` if commit is present)
   - `state: blocked` &rarr; `[!]`
   - `state: skipped` &rarr; `[-]`
3. **Reconcile Checklist**: Update the checklist in `spec.md` to match task file states.
4. **Auto-Scaffolding**: If a task is listed in `spec.md` without a file in `tasks/`, generate a scaffolding stub with typed OKF frontmatter.

## Status Dashboard (`/flow:status`)

Displays unblocked, ready, in-progress, and blocked task queues across active specs.

<!-- project-customization: start -->
## Custom Sync Nuances
<!-- project-customization: end -->
