---
description: Git-aware revert of tracks, phases, or tasks
argument-hint: <track_id|phase|task> [target]
allowed-tools: Read, Write, Edit, Bash
---

# Flow Revert

Reverting: **$ARGUMENTS**

## Phase 1: Parse Target

Determine revert scope:
- `track {track_id}` - Revert entire track
- `phase {track_id} {N}` - Revert phase N
- `task {track_id} {N}` - Revert single task

---

## Phase 2: Find Commits

Use git notes to find related commits:

```bash
git log --notes --grep="track.*{track_id}" --oneline
```

For phase/task, filter by specific markers.

---

## Phase 3: Confirmation

Show what will be reverted:

```
Revert Target: {scope}

Commits to revert:
  - abc1234: feat(auth): Add login endpoint
  - def5678: feat(auth): Add user model

Files affected:
  - src/auth/login.ts
  - src/auth/user.ts
  - tests/auth/login.test.ts

Proceed with revert? (yes/no)
```

---

## Phase 4: Execute Revert

```bash
git revert --no-commit {commits}
git commit -m "revert({scope}): Revert {description}"
```

---

## Phase 5: Update Plan

Reset task statuses in `plan.md`:
- `[x]` -> `[ ]`
- Remove commit SHAs

---

## Phase 6: Sync Beads

```bash
bd update {task_ids} --status pending
```

---

## Critical Rules

1. **CONFIRM FIRST** - Always show what will be reverted
2. **NO FORCE** - Use revert, not reset
3. **SYNC BEADS** - Update task statuses
4. **UPDATE PLAN** - Reset task markers
