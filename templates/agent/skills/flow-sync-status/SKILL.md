---
name: flow-sync-status
description: "Project-tailored Flow sync and status skill. Use for fast direct frontmatter reconciliation, status queue dashboarding, and context refresh."
---

# Flow Sync & Status (Project-Tailored)

<!-- lifecycle-ownership: owner=flow-sync-status; operations=sync,status,refresh -->

## Trigger

Use for `sync|status|refresh`.

## Direct Frontmatter Sync (`/flow:sync`)

Loads the canonical project `flow-state` skill and applies a journaled
`reconcile` operation from authoritative task frontmatter:

1. **Read Task Authority**: Inspect each `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`.
2. **Marker Projection**:
   - `state: open` &rarr; `[ ]`
   - `state: in_progress` &rarr; `[~]`
   - `state: closed` &rarr; `[x]` (with `[<sha>]` if commit is present)
   - `state: blocked` &rarr; `[!]`
   - `state: skipped` &rarr; `[-]`
3. **Prepare Transaction**: Record the complete spec/task read set, exact mismatch payload, and spec before/after fragments in the untracked transaction journal.
4. **Reconcile Checklist**: Update only derived checklist and snapshot fields in `spec.md`, then reread the journal, spec, and every task frontmatter. Missing task files are anomalies; sync never scaffolds or infers them.

## Status Dashboard (`/flow:status`)

Displays unblocked, ready, in-progress, and blocked task queues across active specs.

<!-- project-customization: start -->
## Custom Sync Nuances
<!-- project-customization: end -->
