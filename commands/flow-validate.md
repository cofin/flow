---
description: Validate project integrity and fix issues
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Validate

> Lifecycle skill: use `flow-setup` through the `flow` router.

Validate Flow project integrity and optionally fix issues. All checks are file checks — read the bundle files directly.

## Phase 1: Directory Structure

Check required files exist:

- [ ] `.agents/bundles/index.md` (bundle root; frontmatter carries `okf_version`)
- [ ] `.agents/bundles/product/product.md`
- [ ] `.agents/bundles/product/tech-stack.md`
- [ ] `.agents/bundles/knowledge/workflow.md`
- [ ] `.agents/bundles/knowledge/patterns.md`
- [ ] `.agents/bundles/specs/` directory

---

## Phase 2: Spec Integrity

For each flow directory under `.agents/bundles/specs/<flow_id>/`:

1. Verify `spec.md` exists
2. Verify spec frontmatter: `type: Spec`, `flow_id` equals the directory name, `title`, `state` in `planned|active|completed|archived`, valid `created_at`/`updated_at`
3. Verify Implementation Plan checklist markers are valid: `[ ]`, `[~]`, `[x]`, `[!]`, `[-]`

---

## Phase 3: Task Integrity

For each task file under `.agents/bundles/specs/<flow_id>/tasks/*.md`:

- Frontmatter fields present: `type: Task`, `id`, `title`, `state`, `depends_on`, `created_at`, `updated_at`
- `id` matches `<flow_id>:<short_id>` and `<short_id>` matches the filename
- `state` in `open|in_progress|closed|blocked|skipped` (workflow state lives in `state:`, never `status:`)
- `depends_on` uses short ids that resolve to task files in the same flow
- `closed` tasks carry a `commit:` SHA that exists in git history

---

## Phase 4: Checklist/Task Agreement

For each flow:

1. Every checklist entry in `spec.md` has a matching file in `tasks/`
2. No orphaned task files without a checklist entry
3. Each marker matches its task file's `state` (`open` → `[ ]`, `in_progress` → `[~]`, `closed` → `[x]` + `[sha]`, `blocked` → `[!]`, `skipped` → `[-]`); the task file is authoritative on conflict

---

## Phase 5: Report

```text
Flow Validation Report

=== Structure ===
[x] .agents/bundles/ directory complete
[x] index.md carries okf_version

=== Flows ===
[x] auth: 12 tasks, 5 closed
[!] dark-mode: Missing spec.md

=== Issues Found ===
1. dark-mode: Missing spec.md
2. auth: Task 3 closed but no commit SHA

=== Recommendations ===
- Run with --fix to auto-repair issues
- Manually review dark-mode
```

---

## Phase 6: Auto-Fix (if --fix)

If `--fix` argument provided:

- Create missing files from templates
- Scaffold task files for checklist entries missing one (default `Task` frontmatter)
- Reconcile checklist markers with task file `state` (task file wins)

---

## Critical Rules

1. **NON-DESTRUCTIVE** - Only report by default
2. **FIX ON REQUEST** - Only modify with --fix flag
3. **COMPREHENSIVE** - Check everything
