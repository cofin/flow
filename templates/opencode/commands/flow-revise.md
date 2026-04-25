---
description: Update spec/plan when implementation reveals issues
agent: flow
---

# Flow Revise

Revising flow: $ARGUMENTS

## Phase 1: Load Current State

Read `.agents/specs/{flow_id}/`:

- spec.md
- learnings.md

## Phase 2: Identify Revision Type

Ask user: What section of spec.md needs revision?

## Phase 3: Document Reason

Log why revision is needed.

## Phase 4: Make Changes

Update spec.md as needed.

## Phase 5: Log Revision

Append to `.agents/specs/{flow_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {requirements|plan|both}
**Reason:** {reason}
**Changes:** {description}
```

## Phase 6: Sync Beads

```bash
bd update {affected_task_ids} --notes "Revised: {reason}"

# If NEW tasks added:
bd create "{new_task}" --parent {epic_id} -p 2 \
  --description="{what_and_why}"
bd update {new_task_id} --notes "Added during revision. Created by /flow-revise"
```

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. It is MANDATORY that you run `/flow-sync` to update the markdown state after any task completion or status change.

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **BEADS FIRST** - Update Beads before syncing markdown
3. **PRESERVE HISTORY** - Never delete, only append
