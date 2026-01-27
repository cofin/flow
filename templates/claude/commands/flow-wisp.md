---
description: Create ephemeral exploration flow (no audit trail)
argument-hint: <description>
allowed-tools: Read, Write, Bash
---

# Flow Wisp

Creating ephemeral exploration flow: **$ARGUMENTS**

## Overview

A "wisp" is a lightweight, temporary flow for:
- Proof of concept exploration
- Quick experiments
- Research spikes
- Learning exercises

Wisps have NO audit trail - they're meant to be discarded.

---

## Phase 1: Create Wisp

```bash
bd create "Wisp: {description}" -t task -p 4 \
  --description="{exploration_goal_and_what_youre_trying_to_learn}" \
  --notes="Ephemeral exploration. No audit trail. Created by /flow-wisp on {date}"
```

This creates:

- Temporary Beads task (priority P4 - backlog)
- Minimal spec file
- No git commits required

**Note:** Always include `--description` and `--notes` even for ephemeral work.

---

## Phase 2: Wisp Directory

Create `.agent/wisps/{wisp_id}/`:
- `notes.md` - Scratch notes
- `findings.md` - What you learned

---

## Phase 3: Work Freely

During wisp:
- No TDD required
- No commit conventions
- No coverage requirements
- Just explore and learn

---

## Phase 4: Resolution

When done, choose:

> **What do you want to do with this wisp?**
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
rm -rf .agent/wisps/{wisp_id}
bd mol discard {wisp_id}
git checkout .  # Discard any code changes
```

### Keep Notes

```bash
mv .agent/wisps/{wisp_id}/findings.md .agent/research/
rm -rf .agent/wisps/{wisp_id}
git checkout .
```

---

## Final Output

```
Wisp Created

ID: {wisp_id}
Location: .agent/wisps/{wisp_id}/

This is an ephemeral exploration flow.
- No audit trail
- No TDD required
- Explore freely

When done:
- /flow-wisp promote {wisp_id} - Convert to real flow
- /flow-wisp discard {wisp_id} - Delete everything
- /flow-wisp keep {wisp_id} - Keep notes only
```

---

## Critical Rules

1. **NO AUDIT** - Wisps are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
