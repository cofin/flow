---
description: Export Beads state to spec.md (source of truth sync)
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Sync

Syncing active backend state to disk for flow: **$ARGUMENTS**

## Phase 1: Resolve Flow

1. **Check for User Input:** If `$ARGUMENTS` is provided, use it as `flow_id`.
2. **Auto-Discovery (No Argument):**
    - Read `.agents/flows.md` for active flows.
    - If exactly one active flow, select it.
    - If multiple, choose most recently modified.
    - If none, report "No active flows to sync."

---

## Phase 2: Load Flow Metadata

1. Read `.agents/specs/{flow_id}/metadata.json`.
2. Read `.agents/workflow.md` and `.agents/tech-stack.md` so sync can preserve current workflow guidance and context metadata.
3. Extract backend linkage such as `beads_epic_id`.
4. If no linked backend record exists, continue in markdown-only mode instead of erroring.

---

## Phase 3: Fetch Active Backend State

Resolve the active backend first:

- `bd`: use the official Beads show/export command
- `br`: `br show {beads_epic_id} --format json`
- no-Beads: skip backend export and preserve markdown-only task state

Parse the backend output when available. Map each task's backend status to a markdown marker:

| Backend Status | Marker |
|----------------|--------|
| `open` / `pending` | `[ ]` |
| `in_progress` | `[~]` |
| `closed` / `completed` | `[x]` |
| `blocked` | `[!]` |
| `skipped` / `deferred` | `[-]` |

---

## Phase 4: Regenerate spec.md Task Section

1. Read `.agents/specs/{flow_id}/spec.md`.
2. Find the `## Implementation Plan` section (or `## Plan` or task list section).
3. For each task line matching `- [ ] ...`, `- [x] ...`, `- [~] ...`, `- [!] ...`, `- [-] ...`:
   - If a backend export exists, match the task to the corresponding backend task by title first, then stable ordering only as fallback.
   - Replace the status marker with the current backend status.
   - If the backend completion reason contains a commit SHA, append it: `[abc1234]`.
   - If no backend is configured, preserve the existing markdown-only status markers.
4. Write the updated `spec.md` back to disk.

**IMPORTANT:** Only update the task status markers. Do NOT modify the specification sections (requirements, design, etc.).

---

## Phase 5: Context Drift Check

1. Compare dependency files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`) with `.agents/tech-stack.md`.
2. Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files.
3. If canonical commands, backend assumptions, or ignore policy appear stale, report:
   - "Workflow settings may be stale. Revalidate `.agents/workflow.md` now?"
4. Do not rewrite `workflow.md` aggressively during sync; note drift for the user or apply only explicitly approved doc updates.

---

## Phase 6: Update Metadata

Update `.agents/specs/{flow_id}/metadata.json`:

- Set `"synced_at": "{ISO timestamp}"`
- Set `"updated_at": "{ISO timestamp}"`

---

## Phase 7: Summary

```text
Flow Sync Complete: {flow_id}

Backend: {bd|br|none}
Tasks synced from backend record: {beads_epic_id|none}
  Pending:     {count}
  In Progress: {count}
  Completed:   {count}
  Blocked:     {count}
  Skipped:     {count}

Updated: .agents/specs/{flow_id}/spec.md
workflow.md: {revalidated-needed|unchanged}
tech-stack.md: {drift-detected|unchanged}
```

---

## Critical Rules

1. **READ-ONLY ON BACKEND** - Only read from the active backend during sync; do not close, block, or mutate tasks here
2. **PRESERVE SPEC CONTENT** - Only update task status markers, not requirements text
3. **MATCH CAREFULLY** - Match tasks by title, not just position
4. **IDEMPOTENT** - Running sync multiple times produces the same result
5. **NO GIT OPERATIONS** - Do not commit or push changes
6. **NO HARDCODED BACKEND** - Support `bd`, `br`, and markdown-only mode gracefully
