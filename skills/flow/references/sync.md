
# Flow Sync

Sync active backend task state to on-disk spec.md for a flow.

## Phase 1: Resolve Flow

1. If arguments provided, use as `flow_id`.
2. Otherwise, read `.agents/flows.md` for the active flow.
3. If no active flows, report "No active flows to sync."

## Phase 2: Load Metadata

1. Read `.agents/specs/{flow_id}/metadata.json`
2. Read `.agents/workflow.md` and `.agents/tech-stack.md`
3. Extract backend linkage such as `beads_epic_id`
4. If missing, continue in markdown-only mode instead of erroring

## Phase 3: Fetch Active Backend State

Use the active backend:

- `bd`: official Beads show/export flow
- `br`: `br show {beads_epic_id} --format json`
- no-Beads: skip backend export and preserve markdown-only state

Map backend status to markdown markers:

| Beads Status   | Marker |
|----------------|--------|
| `open` / `pending` | `[ ]` |
| `in_progress` | `[~]` |
| `closed` / `completed` | `[x]` |
| `blocked` | `[!]` |
| `skipped` / `deferred` | `[-]` |

## Phase 4: Update spec.md

1. Read `.agents/specs/{flow_id}/spec.md`
2. Find the Implementation Plan / task list section
3. Replace task status markers with current backend status when a backend export exists
4. Preserve existing markdown-only markers when no backend is configured
5. Append commit SHAs from backend completion reasons where available
6. Write updated spec.md

**Only update task markers. Do NOT modify requirements sections.**

## Phase 5: Update Metadata

Set `"synced_at"` and `"updated_at"` in metadata.json.

## Phase 6: Synthesis Check (The Synthesis Mandate)

1. **Identify**: Inspect `learnings.md` and the `Implementation Plan` for new architectural patterns, conventions, or non-obvious technical discoveries.
2. **Propose**: If a significant pattern is found, propose its immediate elevation to `.agents/patterns.md` or its synthesis into a chapter in `.agents/knowledge/`.
3. **Execute**: If the user confirms, integrate the knowledge now. Do NOT wait for archive if the pattern is foundational for the current or upcoming flows.

## Phase 7: Context Drift Check

1. Compare dependency files with `.agents/tech-stack.md`
2. Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, package scripts, `.pre-commit-config.yaml`, and CI files
3. If commands or backend assumptions are stale, report that `.agents/workflow.md` should be revalidated

## Final Output

```text
Flow Sync Complete: {flow_id}

Backend: {bd|br|none}
Synced from backend record: {beads_epic_id|none}
  Pending: {n}  In Progress: {n}  Completed: {n}  Blocked: {n}
Updated: .agents/specs/{flow_id}/spec.md
workflow.md: {revalidated-needed|unchanged}
```
