---
name: flow-sync-status
description: "Use when syncing flow specifications and task files, checking status dashboard, or executing groundskeeping cleanup checks."
---

# Flow Sync And Status

Use this lifecycle skill for spec/task sync, developer status dashboards, and groundskeeping cleanup checks. Perform every step inline by reading and editing the bundle files directly — do NOT run external scripts (`tools/*.py` are dev utilities for the Flow repository itself, not runtime dependencies).

## Workflow

1. **Reconcile** `spec.md` with `tasks/*.md` for the active flow under `.agents/bundles/specs/<flow_id>/`:
   - Read each task file's `state:` and `commit:` frontmatter. The task file always wins on conflict.
   - Rewrite each `- [<marker>] Task <short_id>: <title>` checklist line to match: `open` -> `[ ]`, `in_progress` -> `[~]`, `closed` -> `[x]` plus `[<sha>]`, `blocked` -> `[!]`, `skipped` -> `[-]`.
   - Scaffold a task file (OKF frontmatter: `type: Task`, `id: <flow_id>:<short_id>`, `title`, `state`, `depends_on`, `files`, `tests`, `created_at`, `updated_at`, `commit`) for any checklist entry missing one.
   - Update the spec's `updated_at` timestamp; change nothing else in its frontmatter.
2. **Report status** by aggregating the same files: per flow, count tasks by `state`, compute progress as closed/(total-skipped), and partition open tasks into a ready queue (all `depends_on` short ids closed) and a blocked queue. Surface in-progress tasks and the five most recent `## Notes & Discoveries` entries.
3. **Cleanup checks**: flag orphaned task files with no matching checklist entry, checklist entries with no task file, malformed frontmatter, and workflow state stored in `status:` instead of `state:`.
4. Suggest archiving completed specs (`state: completed`) using the `/flow:archive <flow_id>` command.

## Guardrails

- **Reconciled markdown is ALWAYS persisted to disk.** The checklist in `spec.md` must match the states of `tasks/*.md` after sync.
- **Do not run external python scripts** (like tools/sync.py, tools/status.py, or tools/validate.py); apply the reconciliation rules inline.
- **Do not commit or stage files automatically** unless the user explicitly approves it.
- **Never mutate task details destructively** during status or cleanup checks. Only sync reconciliation may rewrite checklist markers or add commit SHAs.

## Validation

- Confirm every checklist marker matches its task file's `state` after sync.
- Verify no orphaned task files remain in spec directories.
- Confirm task ids follow `<flow_id>:<short_id>` and `depends_on` uses short ids from the same flow.

## References Index

- [Sync](../flow/references/sync.md)
- [Status](../flow/references/status.md)
- [Cleanup](../flow/references/cleanup.md)

## Example

User: "Show status."

Action: read every active spec bundle and its task files, then print the status dashboard: per-flow progress bar, closed/total counts, active tasks, ready queue, blocked queue, and recent notes.
