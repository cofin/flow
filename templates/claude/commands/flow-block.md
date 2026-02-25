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

## Phase 2: Update Plan

In `.agent/specs/{flow_id}/plan.md`:

```markdown
- [!] N. Task description [BLOCKED: {reason}]
```

---

## Phase 3: Update Beads

```bash
br block {task_id} --reason "{reason}"
```

---

## Phase 4: Log Blocker

Append to `.agent/specs/{flow_id}/blockers.md`:

```markdown
## [YYYY-MM-DD HH:MM] Task N: {description}

**Reason:** {reason}
**Status:** Blocked
**Dependencies:** {if any}
```

---

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
2. **BEADS SYNC** - Update Beads status
3. **LOG HISTORY** - Record in blockers.md
