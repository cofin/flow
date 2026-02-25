# Flow Skip

Skip current task with documented justification.

## Usage
`/flow:skip {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task.

## Phase 2: Update Beads (Source of Truth)

```bash
br close {task_id} --reason "SKIPPED: {reason}"
```

## Phase 3: Log to Skipped File

Append to `.agent/specs/{flow_id}/skipped.md`

## Phase 4: Sync to Markdown (MANDATORY)

Run `/flow:sync {flow_id}` to export Beads state to spec.md.

**Do NOT write `[-]` markers directly to spec.md.** Beads is the source of truth.

## Phase 5: Continue

Display next available task from `br ready`.
