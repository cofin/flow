---
description: Sync context docs with current codebase state
---

# Flow Refresh

Sync context documents with current codebase state.

## Phase 1: Scan Codebase

```bash
git diff --stat HEAD~10
```

## Phase 2: Update Context Files

- Compare `.agents/tech-stack.md` with actual dependencies
- Rebuild `.agents/index.md`
- Flag stale patterns in `.agents/patterns.md`

## Phase 3: Flow Sync

For each active flow:
- Verify affected files still exist
- Update file paths if changed

## Phase 4: Beads Sync

```bash
br sync --flush-only
git add .beads/
git commit -m "sync beads"
```

## Phase 5: Report

```
Context Refresh Complete

Updated:
- tech-stack.md: {changes}
- index.md: {N} files indexed

Flagged for Review:
- {issues found}
```
