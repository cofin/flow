# Flow Revert

Git-aware revert of tracks, phases, or tasks.

## Usage
- `/flow:revert task` - Revert last task
- `/flow:revert phase` - Revert current phase
- `/flow:revert track {track_id}` - Revert entire track

## Phase 1: Identify Scope

### 1.1 Read Current State
```bash
cat .agent/specs/{track_id}/implement_state.json
```

### 1.2 Gather Commits
For task: last commit
For phase: all commits in current phase
For track: all commits since track started

```bash
git log --oneline --since="{track_start_date}"
```

## Phase 2: Confirm Revert

```
Revert Scope: {task|phase|track}

Commits to revert:
- abc1234: feat(auth): add login endpoint
- def5678: test(auth): add login tests

Files affected:
- src/auth/login.ts
- tests/auth/login.test.ts

This will:
- Reset git to {commit_sha}
- Update plan.md status to [ ]
- Reopen Beads tasks

Proceed? [y/N]
```

## Phase 3: Execute Revert

### 3.1 Git Revert
```bash
git revert --no-commit {commit_sha}..HEAD
git commit -m "revert: {scope} - {reason}"
```

### 3.2 Update Plan
Reset task status: `[x]` → `[ ]`

### 3.3 Reopen Beads Tasks
```bash
bd update {task_id} --status pending
```

### 3.4 Clear State
Update `implement_state.json` to previous checkpoint.

## Phase 4: Verify

```bash
git status
npm test
```

## Final Output

```
Revert Complete

Scope: {scope}
Commits Reverted: {count}
Revert Commit: {new_sha}

Plan updated: {count} tasks reset to pending
Beads updated: {count} tasks reopened

Resume with: /flow:implement {track_id}
```
