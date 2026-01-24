---
description: Skip task with justification
argument-hint: <track_id> <task_number> "<reason>"
allowed-tools: Read, Write, Edit, Bash
---

# Flow Skip

Skipping task: **$ARGUMENTS**

## Phase 1: Parse Arguments

Extract:
- track_id
- task_number
- reason

---

## Phase 2: Update Plan

In `.agent/specs/{track_id}/plan.md`:

```markdown
- [-] N. Task description [-: {reason}]
```

---

## Phase 3: Update Beads

```bash
bd update {task_id} --status skipped --notes "Skipped: {reason}"
```

---

## Phase 4: Log Skip

Append to `.agent/specs/{track_id}/skipped.md`:

```markdown
## [YYYY-MM-DD HH:MM] Task N: {description}

**Reason:** {reason}
**Impact:** {any impact on other tasks}
```

---

## Phase 5: Check Dependencies

If other tasks depend on this one, warn:

```
Warning: Task {M} depends on skipped Task {N}
Consider updating dependencies or blocking Task {M}
```

---

## Critical Rules

1. **REASON REQUIRED** - Must justify skip
2. **BEADS SYNC** - Update Beads status
3. **CHECK DEPS** - Warn about dependent tasks
