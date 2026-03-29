---
description: Sync context with codebase after external changes
argument-hint: [--full]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Refresh

Refreshing context for codebase drift: **$ARGUMENTS**

## Phase 1: Load Current Context

1. Read `.agents/index.md`, `.agents/flows.md`, `.agents/tech-stack.md`.
2. Identify active flow from `.agents/flows.md`.
3. If active flow exists, read `.agents/specs/{flow_id}/metadata.json` for last sync timestamp.

---

## Phase 2: Scan for Drift

1. Run `git log --oneline` since last sync to find recent commits.
2. Run `git diff --name-status` to identify changed files.
3. Check dependency files (`package.json`, `pyproject.toml`, `Cargo.toml`) for changes.
4. Compare with `.agents/tech-stack.md`.

---

## Phase 3: Update Context

1. If dependencies changed, update `.agents/tech-stack.md`.
2. If tasks completed externally, sync to Beads: `br close {id} --reason "completed externally"`.
3. Refresh `.agents/index.md` if structural changes detected.

---

## Phase 4: Sync with Beads

```bash
br sync --flush-only
br status
```

---

## Phase 5: Report

```
Flow Refresh Complete
─────────────────────
Since last sync ({timestamp}):
  • {N} commits
  • Dependencies: {changes}
  • tech-stack.md: {updated/unchanged}
  • spec.md: {synced/unchanged}
```

---

## Critical Rules

1. **MERGE, DON'T REPLACE** - Never overwrite manual edits to spec.md
2. **ASK ON CONFLICT** - Present both versions if conflicts detected
3. **READ-ONLY ON CODE** - Only modify `.agents/` context files
4. **SYNC AT END** - Run sync to ensure spec.md reflects final state
