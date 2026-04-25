---
description: Git-aware revert of flows, phases, or tasks
---

# Flow Revert

Git-aware revert of flows, phases, or tasks.

## Usage
- `/flow-revert task` - Revert last task
- `/flow-revert phase` - Revert current phase
- `/flow-revert flow {flow_id}` - Revert entire flow

## Phase 1: Identify Scope

Gather commits to revert based on scope.

## Phase 2: Confirm Revert

```
Revert Scope: {scope}

Commits to revert:
- {list}

Proceed? [y/N]
```

## Phase 3: Execute Revert

```bash
git revert --no-commit {commits}
git commit -m "revert({scope}): {description}"
```

### 3.1 Reopen Beads Tasks (Source of Truth)

```bash
bd update {task_id} --status open
```

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. It is MANDATORY that you run `/flow-sync` to update the markdown state after any task completion or status change.

## Final Output

```
Revert Complete

Commits Reverted: {count}
Tasks Reset: {count}

Resume with: /flow-implement {flow_id}
```
