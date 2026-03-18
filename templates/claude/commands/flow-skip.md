---
description: Skip current task with justification
argument-hint: <flow_id> <task_number> "<reason>"
allowed-tools: Read, Write, Edit, Bash
---

# Flow Skip

Skipping task: **$ARGUMENTS**

## Phase 1: Parse Arguments

Extract:
- flow_id
- task_number
- reason

---

## Phase 2: Update Beads (Source of Truth)

```bash
br close {task_id} --reason "Skipped: {reason}"
```

---

## Phase 3: Log Skip

Append to `.agents/specs/{flow_id}/skipped.md`:

```markdown
## [YYYY-MM-DD HH:MM] Task N: {description}

**Reason:** {reason}
**Impact:** {any impact on other tasks}
```

---

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Phase 5: Check Dependencies

If other tasks depend on this one, warn:

```
Warning: Task {M} depends on skipped Task {N}
Consider updating dependencies or blocking Task {M}
```

---

## Critical Rules

1. **REASON REQUIRED** - Must justify skip
2. **BEADS FIRST** - Update Beads before anything else
4. **CHECK DEPS** - Warn about dependent tasks
