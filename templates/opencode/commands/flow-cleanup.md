---
description: "Groundskeeper: Global maintenance and integrity check of Flow specifications"
---

# Flow Cleanup

Performing global maintenance and integrity checks on Flow specifications and task files.

## The Cleanup Mandate

**CRITICAL:** The Flow specifications directory must be in a clean, consistent, and fully validated state.

---

## Phase 1: Reconcile All Specs on Disk

As the AI agent, you must execute the reconciliation algorithm directly:

1. **Scan Specs Directory**:
   - List all directories under `.agents/bundles/specs/`.
   - For each directory, if it contains a `spec.md` file, run the **Reconciliation Algorithm** (described in the `/flow-sync` command) to ensure task checklist items and task metadata files are fully synchronized.

## Phase 2: Integrity Validation

Execute the repository integrity checks manually:

1. **Verify Orphaned Task Files**:
   - Scan `.agents/bundles/specs/*/tasks/*.md`.
   - Ensure that every task file has a corresponding checklist task in its parent `spec.md`.
   - If any task file is orphaned (not defined in `spec.md`), delete it or flag a validation violation.
2. **Verify File and Test Paths**:
   - For each task file in state `closed` in any active flow, read `files:` and `tests:` arrays.
   - Verify that all listed paths exist in the workspace. If any path does not exist, report a validation violation.
3. **Verify Markdown Links**:
   - Scan all relative links in `spec.md` files and verify they resolve to existing files or directories in the workspace.

If validation fails, resolve the reported violations (e.g. delete orphaned task files, fix broken links, or add missing required frontmatter).

## Phase 3: Identify Completed Flows for Archiving

Scan `.agents/bundles/specs/*/spec.md` for flows that have frontmatter `state: completed`.
For each completed flow found, prompt the developer:

> Propose archiving completed flow '{flow_id}'?
> A) Yes - I will run /flow-archive {flow_id}
> B) No - Keep it active on disk
