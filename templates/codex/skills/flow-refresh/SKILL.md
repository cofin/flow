---
name: flow-refresh
description: "Sync context docs with current codebase state"
---

# Flow Refresh

Sync context documents with current codebase state.

## Usage
`$flow:refresh`

## Phase 1: Scan Codebase

### 1.1 Detect Changes
```bash
git diff --stat HEAD~10
git log --oneline -10
```

### 1.2 Scan Structure
Identify new/removed:
- Directories
- Key files
- Dependencies

## Phase 2: Update Context Files

### 2.1 Tech Stack
Compare `.agents/tech-stack.md` with actual:
- package.json / pyproject.toml / Cargo.toml
- Framework usage
- Database connections

Update if differences found.

### 2.2 Index
Rebuild `.agents/index.md` with current file structure.

### 2.3 Patterns
Check if patterns in `.agents/patterns.md` are still valid:
- Do referenced files exist?
- Are APIs still the same?

Flag stale patterns for review.

## Phase 3: Flow Sync

For each active flow:
1. Check if affected files still exist
2. Verify test files match implementation
3. Update spec.md if file paths changed

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
- tech-stack.md: Added {new_dep}
- index.md: {N} new files indexed

Flagged for Review:
- patterns.md: Line 45 references removed file
- {flow_id}: Task 3 file path changed

Run `$flow:validate` for full integrity check.
```
