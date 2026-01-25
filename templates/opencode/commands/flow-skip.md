# Flow Skip

Skip current task with documented justification.

## Usage
`/flow:skip {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task.

## Phase 2: Document Skip

### 2.1 Update Plan
Change status: `[~]` or `[ ]` → `[-]`

### 2.2 Sync to Beads
```bash
bd close {task_id} --reason "SKIPPED: {reason}"
```

### 2.3 Log to Skipped File
Append to `.agent/specs/{track_id}/skipped.md`

## Phase 3: Continue

Display next available task from `bd ready`.
