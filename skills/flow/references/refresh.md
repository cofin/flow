# /flow:refresh — Sync Context with Codebase

## Purpose

Refresh the flow's context files by re-scanning the codebase and updating the `.agents/bundles/` metadata to reflect the current state. Use this when returning to a project after external changes (other contributors, CI, dependency updates) or when context files feel stale.

## When to Use

- Resuming work after pulling upstream changes
- After another developer merged PRs that affect the current flow
- When `.agents/bundles/` metadata is out of sync with actual project state
- After dependency updates or refactors outside of flow workflow
- At the start of a new session when the bundle files look stale

## Workflow

1. **Read current context**
   - Load `.agents/bundles/index.md`, `.agents/bundles/product/tech-stack.md`, `.agents/bundles/knowledge/workflow.md`
   - Identify active flows by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active` (or `planned`)
   - Load the active flow's `spec.md` and `tasks/*.md`; use the spec's `updated_at` as the last-sync baseline

2. **Scan codebase for drift**
   - Check git log since last known commit
   - Identify new/modified/deleted files relevant to active flows
   - Detect dependency changes (pyproject.toml, Cargo.toml, package.json)
   - Detect tech stack changes (new frameworks, removed packages)
   - Inspect workflow drift across `Makefile`, `justfile`, `Taskfile.yml`, `package.json`, `pyproject.toml`, `Cargo.toml`, `.pre-commit-config.yaml`, and CI files
   - Compare those command surfaces with `.agents/bundles/knowledge/workflow.md`

3. **Update context files**
   - Refresh `.agents/bundles/product/tech-stack.md` if dependencies changed
   - Update `.agents/bundles/knowledge/patterns.md` if new patterns detected in recent commits
   - Prompt to revalidate `.agents/bundles/knowledge/workflow.md` when canonical commands or ignore policy drifted
   - Prefer repo-native aggregate commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, and pre-commit entrypoints when updating workflow guidance
   - If tasks were completed externally (commits reference task ids), set `state: closed` and `commit: <sha>` in the affected task files
   - Refresh `.agents/bundles/index.md` with any structural changes

4. **Reconcile spec and tasks**
   - Run the `/flow:sync` reconciliation inline: update each `spec.md` checklist marker to match its task file's `state`, appending commit SHAs for closed tasks
   - The task file is authoritative on conflict

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
  • spec.md: reconciled with task files

No conflicts detected.
```

## Guard Rails

- Never overwrite manual edits to spec.md — merge changes, don't replace
- If conflicts are detected, present both versions and ask the user to resolve
- Reconcile the checklist at the end so spec.md reflects final task state
- Record externally-detected changes as timestamped entries in the affected task files' `## Notes & Discoveries` sections
- Treat workflow drift as real refresh work, not optional cleanup
