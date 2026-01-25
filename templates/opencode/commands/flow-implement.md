# Flow Implement

Execute tasks from a track's plan using TDD workflow.

## Usage
`/flow:implement {track_id}` or `/flow:implement` (uses current track)

## Phase 1: Load Track Context

1. Read `.agent/specs/{track_id}/plan.md`
2. Read `.agent/specs/{track_id}/spec.md`
3. Read `.agent/patterns.md`
4. Load Beads context: `bd prime`

## Phase 2: Select Task

### 2.1 Check for Resume State
```bash
cat .agent/specs/{track_id}/implement_state.json 2>/dev/null
```

### 2.2 Find Next Task
Use Beads to find unblocked tasks:
```bash
bd ready
```

## Phase 3: Task Execution (TDD)

### 3.1 Mark In Progress
Update plan.md: `[ ]` → `[~]`

```bash
bd update {task_id} --status in_progress
```

### 3.2 Red Phase - Write Failing Tests
1. Create/update test file
2. Write tests that define expected behavior
3. Run tests to confirm they fail

### 3.3 Green Phase - Implement
1. Write minimum code to pass tests
2. Run tests until green

### 3.4 Refactor Phase
1. Clean up while tests pass
2. Apply patterns from patterns.md

### 3.5 Verify Coverage
Target: 80% minimum

## Phase 4: Commit

```bash
git add -A
git commit -m "<type>(<scope>): <description>"
```

## Phase 5: Update Status

### 5.1 Update Plan
Mark complete with commit SHA:
```markdown
- [x] Task 1.1: Description [abc1234]
```

### 5.2 Sync to Beads
```bash
bd close {task_id} --reason "commit: {sha}"
```

### 5.3 Log Learnings
Add discoveries to `.agent/specs/{track_id}/learnings.md`

## Phase 6: Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **BEADS SYNC** - Keep task status updated
4. **LOG LEARNINGS** - Capture patterns as you go
5. **LOCAL ONLY** - Never push automatically
