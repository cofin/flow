---
description: Git-aware revert of flows, phases, or tasks
argument-hint: <flow_id|phase|task> [target]
allowed-tools: Read, Write, Edit, Bash
---

# Flow Revert

Reverting: **$ARGUMENTS**

## Phase 1: Parse Target

Determine revert scope:

- `flow {flow_id}` - Revert entire flow
- `phase {flow_id} {N}` - Revert phase N
- `task {flow_id} {N}` - Revert single task

---

## Phase 2: Find Commits

Use git notes to find related commits:

```bash
git log --notes --grep="flow.*{flow_id}" --oneline
```

For phase/task, filter by specific markers.

---

## Phase 3: Confirmation

Show what will be reverted:

```text
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

## Phase 5: Sync Beads (Source of Truth)

```bash
bd update {task_ids} --status open
```

---

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow-sync` to update the markdown state after task completion or status changes.

## Critical Rules

1. **CONFIRM FIRST** - Always show what will be reverted
2. **NO FORCE** - Use revert, not reset
3. **BEADS FIRST** - Update Beads before syncing markdown
