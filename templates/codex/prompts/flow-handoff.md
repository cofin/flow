# Flow Handoff

Create context handoff document for session transfer.

## Usage
`/flow:handoff`

## Phase 1: Gather Current State

### 1.1 Active Flow
Read current in-progress flow from `.agent/flows.md`

### 1.2 Current Task
```bash
br ready
br show {current_task_id}
```

### 1.3 Recent Activity
```bash
git log --oneline -10
```

## Phase 2: Compile Handoff

Create `.agent/handoff.md`:

```markdown
# Session Handoff

**Generated:** {timestamp}
**Flow:** {flow_id}
**Phase:** {current_phase}
**Task:** {current_task}

## Context

### What I Was Working On
{description of current work}

### Progress Made
- {completed item 1}
- {completed item 2}

### Current State
- Tests: {passing/failing}
- Coverage: {percentage}
- Files modified: {list}

## Next Steps

1. {immediate next action}
2. {following action}

## Key Decisions Made
- {decision 1}: {rationale}
- {decision 2}: {rationale}

## Open Questions
- {question 1}
- {question 2}

## Beads Context
```bash
br status                     # Workspace overview
br ready                      # Unblocked tasks
br list --status in_progress  # Active work
```

## Commands to Resume
```bash
br status
br list --status in_progress
# Then run:
/flow:implement {flow_id}
```
```

## Phase 3: Sync to Beads

```bash
br update {task_id} --notes "HANDOFF: {summary}"
```

## Final Output

```
Handoff Created: .agent/handoff.md

To resume in new session:
1. Read .agent/handoff.md
2. Run: br status && br list --status in_progress
3. Run: /flow:implement {flow_id}
```
