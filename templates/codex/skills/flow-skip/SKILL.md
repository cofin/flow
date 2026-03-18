---
name: flow-skip
description: "Skip current task with justification"
---

# Flow Skip

Skip current task with documented justification.

## Usage
`$flow:skip {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task.

## Phase 2: Validate Skip

Confirm with user:
> Are you sure you want to skip "{task_description}"?
> This should only be used for tasks that are:
> - No longer needed
> - Out of scope
> - Blocked with no resolution path

## Phase 3: Update Beads (Source of Truth)

```bash
br close {task_id} --reason "SKIPPED: {reason}"
```

## Phase 4: Log to Skipped File

Append to `.agents/specs/{flow_id}/skipped.md`:
```markdown
## {date} - Task {task_id}

**Task:** {description}

**Reason:** {reason}

**Decision By:** User
```

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Phase 6: Continue

```
Task {task_id} SKIPPED

Reason: {reason}

Finding next task...
```

Then display next available task from `br ready`.
