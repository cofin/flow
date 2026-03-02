---
name: flow-revert
description: "Git-aware revert of flows, phases, or tasks"
---

# Flow Revert

Git-aware revert of flows, phases, or tasks.

## Usage
- `$flow:revert task` - Revert last task
- `$flow:revert phase` - Revert current phase
- `$flow:revert flow {flow_id}` - Revert entire flow

## Phase 1: Identify Scope

### 1.1 Read Current State
```bash
cat .agent/specs/{flow_id}/implement_state.json
```

### 1.2 Gather Commits
For task: last commit
For phase: all commits in current phase
For flow: all commits since flow started

```bash
git log --oneline --since="{flow_start_date}"
```

## Phase 2: Confirm Revert

```
Revert Scope: {task|phase|flow}

Commits to revert:
- abc1234: feat(auth): add login endpoint
- def5678: test(auth): add login tests

Files affected:
- src/auth/login.ts
- tests/auth/login.test.ts

This will:
- Reset git to {commit_sha}
- Update spec.md status to [ ]
- Reopen Beads tasks

Proceed? [y/N]
```

## Phase 3: Execute Revert

### 3.1 Git Revert
```bash
git revert --no-commit {commit_sha}..HEAD
git commit -m "revert: {scope} - {reason}"
```

### 3.2 Reopen Beads Tasks (Source of Truth)
```bash
br update {task_id} --status open
```

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

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

Resume with: $flow:implement {flow_id}
```
