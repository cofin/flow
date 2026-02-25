---
description: Skip task with justification
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

Append to `.agent/specs/{flow_id}/skipped.md`:

```markdown
## [YYYY-MM-DD HH:MM] Task N: {description}

**Reason:** {reason}
**Impact:** {any impact on other tasks}
```

---

## Phase 4: Sync to Markdown (MANDATORY)

Run `/flow-sync {flow_id}` to export Beads state to spec.md.

**Do NOT write `[-]` markers directly to spec.md.** Beads is the source of truth.

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
2. **BEADS FIRST** - Update Beads before anything else
3. **MANDATORY SYNC** - Run `/flow-sync` after Beads update (never write `[-]` directly)
4. **CHECK DEPS** - Warn about dependent tasks
