---
description: Create ephemeral exploration flow (no audit trail)
argument-hint: <description>
allowed-tools: Read, Write, Bash
---

# Flow Task

Creating ephemeral exploration flow: **$ARGUMENTS**

## Overview

A "task" is a lightweight, temporary flow for:
- Proof of concept exploration
- Quick experiments
- Research spikes
- Learning exercises

Tasks have NO audit trail - they're meant to be discarded.

---

## Phase 1: Create Task

```bash
br create "Task: {description}" -t task -p 4 \
  --description="{exploration_goal_and_what_youre_trying_to_learn}"
br update {task_id} --notes "Ephemeral exploration. No audit trail. Created by /flow-task on {date}"
```

This creates:

- Temporary Beads task (priority P4 - backlog)
- Minimal spec file
- No git commits required

**Note:** Always include `--description` with `br create`, then add `--notes` via `br update`, even for ephemeral work.

---

## Phase 2: Task Directory

Create `.agents/tasks/{task_id}/`:
- `notes.md` - Scratch notes
- `findings.md` - What you learned

---

## Phase 3: Work Freely

During task:
- No TDD required
- No commit conventions
- No coverage requirements
- Just explore and learn

---

## Phase 4: Resolution

When done, choose:

> **What do you want to do with this task?**
>
> - **Promote** - Convert to a real flow (preserves learnings)
> - **Discard** - Delete everything
> - **Keep Notes** - Delete code, keep findings.md

### Promote

```bash
/flow-prd "{description}"
# Copy findings to PRD's learnings.md
```

### Discard

```bash
rm -rf .agents/tasks/{task_id}
br close {task_id} --reason "Task discarded"  # if tracked in Beads
git checkout .  # Discard any code changes
```

### Keep Notes

```bash
mv .agents/tasks/{task_id}/findings.md .agents/research/
rm -rf .agents/tasks/{task_id}
git checkout .
```

---

## Final Output

```
Task Created

ID: {task_id}
Location: .agents/tasks/{task_id}/

This is an ephemeral exploration flow.
- No audit trail
- No TDD required
- Explore freely

When done:
- /flow-task promote {task_id} - Convert to real flow
- /flow-task discard {task_id} - Delete everything
- /flow-task keep {task_id} - Keep notes only
```

---

## Critical Rules

1. **NO AUDIT** - Tasks are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
