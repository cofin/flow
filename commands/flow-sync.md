---
description: Export Beads state to spec.md (source of truth sync)
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Sync

Syncing active backend state to disk for flow: **$ARGUMENTS**

## The Bridge Mandate

**CRITICAL:** `/flow:sync` is the primary bridge between the **Beads Source of Truth** and the **Markdown View**. It should be run after every task completion, note addition, or status change in Beads.

---

## Phase 0: Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
    - Use the injected **Flow Root** for all artifact paths.
    - Use the injected **Beads Backend** for sync and task management.
2. **Fallback (if context missing):** Use `.agents/` as the default root.

---

## Phase 1: Resolve Flow

1. **Check for User Input:** If `$ARGUMENTS` is provided, use it as `flow_id`.
2. **Auto-Discovery (No Argument):**
    - Read `<root_directory>/flows.md` for active flows.
    - If exactly one active flow, select it.
    - If multiple, choose most recently modified.
    - If none, report "No active flows to sync."

---

## Phase 2: Load Flow Metadata

1. Read `<root_directory>/specs/{flow_id}/metadata.json`.
2. Read `<root_directory>/workflow.md` and `<root_directory>/tech-stack.md`.
3. Extract backend linkage such as `beads_epic_id`.

---

## Phase 3: Fetch Active Backend State

Resolve the active backend first (check hook context or beads.json):

- `bd`: use the official Beads show/export command. **CRITICAL:** Pull all `notes` for the epic and its tasks.
- no-Beads: skip backend export and preserve markdown-only task state.

Parse the backend output. Map statuses to markdown markers:

| Backend Status | Marker |
|----------------|--------|
| `open` / `pending` | `[ ]` |
| `in_progress` | `[~]` |
| `closed` / `completed` | `[x]` |
| `blocked` | `[!]` |
| `skipped` / `deferred` | `[-]` |

---

## Phase 4: Regenerate spec.md and learnings.md

1. **Update spec.md**:
   - Find the `## Implementation Plan` section.
   - For each task line matching `- [ ] ...`, `- [x] ...`, etc.:
     - Match the task to the corresponding backend task by title.
     - Replace the status marker with the current backend status.
     - If the backend completion reason contains a commit SHA, append it: `[abc1234]`.
   - Write updated `spec.md`.

2. **Update learnings.md**:
   - Extract all `notes`/`comments` from the backend for the current flow.
   - Categorize by task ID and timestamp.
   - Append NEW notes to `.agents/specs/{flow_id}/learnings.md` in Ralph-style format.
   - Synthesize notes into patterns where appropriate.

---

## Phase 5: Context Drift Check

1. Compare dependency files (`package.json`, `pyproject.toml`, etc.) with `.agents/tech-stack.md`.
2. Inspect workflow drift across `Makefile`, `justfile`, etc.
3. If drift detected, report and ask to revalidate `.agents/workflow.md`.

---

## Phase 6: Update Metadata

Update `.agents/specs/{flow_id}/metadata.json`:

- Set `"synced_at": "{ISO timestamp}"`
- Set `"updated_at": "{ISO timestamp}"`

---

## Phase 7: Summary

```text
Flow Sync Complete: {flow_id}

Backend: {bd|none}
Tasks synced from backend record: {beads_epic_id|none}
  Pending:     {count}
  In Progress: {count}
  Completed:   {count}
  Blocked:     {count}
  Skipped:     {count}

Notes synced: {count} new notes added to learnings.md
Updated: .agents/specs/{flow_id}/spec.md
```

---

## Critical Rules

1. **READ-ONLY ON BACKEND** - Only read from the active backend during sync; do not mutate tasks here.
2. **PRESERVE SPEC CONTENT** - Only update task status markers and append notes, not requirements text.
3. **MATCH CAREFULLY** - Match tasks by title.
4. **IDEMPOTENT** - Running sync multiple times produces the same result.
5. **NO HARDCODED BACKEND** - Support `bd` and markdown-only mode gracefully.
