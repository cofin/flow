
# Flow Revise

Update spec or plan when implementation reveals issues.

## Usage

```text
flow-revise <flow_id>
```

## Workflow

### Phase 1: Load Current State

Read `.agents/bundles/specs/{flow_id}/`:

- spec.md
- tasks/*.md
- learnings.md

### Phase 2: Identify Revision Need (Critical Thinking)

Follow the **Critical Thinking Iron Law** to evaluate the implementation issue:

- **EVALUATE ACCURACY** — What exactly is failing? Read the code/logs.
- **EVALUATE COMPLETENESS** — What was missing in the original spec?
- **EVALUATE REASONING QUALITY** — Why did the original plan fail?
- **INVESTIGATE** — Confirm root cause before proposing revision.

Ask user for guidance on the proposed revision.

### Phase 3: Document Reason

Log why revision is needed based on your investigation. **Deliver honest assessment** of the original spec's flaws.

### Phase 4: Make Changes

Update spec.md as needed.

### Phase 5: Log Revision

Append to `.agents/bundles/specs/{flow_id}/revisions.md`:

```markdown
## [YYYY-MM-DD HH:MM] Revision {N}

**Type:** {spec|plan|both}
**Reason:** {reason}
**Changes:** {description}
```

### Phase 6: Update Task Files

- **Affected tasks:** append `- [timestamp] Revised: {reason}` to each affected task file's `## Notes & Discoveries` section and refresh `updated_at`.
- **New tasks:** add a `- [ ] Task {short_id}: {title}` checklist line to the spec's Implementation Plan, then create `tasks/{short_id}.md` with full frontmatter (`type: Task`, `id: {flow_id}:{short_id}`, `title`, `state: open`, `depends_on`, `files`, `tests`, `created_at`, `updated_at`, `commit: null`), a body describing what changed and why, and a note `- [timestamp] Added during revision. Created by flow-revise`.
- **Removed tasks** (not started): set `state: skipped` and note `- [timestamp] Removed in revision`. Never delete task files.

Run `/flow:sync` (reconcile checklist markers with task-file `state`) after task files change.

## Critical Rules

1. **LOG EVERYTHING** - All revisions documented
2. **TASK FILES FIRST** - Update task files, then reconcile the checklist
3. **PRESERVE HISTORY** - Never delete, only append
