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

```bash
br create "Task: {description}" -t task -p 4 \
  --description="{exploration_goal}"
br update {task_task_id} --notes "Ephemeral exploration. Created by /flow:task"
```

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

**Promote** - Convert to a real flow:
```bash
/flow:prd "{description}"
```

**Discard** - Delete everything:
```bash
rm -rf .agents/tasks/{task_id}
git checkout .
```

**Keep Notes** - Delete code, keep findings:
```bash
mv .agents/tasks/{task_id}/findings.md .agents/research/
rm -rf .agents/tasks/{task_id}
```

## Critical Rules

1. **NO AUDIT** - Tasks are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
