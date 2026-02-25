# Flow Handoff

Create context handoff document for session transfer.

## Phase 1: Gather Current State

```bash
br ready
br show {current_task_id}
git log --oneline -10
```

## Phase 2: Compile Handoff

Create `.agent/handoff.md`:

```markdown
# Session Handoff

**Generated:** {timestamp}
**Flow:** {flow_id}
**Task:** {current_task}

## What I Was Working On
{description}

## Progress Made
- {item 1}
- {item 2}

## Next Steps
1. {action 1}
2. {action 2}

## Commands to Resume
```bash
br prime
/flow:implement {flow_id}
```
```

## Phase 3: Sync to Beads

```bash
br update {task_id} --notes "HANDOFF: {summary}"
```
