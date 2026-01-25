# Flow Status

Display progress overview for all active tracks.

## Phase 1: Load Registry

Read `.agent/tracks.md` to get list of active tracks.

## Phase 2: Beads Status

```bash
bd prime
bd ready
bd blocked
```

## Phase 3: Track Summary

For each active track:

1. Read `.agent/specs/{track_id}/plan.md`
2. Count tasks by status: `[ ]`, `[~]`, `[x]`, `[!]`, `[-]`
3. Calculate progress percentage

## Phase 4: Display Dashboard

```
Flow Status Dashboard

=== Active Tracks ===

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

=== Quality Gates ===

Last Test Run: PASSED
Coverage: 82%

=== Recent Activity ===

- 14:30 - auth_20260124: Task 5 completed [abc1234]
```

## Phase 5: Recommendations

Based on status, suggest next action:

- If blocked: "Run `/flow:block` to document blockers"
- If no in-progress: "Run `/flow:implement {track_id}`"
- If complete: "Run `/flow:archive {track_id}`"
