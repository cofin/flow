---
name: flow-block
description: "Mark task as blocked with reason"
---

# Flow Block

Mark a task as blocked with documented reason.

## Usage
`$flow:block {task_id} "{reason}"`

## Phase 1: Identify Task

If task_id not provided, use current in-progress task from:
1. Beads: `br ready` (look for in_progress)
2. Plan.md: find `[~]` task

## Phase 2: Update Beads (Source of Truth)

```bash
br update {task_id} --status blocked --notes "{reason}"
```

## Phase 3: Log to Blockers File

Append to `.agents/specs/{flow_id}/blockers.md`:
```markdown
## {date} - Task {task_id}

**Reason:** {reason}

**Impact:** {what this blocks}

**Resolution Path:** {suggested resolution}
```

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Phase 5: Suggest Next Actions

```
Task {task_id} marked as BLOCKED

Reason: {reason}

Next options:
1. Work on another task: `br ready`
2. Skip this task: `$flow:skip {task_id}`
3. Resolve blocker and unblock: `$flow:unblock {task_id}`
```
