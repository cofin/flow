# Flow Cleanup Reference

Global maintenance and optimization of the `.agents/` directory structure to ensure integrity and consistency.

---

## 1.0 THE CLEANUP MANDATE

The Groundskeeeping routine ensures that:

- All task files match their spec plans.
- No orphaned task files exist in spec directories.
- Frontmatter schemas and Markdown link targets are correct.
- Completed specs are identified for archiving.

---

## 2.0 WORKFLOW

### Phase 1: Reconcile Specs

Run the global sync reconciler to update all active specifications with their task statuses:

```bash
python3 tools/sync.py
```

### Phase 2: Run Integrity Check

Run the validator script. This validates frontmatter YAML structure, checks that referenced files exist for closed tasks, checks that links resolve for completed flows, and checks for **orphaned task files** (files under `tasks/*.md` that do not exist in `spec.md` checklist plans):

```bash
SKIP_CLAUDE_VALIDATE=1 python3 tools/validate.py
```

If validation fails:

- Review the violations list.
- Prune/delete any orphaned task files.
- Resolve any broken links or missing required frontmatter fields.

### Phase 3: Archive completed flows

1. Scan `.agents/bundles/specs/*/spec.md` files.
2. Filter for specs containing `status: completed`.
3. Propose archiving each completed flow:
   - Suggest running the `/flow:archive <flow_id>` slash command to move the spec directory to the archive store and elevate patterns.

---

## 3.0 CRITICAL RULES

1. **NO ORPHANED TASKS** - Never leave task files inside `tasks/` that are not listed in the main `spec.md` implementation plan.
2. **VALIDATION PASS REQUIRED** - A cleanup is not complete unless `tools/validate.py` passes with zero violations.
3. **DO NOT DESTRUCTIVELY CLEAN ACTIVE WORK** - Only archive flows that are fully complete and verified.
