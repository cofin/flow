# Flow Block

Mark a task as blocked with documented reason.

## Usage
`/flow:block {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task from:
1. Beads: `bd ready` (look for in_progress)
2. Plan.md: find `[~]` task

## Phase 2: Document Block

### 2.1 Update Plan
Change status: `[~]` → `[!]`

Add block note:
```markdown
- [!] Task 1.3: Description
  - BLOCKED: {reason}
  - Blocked: {date}
```

### 2.2 Sync to Beads
```bash
bd update {task_id} --status blocked --notes "{reason}"
```

### 2.3 Log to Blockers File
Append to `.agent/specs/{track_id}/blockers.md`:
```markdown
## {date} - Task {task_id}

**Reason:** {reason}

**Impact:** {what this blocks}

**Resolution Path:** {suggested resolution}
```

## Phase 3: Suggest Next Actions

```
Task {task_id} marked as BLOCKED

Reason: {reason}

Next options:
1. Work on another task: `bd ready`
2. Skip this task: `/flow:skip {task_id}`
3. Resolve blocker and unblock: `/flow:unblock {task_id}`
```
