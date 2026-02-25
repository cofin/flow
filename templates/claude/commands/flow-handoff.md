---
description: Create context handoff for session transfer
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Bash
---

# Flow Handoff

Creating handoff for: **$ARGUMENTS**

## Phase 1: Analyze Progress

1. Read current spec.md status
2. Calculate completion percentage
3. Identify current phase and task
4. Check for blockers

---

## Phase 2: Gather Context

Collect:
- Recent git history for flow
- Learnings from learnings.md
- Any notes from Beads
- Files modified in current phase

---

## Phase 3: Generate Handoff Document

Create `.agent/specs/{flow_id}/handoff_{N}.md`:

```markdown
# Handoff: {flow_id}

**Created:** {timestamp}
**Handoff Number:** {N}
**Author Session:** {if available}

## Current Status

**Phase:** {N} - {phase name}
**Task:** {current task number and description}
**Progress:** {completed}/{total} ({%})

## Context Summary

{Brief summary of what's been done}

## Recent Commits

| SHA | Message | Files |
|-----|---------|-------|
| abc1234 | feat(auth): Add login | 3 files |

## Key Learnings

{Important patterns/gotchas discovered}

## Blockers

{Any current blockers}

## Next Steps

1. {Immediate next task}
2. {Following tasks}

## Files to Review

{List of key files for context}

## Beads Recovery

To resume in new session:
```bash
br status                          # Workspace overview
br ready                           # List unblocked tasks
br list --status in_progress       # Resume active work
br show {epic_id}
```

## Notes for Next Session

{Any additional context}
```

---

## Phase 4: Update State

Save to `implement_state.json`:

```json
{
  "handoff_created": "timestamp",
  "handoff_number": N,
  "current_phase": N,
  "current_task": N
}
```

---

## Phase 5: Commit Handoff

```bash
git add .agent/specs/{flow_id}/
git commit -m "flow(handoff): {flow_id} handoff {N}"
```

---

## Final Summary

```
Handoff Created

Flow: {flow_id}
Handoff: handoff_{N}.md
Progress: {completed}/{total} tasks

To resume in new session:
1. Run `br status` and `br ready` to load Beads context
2. Read .agent/specs/{flow_id}/handoff_{N}.md
3. Run `/flow-implement {flow_id}` to continue
```

---

## Critical Rules

1. **COMPREHENSIVE** - Include all needed context
2. **BEADS INSTRUCTIONS** - Include recovery commands
3. **COMMIT HANDOFF** - Preserve in git
