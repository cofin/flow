# Flow Wisp

Create ephemeral exploration flow (no audit trail).

## Usage

```
/flow:wisp <description>
```

## Overview

A "wisp" is a lightweight, temporary flow for:
- Proof of concept exploration
- Quick experiments
- Research spikes

Wisps have NO audit trail - meant to be discarded.

## Workflow

### Phase 1: Create Wisp

```bash
br create "Wisp: {description}" -t task -p 4 \
  --description="{exploration_goal}"
br update {wisp_task_id} --notes "Ephemeral exploration. Created by /flow:wisp"
```

### Phase 2: Wisp Directory

Create `.agent/wisps/{wisp_id}/`:
- `notes.md` - Scratch notes
- `findings.md` - What you learned

### Phase 3: Work Freely

During wisp:
- No TDD required
- No commit conventions
- Just explore and learn

### Phase 4: Resolution

When done, choose:

**Promote** - Convert to a real flow:
```bash
/flow:prd "{description}"
```

**Discard** - Delete everything:
```bash
rm -rf .agent/wisps/{wisp_id}
git checkout .
```

**Keep Notes** - Delete code, keep findings:
```bash
mv .agent/wisps/{wisp_id}/findings.md .agent/research/
rm -rf .agent/wisps/{wisp_id}
```

## Critical Rules

1. **NO AUDIT** - Wisps are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
