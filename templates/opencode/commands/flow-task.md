---
description: Create ephemeral exploration flow (no audit trail)
agent: flow
---

# Flow Task

Creating ephemeral exploration: $ARGUMENTS

## Overview

A "task" is a lightweight, temporary flow for:
- Proof of concept exploration
- Quick experiments
- Research spikes

Tasks have NO audit trail - meant to be discarded.

## Phase 1: Create Task

1. **Generate ID**: Create `task_id` in the format `task_shortname` (e.g., `task_fix_login`).
2. **Record the goal**: Note the exploration goal and what you are trying to learn in the task's `notes.md` (created in Phase 2).

This creates:

- A temporary task directory (no spec bundle, no task files)
- No git commits required

## Phase 2: Task Directory

Create `.agents/tasks/{task_id}/`:
- `notes.md` - Scratch notes
- `findings.md` - What you learned

## Phase 3: Work Freely

During task:
- No TDD required
- No commit conventions
- Just explore and learn

## Phase 4: Resolution

When done, choose:

**Promote** - Convert to a real flow (preserves learnings):
```bash
/flow-prd "{description}"
# Copy findings to the new spec bundle's learnings.md
```

**Discard** - Delete everything:
```bash
rm -rf .agents/tasks/{task_id}
git checkout .
```

**Keep Notes** - Delete code, keep findings:
```bash
mv .agents/tasks/{task_id}/findings.md .agents/bundles/research/
rm -rf .agents/tasks/{task_id}
git checkout .
```

## Critical Rules

1. **NO AUDIT** - Tasks are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
