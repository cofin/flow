---
description: Display progress overview with Beads status
allowed-tools: Read, Glob, Grep, Bash
---

# Flow Status

Display progress overview for all active flows.

## Phase 1: Load Registry

Read `.agents/flows.md` to get list of active flows.

---

## Phase 2: Beads Status (Source of Truth)

```bash
br status                          # Workspace overview
br ready                           # Unblocked tasks ready to work
br list --status in_progress       # Resume active work
br blocked                         # Blocked tasks
```

---

## Phase 3: Flow Summary (Beads-First)

For each active flow:

### Primary: Get Status from Beads

```bash
br show {epic_id} --format json
```

Parse JSON to count:

- `pending` tasks
- `in_progress` tasks  
- `completed` tasks
- `blocked` tasks

Calculate progress: `completed / total * 100`

### Fallback: Parse spec.md

If Beads unavailable:

1. Read `.agents/specs/{flow_id}/spec.md` (unified spec+plan)
2. Parse Implementation Plan section
3. Count tasks by status (from Beads export or markers)

---

## Phase 4: Display Dashboard

```
Flow Status Dashboard

=== Active Flows ===

[~] auth - Add user authentication
    Progress: 5/12 tasks (41%)
    Current: Phase 2, Task 6
    Last Activity: 2026-01-24 14:30
    Blockers: 0

[ ] dark-mode - Add dark mode toggle
    Progress: 0/8 tasks (0%)
    Status: Not started

=== Beads Ready ===

Ready tasks (no blockers):
  - auth: Task 6 - Implement login endpoint
  - auth: Task 7 - Add session middleware

=== Beads Blocked ===

Blocked tasks:
  - auth: Task 8 - Waiting for API keys [!]

=== Quality Gates ===

Last Test Run: PASSED (2026-01-24 14:25)
Coverage: 82%

=== Recent Activity ===

- 14:30 - auth: Task 5 completed [abc1234]
- 14:15 - auth: Task 4 completed [def5678]
- 13:45 - dark-mode: Flow created
```

---

## Phase 5: Recommendations

Based on status, suggest next action:

- If blocked tasks exist: "Document blockers with `br update {id} --status blocked --notes \"BLOCKED: {reason}\"`"
- If no in-progress: "Ready to continue? Run `/flow-implement {flow_id}`"
- If flow complete: "Flow ready for archive? Run `/flow-archive {flow_id}`"

---

## Critical Rules

1. **READ ONLY** - This command only displays information
2. **BEADS IS SOURCE OF TRUTH** - Pull task status from Beads, not spec.md
3. **ACTIONABLE** - Provide next step suggestions
