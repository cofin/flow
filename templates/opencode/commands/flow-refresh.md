---
description: Sync context with codebase after external changes
---

# Flow Refresh

Refresh context files by re-scanning the codebase.

## Phase 1: Load Context

1. Read `.agents/flows.md` for active flow.
2. Read `.agents/specs/{flow_id}/metadata.json` for last sync timestamp.
3. Read `.agents/tech-stack.md`.
4. Read `.agents/workflow.md`.

## Phase 2: Scan for Drift

1. Run `git log --oneline` since last sync.
2. Check dependency files for changes.
3. Compare with `.agents/tech-stack.md`.
4. Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files.
5. Compare those command surfaces with `.agents/workflow.md`.

## Phase 3: Update Context

1. Update `.agents/tech-stack.md` if dependencies changed.
2. If workflow settings or canonical commands changed, prompt to revalidate `.agents/workflow.md` and refresh only the affected sections.
3. Prefer repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, and pre-commit entrypoints when updating workflow guidance.
4. Sync externally completed tasks through the active backend, not a hardcoded backend.
5. Refresh `.agents/index.md` if needed.

## Phase 4: Sync with Beads

Use the active backend:

- `bd`: official Beads sync/status flow
- no-Beads: skip backend sync

## Final Output

```
Flow Refresh Complete
─────────────────────
Since last sync ({timestamp}):
  • {N} commits
  • Dependencies: {changes}
  • tech-stack.md: {updated/unchanged}
  • workflow.md: {revalidated/unchanged}
```
