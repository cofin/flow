
# Flow Task

Create ephemeral exploration flow (no audit trail).

## Usage

```text
flow-task <description>
```

## Overview

A "task" is a lightweight, temporary flow for:

- Proof of concept exploration
- Quick experiments
- Research spikes

Tasks have NO audit trail - meant to be discarded.

## Workflow

### Phase 1: Create Task

1. Generate `task_id` in the format `task_shortname` (e.g., `task_fix_login`).
2. Record the exploration goal in the task's `notes.md`.

### Phase 2: Scratch Directory

Create `<configured-root>/scratch/{task_id}/`:

- `notes.md` - Scratch notes
- `findings.md` - What you learned

Scratch is ephemeral, untracked, and deliberately not OKF. Never create it under
`<bundle-root>`.

### Phase 3: Work Freely

During task:

- No TDD required
- No commit conventions
- Just explore and learn

### Phase 4: Resolution

When done, choose:

**Promote** - Convert to a real flow:

```bash
flow-prd "{description}"
```

**Discard** - Delete everything:

```bash
rm -rf <configured-root>/scratch/{task_id}
git checkout .
```

**Keep Notes** - Delete code, author a research bundle per
[Research](research.md), then delete the scratch directory. Rewrite the
findings into the research sections; never move `findings.md` into `bundles/`
as-is.

## Critical Rules

1. **NO AUDIT** - Tasks are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
4. **NEVER WRITE SCRATCH INTO BUNDLES** - Anything entering `bundles/` is a
   well-formed OKF document, authored as such, never a moved scratch file
