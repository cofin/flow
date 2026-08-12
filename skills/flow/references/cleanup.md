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
As the AI agent, you must execute the reconciliation algorithm directly (as detailed in `/flow:sync` instructions) for all active spec directories.

### Phase 2: Run Integrity Check

Perform validation checks manually using your file-manipulation tools:

1. **Verify Orphaned Task Files**: Scan `.agents/bundles/specs/*/tasks/*.md` and ensure every task file has a corresponding checklist task in its parent `spec.md`.
2. **Verify File and Test Paths**: For each task file in status `closed` in any active spec, verify that all paths in its `files` and `tests` arrays exist on disk.
3. **Verify Markdown Links**: Verify that all relative links in `spec.md` files resolve to existing files or directories in the workspace.

If validation fails:

- Review the violations list.
- Prune/delete any orphaned task files.
- Resolve any broken links or missing required frontmatter fields.

### Phase 3: Archive completed flows

1. Scan `.agents/bundles/specs/*/spec.md` files.
2. Filter for specs containing `state: completed`.
3. Propose archiving each completed flow:
   - Suggest running the `/flow:archive <flow_id>` slash command to move the spec directory to the archive store and elevate patterns.

---

## 3.0 CRITICAL RULES

1. **NO ORPHANED TASKS** - Never leave task files inside `tasks/` that are not listed in the main `spec.md` implementation plan.
2. **VALIDATION PASS REQUIRED** - A cleanup is not complete unless all manual validation checks pass with zero violations.
3. **DO NOT DESTRUCTIVELY CLEAN ACTIVE WORK** - Only archive flows that are fully complete and verified.
