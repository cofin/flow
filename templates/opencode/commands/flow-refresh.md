---
description: Sync context with codebase after external changes
---

# Flow Refresh

Refresh context files by re-scanning the codebase.

## Phase 1: Load Context

1. Read `.agents/flows.md` for active flow.
2. Read `.agents/specs/{flow_id}/metadata.json` for last sync timestamp.
3. Read `.agents/tech-stack.md`.

## Phase 2: Scan for Drift

1. Run `git log --oneline` since last sync.
2. Check dependency files for changes.
3. Compare with `.agents/tech-stack.md`.

## Phase 3: Update Context

1. Update `.agents/tech-stack.md` if dependencies changed.
2. Sync externally completed tasks to Beads.
3. Refresh `.agents/index.md` if needed.

## Phase 4: Sync with Beads

```bash
br sync --flush-only
br status
```

## Final Output

```
Flow Refresh Complete
─────────────────────
Since last sync ({timestamp}):
  • {N} commits
  • Dependencies: {changes}
  • tech-stack.md: {updated/unchanged}
```
