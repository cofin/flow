---
description: Sync context with codebase after external changes
argument-hint: [--full]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Refresh

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Refreshing context for codebase drift: **$ARGUMENTS**

## Phase 1: Load Current Context

1. Read `.agents/bundles/index.md`, `.agents/bundles/knowledge/product/tech-stack.md`, `.agents/bundles/knowledge/workflow/workflow.md`.
2. Identify active flows by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active` (or `planned`).
3. If an active flow exists, read its `spec.md` and `tasks/*.md`; use the spec's `updated_at` as the last-sync baseline.

---

## Phase 2: Scan for Drift

1. Run `git log --oneline` since last sync to find recent commits.
2. Run `git diff --name-status` to identify changed files.
3. Check dependency files (`package.json`, `pyproject.toml`, `Cargo.toml`) for changes.
4. Compare with `.agents/bundles/knowledge/product/tech-stack.md`.
5. Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files.
6. Compare those command surfaces with `.agents/bundles/knowledge/workflow/workflow.md`.

---

## Phase 3: Update Context

1. If dependencies changed, update `.agents/bundles/knowledge/product/tech-stack.md`.
2. If workflow settings or canonical commands changed, prompt:
   - "Workflow settings may be stale. Revalidate `.agents/bundles/knowledge/workflow/workflow.md` now?"
   - Refresh only the affected workflow sections instead of replacing the whole file.
3. Prefer repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, and pre-commit entrypoints when updating workflow guidance.
4. If tasks completed externally (commits reference task ids), set `state: closed` and `commit: <sha>` in the affected task files.
5. Refresh `.agents/bundles/index.md` if structural changes detected.

---

## Phase 4: Reconcile Spec and Tasks

Run the `/flow:sync` reconciliation inline: update each `spec.md` checklist marker to match its task file's `state` (task file wins on conflict), appending commit SHAs for closed tasks.

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
4. **SYNC AT END** - Reconcile the checklist so spec.md reflects final task state
5. **WORKFLOW DRIFT COUNTS** - Treat stale canonical commands and ignore policy as refresh work, not optional cleanup
