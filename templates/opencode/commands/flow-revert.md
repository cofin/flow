# Flow Revert

Git-aware revert of tracks, phases, or tasks.

## Usage
- `/flow:revert task` - Revert last task
- `/flow:revert phase` - Revert current phase
- `/flow:revert track {track_id}` - Revert entire track

## Phase 1: Identify Scope

Gather commits to revert based on scope.

## Phase 2: Confirm Revert

```
Revert Scope: {scope}

Commits to revert:
- {list}

Proceed? [y/N]
```

## Phase 3: Execute Revert

```bash
git revert --no-commit {commits}
git commit -m "revert: {scope}"
```

Update plan.md status to `[ ]`

```bash
bd update {task_id} --status pending
```

## Final Output

```
Revert Complete

Commits Reverted: {count}
Tasks Reset: {count}

Resume with: /flow:implement {track_id}
```
