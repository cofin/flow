---
description: Git-aware revert of flows, phases, or tasks
---

# Flow Revert

Git-aware revert of flows, phases, or tasks.

## Usage
- `/flow-revert task {flow_id} {N}` - Revert single task commit
- `/flow-revert phase {flow_id} {N}` - Revert phase N commits
- `/flow-revert flow {flow_id}` - Revert entire flow spec and folder (if deleted)

## Phase 1: Parse Target

Determine revert scope from the arguments (flow, phase, or task).

## Phase 2: Find Commits

1. **Reverting a Flow (Restoring Specs)**: If the spec directory is deleted, restore it from Git:

   ```bash
   git checkout HEAD -- .agents/bundles/specs/{flow_id}
   ```

   And set the spec's frontmatter to `state: active` in `.agents/bundles/specs/{flow_id}/spec.md`.

2. **Reverting a Task**: Read `.agents/bundles/specs/{flow_id}/tasks/{task_id}.md` to extract `commit: <sha>` from YAML frontmatter.

3. **Reverting a Phase**: Read `.agents/bundles/specs/{flow_id}/spec.md` to identify the task IDs in the target phase, and read each corresponding task file under `tasks/` to extract their commit SHAs.

## Phase 3: Confirmation

Show what will be reverted:

```text
Revert Target: {scope}

Commits to revert:
  - abc1234: feat(auth): Add login endpoint

Files affected:
  - src/auth/login.ts
  - tests/auth/login.test.ts

Proceed with revert? (yes/no)
```

## Phase 4: Execute Revert

1. **Revert Commits**: Run git revert for the resolved commit(s) in reverse chronological order:

   ```bash
   git revert --no-commit {commits}
   ```

2. **Commit Reversal**:

   ```bash
   git commit -m "revert({scope}): Revert changes for {target}"
   ```

## Phase 5: Update Metadata & Sync

1. **Reset Task Status**: For reverted tasks, edit their task files under `tasks/*.md`:
   - `state: open`
   - `commit: null`
2. **Sync**: Run `/flow-sync` to update `spec.md` task checklists to match the reverted task states.

## Critical Rules

1. **CONFIRM FIRST** - Always show what will be reverted before running git revert
2. **NO FORCE** - Use git revert, not git reset
3. **METADATA FIRST** - Reset task file state and run sync after committing the revert
