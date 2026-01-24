---
description: Update spec or plan when implementation reveals issues
argument-hint: <track_id>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Flow Revise

Revising track: **$ARGUMENTS**

## Phase 1: Load Current State

Read:
- `.agent/specs/{track_id}/spec.md`
- `.agent/specs/{track_id}/plan.md`
- `.agent/specs/{track_id}/learnings.md`

---

## Phase 2: Identify Revision Type

Ask user:

> **What needs to be revised?**
> - Spec - Requirements changed
> - Plan - Tasks need adjustment
> - Both - Significant pivot

---

## Phase 3: Document Reason

> **Why is this revision needed?**
> (This will be logged in revisions.md)

---

## Phase 4: Make Changes

Based on revision type:

### Spec Revision
1. Open spec.md in editor mode
2. User makes changes
3. Validate acceptance criteria still testable

### Plan Revision
1. Show current task status
2. Allow adding/removing/reordering tasks
3. Update task numbers and dependencies

---

## Phase 5: Log Revision

Append to `.agent/specs/{track_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {spec|plan|both}
**Reason:** {user provided reason}

**Changes:**
- {description of change}

**Impact:**
- Tasks affected: {list}
- Completion estimate change: {if any}
```

---

## Phase 6: Sync Beads

If plan changed:
```bash
bd update {affected_task_ids} --notes "Revised: {reason}"
```

---

## Phase 7: Commit Revision

```bash
git add .agent/specs/{track_id}/
git commit -m "flow(revise): {track_id} - {brief description}"
```

---

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **BEADS SYNC** - Update affected tasks
3. **PRESERVE HISTORY** - Never delete, only append
