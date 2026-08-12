---
description: Update spec/plan when implementation reveals issues
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Flow Revise

> Lifecycle skill: use `flow-planning` through the `flow` router.

Revising flow: **$ARGUMENTS**

## Phase 1: Load Current State

Read:

- `.agents/bundles/specs/{flow_id}/spec.md`
- `.agents/bundles/specs/{flow_id}/tasks/*.md`
- `.agents/bundles/specs/{flow_id}/learnings.md`

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

1. Show current task status from task files
2. Allow adding/removing/reordering tasks
3. Update task numbers and dependencies

---

## Phase 5: Log Revision

Append to `.agents/bundles/specs/{flow_id}/revisions.md`:

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

## Phase 6: Update Task Files

If plan changed:

- **Affected tasks:** Append to each affected task file's `## Notes & Discoveries` section: `- [timestamp] Revised: {reason}`. Refresh `updated_at`.
- **New tasks:** Add a `- [ ] Task {short_id}: {title}` line to the spec's Implementation Plan, then create `tasks/{short_id}.md` with full frontmatter (`type: Task`, `id: {flow_id}:{short_id}`, `title`, `state: open`, `depends_on`, `files`, `tests`, `created_at`, `updated_at`, `commit: null`), a body describing what changed and why this task is needed, and a note: `- [timestamp] Added during revision. Reason: {reason}. Created by /flow-revise on {date}`.
- **Removed tasks** (not started): set `state: skipped` in the task file and note `- [timestamp] Removed in revision`. Never delete task files.

**CRITICAL:** Always include a description of what changed and why when creating task files, plus the revision note.

---

### Markdown Sync

**CRITICAL:** Do NOT hand-edit status markers in spec.md. Run `/flow-sync` (reconcile checklist markers with task-file `state`) after task files change.

## Phase 8: Commit Revision

```bash
git add .agents/bundles/specs/{flow_id}/
git commit -m "chore(revise): {flow_id} - {brief description}"
```

---

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **TASK FILES FIRST** - Update task files before reconciling checklist markers
3. **PRESERVE HISTORY** - Never delete, only append
