---
description: Sync context with codebase after external changes
argument-hint: [--full]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Refresh

Refreshing context for codebase drift: **$ARGUMENTS**

## Phase 1: Load Current Context

1. Read `.agents/index.md`, `.agents/flows.md`, `.agents/tech-stack.md`, `.agents/workflow.md`.
2. Identify active flow from `.agents/flows.md`.
3. If active flow exists, read `.agents/specs/{flow_id}/metadata.json` for last sync timestamp.

---

## Phase 2: Scan for Drift

1. Run `git log --oneline` since last sync to find recent commits.
2. Run `git diff --name-status` to identify changed files.
3. Check dependency files (`package.json`, `pyproject.toml`, `Cargo.toml`) for changes.
4. Compare with `.agents/tech-stack.md`.
5. Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files.
6. Compare those command surfaces with `.agents/workflow.md`.

---

## Phase 3: Update Context

1. If dependencies changed, update `.agents/tech-stack.md`.
2. If workflow settings or canonical commands changed, prompt:
   - "Workflow settings may be stale. Revalidate `.agents/workflow.md` now?"
   - Refresh only the affected workflow sections instead of replacing the whole file.
3. Prefer repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, and pre-commit entrypoints when updating workflow guidance.
4. If tasks completed externally, sync them through the active backend's completion flow.
5. Refresh `.agents/index.md` if structural changes detected.

---

## Phase 4: Sync with Beads

Resolve the active backend first:

- `bd`: use the official Beads sync/status commands
- no-Beads: skip backend sync and continue refreshing workflow/context files

---

## Phase 5: Report

```text
Flow Refresh Complete
─────────────────────
Since last sync ({timestamp}):
  • {N} commits
  • Dependencies: {changes}
  • tech-stack.md: {updated/unchanged}
  • workflow.md: {revalidated/unchanged}
  • spec.md: {synced/unchanged}
```

---

## Critical Rules

1. **MERGE, DON'T REPLACE** - Never overwrite manual edits to spec.md
2. **ASK ON CONFLICT** - Present both versions if conflicts detected
3. **READ-ONLY ON CODE** - Only modify `.agents/` context files
4. **SYNC AT END** - Run sync to ensure spec.md reflects final state
5. **WORKFLOW DRIFT COUNTS** - Treat stale canonical commands, backend assumptions, and ignore policy as refresh work, not optional cleanup
