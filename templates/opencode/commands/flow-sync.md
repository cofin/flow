---
description: Export Beads state back to .agent/specs/ markdown
---

# Flow Sync

Sync Beads task state to on-disk spec.md for a flow.

## Phase 1: Resolve Flow

1. If `$ARGUMENTS` provided, use as `flow_id`.
2. Otherwise, read `.agent/flows.md` for the active flow.
3. If no active flows, report "No active flows to sync."

## Phase 2: Load Metadata

1. Read `.agent/specs/{flow_id}/metadata.json`
2. Extract `beads_epic_id`
3. If missing, error: "Flow has no linked Beads epic."

## Phase 3: Fetch Beads State

```bash
br show {beads_epic_id} --children --json
```

Map Beads status to markdown markers:

| Beads Status   | Marker |
|----------------|--------|
| `pending`      | `[ ]`  |
| `in_progress`  | `[~]`  |
| `completed`    | `[x]`  |
| `blocked`      | `[!]`  |
| `skipped`      | `[-]`  |

## Phase 4: Update spec.md

1. Read `.agent/specs/{flow_id}/spec.md`
2. Find the Implementation Plan / task list section
3. Replace task status markers with current Beads status
4. Append commit SHAs from Beads close reasons where available
5. Write updated spec.md

**Only update task markers. Do NOT modify requirements sections.**

## Phase 5: Update Metadata

Set `"synced_at"` and `"updated_at"` in metadata.json.

## Final Output

```
Flow Sync Complete: {flow_id}

Synced from Beads epic: {beads_epic_id}
  Pending: {n}  In Progress: {n}  Completed: {n}  Blocked: {n}
Updated: .agent/specs/{flow_id}/spec.md
```
