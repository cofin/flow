
# Flow Revert

Git-aware revert of flows, phases, or tasks.

## Usage

- `flow-revert task` - Revert last task
- `flow-revert phase` - Revert current phase
- `flow-revert flow {flow_id}` - Revert entire flow

## Phase 1: Identify Scope

### 1.1 Read Current State

Read the spec file `.agents/bundles/specs/{flow_id}/spec.md` and task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` to determine active/completed tasks.

### 1.2 Gather Commits

- **For Task Revert**: Read the commit SHA from the target task's file (e.g. `tasks/{task_id}.md`) frontmatter `commit: <sha>`.
- **For Phase Revert**: Read the commit SHAs from all task files in the target phase that have `status: closed`.
- **For Flow Revert**: Read the commit SHAs from all task files under `tasks/*.md` that have `status: closed`.

## Phase 2: Confirm Revert

```text
Revert Scope: {task|phase|flow}

Commits to revert:
- abc1234: feat(auth): add login endpoint
- def5678: test(auth): add login tests

Files affected:
- src/auth/login.ts
- tests/auth/login.test.ts

This will:
- Run git revert on the resolved commit SHAs
- Reset task status to open and commit to null in task files

Proceed? [y/N]
```

## Phase 3: Execute Revert

### 3.1 Git Revert

```bash
git revert --no-commit {commit_shas}
git commit -m "revert({scope}): {reason}"
```

### 3.2 Reset Task Metadata

For the reverted tasks, edit their task files under `tasks/*.md`:

- Set `status: open`
- Set `commit: null`

If reverting an entire flow, also update `.agents/bundles/specs/{flow_id}/spec.md` frontmatter to `status: in_progress`.

### 3.3 Sync Spec Checklist

Run the spec checklist sync command to reconcile `spec.md` checklist markers:

```bash
flow-sync {flow_id}
```

## Phase 4: Verify

```bash
git status
pytest
```

## Final Output

```text
Revert Complete

Scope: {scope}
Commits Reverted: {count}
Revert Commit: {new_sha}

Metadata updated: {count} tasks reopened
Spec checklist synchronized.

Resume with: flow-implement {flow_id}
```
