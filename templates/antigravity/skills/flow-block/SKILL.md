---
name: flow-block
description: "Mark task as blocked with reason"
---

# Flow Block

Mark a task as blocked with documented reason.

## Usage
`flow-block {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task from:
1. Beads: `br list --status in_progress`
2. spec.md: find `[~]` task

## Phase 2: Document Block

### 2.1 Sync to Beads
```bash
br update {task_id} --status blocked --notes "BLOCKED: {reason}"
```

### 2.2 Log to Blockers File
Append to `.agents/specs/{flow_id}/blockers.md`:
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
1. Work on another task: `br ready`
2. Skip this task: `flow-skip {task_id}`
3. Resolve blocker and unblock with: `br update {task_id} --status open`
```
