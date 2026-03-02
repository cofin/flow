---
description: Update spec/plan when implementation reveals issues
agent: flow
---

# Flow Revise

Revising flow: $ARGUMENTS

## Phase 1: Load Current State

Read `.agent/specs/{flow_id}/`:
- spec.md
- learnings.md

## Phase 2: Identify Revision Type

Ask user: What section of spec.md needs revision?

## Phase 3: Document Reason

Log why revision is needed.

## Phase 4: Make Changes

Update spec.md as needed.

## Phase 5: Log Revision

Append to `.agent/specs/{flow_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {requirements|plan|both}
**Reason:** {reason}
**Changes:** {description}
```

## Phase 6: Sync Beads

```bash
br update {affected_task_ids} --notes "Revised: {reason}"

# If NEW tasks added:
br create "{new_task}" --parent {epic_id} -p 2 \
  --description="{what_and_why}"
br update {new_task_id} --notes "Added during revision. Created by /flow:revise"
```

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **BEADS FIRST** - Update Beads before syncing markdown
4. **PRESERVE HISTORY** - Never delete, only append
