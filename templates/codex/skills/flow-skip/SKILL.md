---
name: flow-skip
description: "Skip task with justification"
---

# Flow Skip

Skip current task with documented justification.

## Usage
`/flow:skip {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task.

## Phase 2: Validate Skip

Confirm with user:
> Are you sure you want to skip "{task_description}"?
> This should only be used for tasks that are:
> - No longer needed
> - Out of scope
> - Blocked with no resolution path

## Phase 3: Document Skip

### 3.1 Update Plan
Change status: `[~]` or `[ ]` → `[-]`

```markdown
- [-] Task 1.3: Description
  - SKIPPED: {reason}
```

### 3.2 Sync to Beads
```bash
br close {task_id} --reason "SKIPPED: {reason}"
```

### 3.3 Log to Skipped File
Append to `.agent/specs/{flow_id}/skipped.md`:
```markdown
## {date} - Task {task_id}

**Task:** {description}

**Reason:** {reason}

**Decision By:** User
```

## Phase 4: Continue

```
Task {task_id} SKIPPED

Reason: {reason}

Finding next task...
```

Then display next available task from `br ready`.
