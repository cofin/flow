# /flow:refresh — Sync Context with Codebase

## Purpose

Refresh the flow's context files by re-scanning the codebase and updating `.agents/` metadata to reflect the current state. Use this when returning to a project after external changes (other contributors, CI, dependency updates) or when context files feel stale.

## When to Use

- Resuming work after pulling upstream changes
- After another developer merged PRs that affect the current flow
- When `.agents/` metadata is out of sync with actual project state
- After dependency updates or refactors outside of flow workflow
- At the start of a new session when `bd status` shows stale context

## Workflow

1. **Read current context**
   - Load `.agents/index.md`, `.agents/flows.md`, `.agents/tech-stack.md`, `.agents/workflow.md`
   - Load active flow's `spec.md` and `metadata.json`

2. **Scan codebase for drift**
   - Check git log since last known commit in metadata
   - Identify new/modified/deleted files relevant to active flows
   - Detect dependency changes (pyproject.toml, Cargo.toml, package.json)
   - Detect tech stack changes (new frameworks, removed packages)
   - Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files
   - Compare those command surfaces with `.agents/workflow.md`

3. **Update context files**
   - Refresh `.agents/tech-stack.md` if dependencies changed
   - Update `.agents/patterns.md` if new patterns detected in recent commits
   - Prompt to revalidate `.agents/workflow.md` when canonical commands, backend assumptions, or ignore policy drifted
   - Prefer repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, and pre-commit entrypoints when updating workflow guidance
   - Update flow's `spec.md` task statuses from git history (commits referencing tasks)
   - Refresh `.agents/index.md` with any structural changes

4. **Sync with Beads**
   - Resolve the active backend first
   - `bd`: use the official Beads sync/status commands
   - no-Beads: skip backend sync and continue refreshing workflow/context files
   - Reconcile backend state with refreshed context

5. **Report changes**
   - Summarize what changed since last session
   - Flag any conflicts between context files and codebase state
   - Suggest actions if manual intervention is needed

## Output

Print a concise summary:

```text
Flow Refresh Complete
─────────────────────
Since last session (abc1234, 2 days ago):
  • 3 commits by other contributors
  • pyproject.toml: added `httpx` dependency
  • tech-stack.md: updated
  • workflow.md: revalidated
  • auth flow: 2 tasks completed externally
  • spec.md: synced with Beads

No conflicts detected.
```

## Guard Rails

- Never overwrite manual edits to spec.md — merge changes, don't replace
- If conflicts are detected, present both versions and ask the user to resolve
- Always run `/flow:sync` at the end to ensure spec.md reflects final state
- Log the refresh action through the active backend's note/comment mechanism
- Treat workflow drift as real refresh work, not optional cleanup
