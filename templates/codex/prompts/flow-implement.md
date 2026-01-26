# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`/flow:implement {flow_id}` or `/flow:implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Artifacts:**
    - `.agent/specs/{flow_id}/spec.md`
    - `.agent/specs/{flow_id}/plan.md`
    - `.agent/specs/{flow_id}/learnings.md`
2. **Read Project Context:** `.agent/patterns.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read `.agent/prd/<parent_id>/prd.md`.
4. **Load Beads:** `bd prime`

**CRITICAL:** Before starting, check `.gitignore`. If `.agent/` is ignored, do NOT commit changes to artifacts inside it using git. Update them on disk only.

## Phase 2: Select Task

### 2.1 Check for Resume State

```bash
cat .agent/specs/{flow_id}/implement_state.json 2>/dev/null
```

### 2.2 Find Next Task

Use Beads to find unblocked tasks:

```bash
bd ready
```

Or scan plan.md for first `[ ]` pending task.

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

```bash
# Run tests
npm test  # or pytest, cargo test, etc.
```

### 3.3 Green Phase - Implement

1. Write minimum code to pass tests
2. Run tests until green

### 3.4 Refactor Phase

1. Clean up while tests pass
2. Apply patterns from patterns.md

### 3.5 Verify Coverage

```bash
npm test -- --coverage
```

Target: 80% minimum

## Phase 4: Commit

```bash
git add -A
git commit -m "<type>(<scope>): <description>"
```

Format: conventional commits

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

If any patterns discovered, add to `.agent/specs/{flow_id}/learnings.md`

## Phase 6: Save State

Save progress to `.agent/specs/{flow_id}/implement_state.json`:

```json
{
  "current_phase": 1,
  "current_task": "1.2",
  "last_commit": "abc1234",
  "timestamp": "ISO timestamp"
}
```

## Phase 7: Phase Checkpoint

At end of each phase:

1. Run full test suite
2. Create tag: `checkpoint/{flow_id}/phase-{N}`
3. Prompt for pattern elevation
4. Ask user to verify

## Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

If continuing, loop back to Phase 2.

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **BEADS SYNC** - Keep task status updated
4. **LOG LEARNINGS** - Capture patterns as you go
5. **LOCAL ONLY** - Never push automatically
