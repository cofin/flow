
# Flow Status

Display progress overview for all active flows.

## Phase 1: Load Registry

Read `.agents/flows.md` to get list of active flows.

## Phase 2: Beads Status (Source of Truth)

```bash
br status                     # Workspace overview
br ready                      # Unblocked tasks ready to work
br list --status in_progress  # Resume active work
```

## Phase 3: Flow Summary (Beads-First)

For each active flow:

### Primary: Get Status from Beads

```bash
br show {epic_id} --format json
```

Parse JSON to count:

- `open` tasks
- `in_progress` tasks
- `closed` tasks
- `blocked` tasks

Calculate progress: `closed / total * 100`

### Fallback: Parse spec.md

If Beads unavailable:

1. Read `.agents/specs/{flow_id}/spec.md` (unified spec+plan)
2. Parse Implementation Plan section
3. Count tasks by status

## Phase 4: Display Dashboard

```text
Flow Status Dashboard

=== Active Flows ===

[~] auth_20260124 - Add user authentication
    Progress: 5/12 tasks (41%)
    Current: Phase 2, Task 6
    Blockers: 0

[ ] dark-mode_20260124 - Add dark mode toggle
    Progress: 0/8 tasks (0%)
    Status: Not started

=== Beads Ready ===

Ready tasks (no blockers):
  - auth_20260124: Task 6 - Implement login endpoint

=== Beads Blocked ===

Blocked tasks:
  - auth_20260124: Task 8 - Waiting for API keys [!]

=== Quality Gates ===

Last Test Run: PASSED
Coverage: 82%

=== Recent Activity ===

- 14:30 - auth_20260124: Task 5 completed [abc1234]
```

## Phase 5: Recommendations

Based on status, suggest next action:

- If blocked: "Run `flow-block` to document blockers"
- If no in-progress: "Run `flow-implement {flow_id}`"
- If complete: "Run `flow-archive {flow_id}`"

## Critical Rules

1. **READ ONLY** - This command only displays information
2. **BEADS IS SOURCE OF TRUTH** - Pull task status from Beads, not spec.md
3. **ACTIONABLE** - Provide next step suggestions
