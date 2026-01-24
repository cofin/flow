---
description: Create ephemeral exploration track (no audit trail)
argument-hint: <description>
allowed-tools: Read, Write, Bash
---

# Flow Wisp

Creating ephemeral exploration track: **$ARGUMENTS**

## Overview

A "wisp" is a lightweight, temporary track for:
- Proof of concept exploration
- Quick experiments
- Research spikes
- Learning exercises

Wisps have NO audit trail - they're meant to be discarded.

---

## Phase 1: Create Wisp

```bash
bd mol wisp {description}
```

This creates:
- Temporary Beads epic (marked ephemeral)
- Minimal spec file
- No git commits required

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
> - **Promote** - Convert to a real track (preserves learnings)
> - **Discard** - Delete everything
> - **Keep Notes** - Delete code, keep findings.md

### Promote

```bash
/flow-newtrack "{description}"
# Copy findings to new track's learnings.md
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

This is an ephemeral exploration track.
- No audit trail
- No TDD required
- Explore freely

When done:
- /flow-wisp promote {wisp_id} - Convert to real track
- /flow-wisp discard {wisp_id} - Delete everything
- /flow-wisp keep {wisp_id} - Keep notes only
```

---

## Critical Rules

1. **NO AUDIT** - Wisps are temporary
2. **LOW CEREMONY** - Minimal process
3. **EXPLICIT END** - Must promote, discard, or keep
