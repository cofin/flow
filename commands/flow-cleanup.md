---
description: Groundskeeper: Global maintenance and integrity check of Flow specifications
allowed-tools: Read, Glob, Grep, Bash
---

# Flow Cleanup

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Performing global maintenance and integrity checks on Flow specifications and task files.

## The Cleanup Mandate

**CRITICAL:** The Flow specifications directory must be in a clean, consistent, and fully validated state.

---

## Phase 1: Reconcile All Specs

Run the sync reconciler on the active flow (if any) or execute it to ensure all task files are aligned with their respective spec plans:

```bash
python3 tools/sync.py
```

## Phase 2: Run Integrity Check

Run the repository validation tool. This checks OKF YAML schemas, verifies that referenced files exist for closed tasks, checks that relative links are valid in completed flows, and flags any **orphaned task files** (files under `tasks/*.md` that are no longer listed in `spec.md` plans):

```bash
SKIP_CLAUDE_VALIDATE=1 python3 tools/validate.py
```

If validation fails, resolve the reported violations (e.g. delete orphaned task files, fix broken links, or add missing required frontmatter).

## Phase 3: Identify Completed Flows for Archiving

Scan `.agents/bundles/specs/*/spec.md` for flows that have frontmatter `status: completed`.
For each completed flow found, prompt the developer:

> Propose archiving completed flow '{flow_id}'?
> A) Yes - I will run /flow:archive {flow_id}
> B) No - Keep it active on disk
