---
name: flow-sync-status
description: "Use when syncing flow specifications and task files, checking status dashboard, or executing groundskeeping cleanup checks."
---

# Flow Sync And Status

Use this lifecycle skill for spec/task sync, developer status dashboards, and groundskeeping cleanup checks.

## Workflow

1. Reconcile the flow specification (`spec.md`) and the task files (`tasks/*.md`) by running `python3 tools/sync.py`. This resolves statuses, commit SHAs, and auto-scaffolds missing task files.
2. Generate the developer status dashboard by running `python3 tools/status.py`. This aggregates progress, handles ready/blocked queues, and extracts notes.
3. Validate repository integrity and find orphaned task files by running `SKIP_CLAUDE_VALIDATE=1 python3 tools/validate.py`.
4. Suggest archiving completed specs (`status: completed`) using the `/flow:archive <flow_id>` command.

## Guardrails

- **Reconciled markdown is ALWAYS persisted to disk.** Reconciler updates the task checklist in `spec.md` to match the states of `tasks/*.md` task files.
- **Do not commit or stage files automatically** unless sync policy config or the user explicitly approves it.
- **Never mutate task details destructively** during status dashboard or cleanup validation checks. Only the reconciler should mutate task statuses or add commit SHAs.

## Validation

- Confirm that `tools/validate.py` passes with zero violations after sync or cleanup operations.
- Verify that no orphaned task files remain in spec directories.
- For this repo, run `python3 tools/validate.py` after skill or command changes.

## References Index

- [Sync](../flow/references/sync.md)
- [Status](../flow/references/status.md)
- [Cleanup](../flow/references/cleanup.md)

## Example

User: "Show status."

Action: Run `python3 tools/status.py` and print the formatted active dashboard.
