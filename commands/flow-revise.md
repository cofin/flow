---
description: Update spec/plan when implementation reveals issues
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Flow Revise

> **Beads mode:** Skip every `bd` invocation below when the SessionStart hook reports `Beads Backend: Missing (None)` or `Disabled via plugin config (useBeads=false)`. Treat `spec.md` markers as fallback source of truth and skip `/flow:sync`. Never halt for missing Beads. See `skills/flow/references/discipline.md`.
>
> Lifecycle skill: use `flow-planning` through the `flow` router.

Revising flow: **$ARGUMENTS**

## Phase 1: Load Current State

Read:

- `.agents/specs/{flow_id}/spec.md`
- `.agents/specs/{flow_id}/learnings.md`

---

## Phase 2: Identify Revision Type

Ask user:

> **What needs to be revised?**
>
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

Append to `.agents/specs/{flow_id}/revisions.md`:

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
# Update existing tasks with revision notes
bd update {affected_task_ids} --notes "Revised: {reason}"

# If NEW tasks were added during revision, create with FULL CONTEXT:
bd create "{new_task}" --parent {epic_id} -p 2 \
  --description="{what_changed_and_why}"
bd update {new_task_id} --notes "Added during revision. Reason: {reason}. Created by /flow-revise on {date}"
```

**CRITICAL:** Always include `--description` when creating tasks, then add `--notes` via `bd update`.

---

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow-sync` to update the markdown state after task completion or status changes.

## Phase 8: Commit Revision

```bash
git add .agents/specs/{flow_id}/
git commit -m "chore(revise): {flow_id} - {brief description}"
```

---

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **BEADS FIRST** - Update Beads before syncing markdown
3. **PRESERVE HISTORY** - Never delete, only append
