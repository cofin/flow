---
description: Mark task as blocked with reason
argument-hint: <flow_id> <task_number> "<reason>"
allowed-tools: Read, Write, Edit, Bash
---

# Flow Block

Blocking task: **$ARGUMENTS**

## Phase 1: Parse Arguments

Extract:
- flow_id
- task_number
- reason

---

## Phase 2: Update Beads (Source of Truth)

```bash
br update {task_id} --status blocked --notes "BLOCKED: {reason}"
br dep add {task_id} {blocking_task_id}  # if blocked by another task
```

---

## Phase 3: Log Blocker

Append to `.agents/specs/{flow_id}/blockers.md`:

```markdown
## [YYYY-MM-DD HH:MM] Task N: {description}

**Reason:** {reason}
**Status:** Blocked
**Dependencies:** {if any}
```

---

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Phase 5: Notify

```
Task Blocked

Flow: {flow_id}
Task: {N}. {description}
Reason: {reason}

Next Steps:
- Address the blocker
- Run `/flow-implement {flow_id}` to continue with other tasks
- Run `br ready` to see unblocked tasks
```

---

## Critical Rules

1. **REASON REQUIRED** - Must provide blocking reason
2. **BEADS FIRST** - Update Beads before anything else
4. **LOG HISTORY** - Record in blockers.md
