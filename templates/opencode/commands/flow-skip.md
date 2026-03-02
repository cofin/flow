---
description: Skip current task with justification
---

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

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Phase 5: Continue

Display next available task from `br ready`.
