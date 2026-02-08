---
name: flow-handoff
---

# Flow Handoff

Create context handoff document for session transfer.

## Usage
`/flow:handoff`

## Phase 1: Gather Current State

### 1.1 Active Flow
Read current in-progress flow from `.agent/flows.md`

### 1.2 Current Task
```bash
bd ready
bd show {current_task_id}
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
bd prime
bd ready
```

## Commands to Resume
```bash
bd prime
# Then run:
/flow:implement {flow_id}
```
```

## Phase 3: Sync to Beads

```bash
bd update {task_id} --notes "HANDOFF: {summary}"
```

## Final Output

```
Handoff Created: .agent/handoff.md

To resume in new session:
1. Read .agent/handoff.md
2. Run: bd prime
3. Run: /flow:implement {flow_id}
```
