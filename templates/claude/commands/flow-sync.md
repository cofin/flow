---
description: Export Beads state back to .agent/specs/ markdown
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Sync

Syncing Beads state to disk for flow: **$ARGUMENTS**

## Phase 1: Resolve Flow

1. **Check for User Input:** If `$ARGUMENTS` is provided, use it as `flow_id`.
2. **Auto-Discovery (No Argument):**
    - Read `.agent/flows.md` for active flows.
    - If exactly one active flow, select it.
    - If multiple, choose most recently modified.
    - If none, report "No active flows to sync."

---

## Phase 2: Load Flow Metadata

1. Read `.agent/specs/{flow_id}/metadata.json`.
2. Extract `beads_epic_id`.
3. If no `beads_epic_id`, report error: "Flow has no linked Beads epic. Cannot sync."

---

## Phase 3: Fetch Beads State

```bash
bd show {beads_epic_id} --children --json
```

Parse the JSON output. Map each task's Beads status to a markdown marker:

| Beads Status   | Marker |
|----------------|--------|
| `pending`      | `[ ]`  |
| `in_progress`  | `[~]`  |
| `completed`    | `[x]`  |
| `blocked`      | `[!]`  |
| `skipped`      | `[-]`  |

---

## Phase 4: Regenerate spec.md Task Section

1. Read `.agent/specs/{flow_id}/spec.md`.
2. Find the `## Implementation Plan` section (or `## Plan` or task list section).
3. For each task line matching `- [ ] ...`, `- [x] ...`, `- [~] ...`, `- [!] ...`, `- [-] ...`:
   - Match the task to the corresponding Beads task (by title or position).
   - Replace the status marker with the current Beads status.
   - If the Beads task has a `--reason` containing a commit SHA, append it: `[abc1234]`.
4. Write the updated `spec.md` back to disk.

**IMPORTANT:** Only update the task status markers. Do NOT modify the specification sections (requirements, design, etc.).

---

## Phase 5: Update Metadata

Update `.agent/specs/{flow_id}/metadata.json`:
- Set `"synced_at": "{ISO timestamp}"`
- Set `"updated_at": "{ISO timestamp}"`

---

## Phase 6: Summary

```
Flow Sync Complete: {flow_id}

Tasks synced from Beads epic: {beads_epic_id}
  Pending:     {count}
  In Progress: {count}
  Completed:   {count}
  Blocked:     {count}
  Skipped:     {count}

Updated: .agent/specs/{flow_id}/spec.md
```

---

## Critical Rules

1. **READ-ONLY ON BEADS** - Only read from Beads, never write during sync
2. **PRESERVE SPEC CONTENT** - Only update task status markers, not requirements text
3. **MATCH CAREFULLY** - Match tasks by title, not just position
4. **IDEMPOTENT** - Running sync multiple times produces the same result
5. **NO GIT OPERATIONS** - Do not commit or push changes
