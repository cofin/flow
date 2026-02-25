---
description: Update spec or plan when implementation reveals issues
agent: flow
---

# Flow Revise

Revising flow: $ARGUMENTS

## Phase 1: Load Current State

Read `.agent/specs/{flow_id}/`:
- spec.md
- plan.md
- learnings.md

## Phase 2: Identify Revision Type

Ask user: Spec, Plan, or Both?

## Phase 3: Document Reason

Log why revision is needed.

## Phase 4: Make Changes

Update spec.md and/or plan.md as needed.

## Phase 5: Log Revision

Append to `.agent/specs/{flow_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {spec|plan|both}
**Reason:** {reason}
**Changes:** {description}
```

## Phase 6: Sync Beads

```bash
br update {affected_task_ids} --notes "Revised: {reason}"

# If NEW tasks added:
br create "{new_task}" --parent {epic_id} -p 2 \
  --description="{what_and_why}" \
  --notes="Added during revision. Created by /flow:revise"
```

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **BEADS SYNC** - Update affected tasks
3. **PRESERVE HISTORY** - Never delete, only append
