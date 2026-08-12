---
description: Update spec/plan when implementation reveals issues
agent: flow
---

# Flow Revise

Revising flow: $ARGUMENTS

## Phase 1: Load Current State

Read `.agents/bundles/specs/{flow_id}/`:

- spec.md
- tasks/*.md
- learnings.md

## Phase 2: Identify Revision Type

Ask user:

> **What needs to be revised?**
>
> - Spec - Requirements changed
> - Plan - Tasks need adjustment
> - Both - Significant pivot

## Phase 3: Document Reason

Log why revision is needed (this will be logged in revisions.md).

## Phase 4: Make Changes

Based on revision type:

### Spec Revision

1. Update spec.md requirements
2. Validate acceptance criteria still testable

### Plan Revision

1. Show current task status from task files
2. Allow adding/removing/reordering tasks
3. Update task numbers and dependencies

## Phase 5: Log Revision

Append to `.agents/bundles/specs/{flow_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {spec|plan|both}
**Reason:** {reason}

**Changes:**
- {description of change}

**Impact:**
- Tasks affected: {list}
```

## Phase 6: Update Task Files

If plan changed:

- **Affected tasks:** Append to each affected task file's `## Notes & Discoveries` section: `- [timestamp] Revised: {reason}`. Refresh `updated_at`.
- **New tasks:** Add a `- [ ] Task {short_id}: {title}` line to the spec's Implementation Plan, then create `tasks/{short_id}.md` with full frontmatter (`type: Task`, `id: {flow_id}:{short_id}`, `title`, `state: open`, `depends_on`, `files`, `tests`, `created_at`, `updated_at`, `commit: null`), a body describing what changed and why this task is needed, and a note: `- [timestamp] Added during revision. Reason: {reason}. Created by /flow-revise on {date}`.
- **Removed tasks** (not started): set `state: skipped` in the task file and note `- [timestamp] Removed in revision`. Never delete task files.

**CRITICAL:** Always include a description of what changed and why when creating task files, plus the revision note.

### Markdown Sync

**CRITICAL:** Do NOT hand-edit status markers in spec.md. Run `/flow-sync` (reconcile checklist markers with task-file `state`) after task files change.

## Phase 7: Commit Revision

```bash
git add .agents/bundles/specs/{flow_id}/
git commit -m "chore(revise): {flow_id} - {brief description}"
```

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **TASK FILES FIRST** - Update task files before reconciling checklist markers
3. **PRESERVE HISTORY** - Never delete, only append
