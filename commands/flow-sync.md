---
description: Synchronize flow specifications and task files (Beads-free OKF bundle)
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Sync

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Syncing active flow state on disk: **$ARGUMENTS**

## The Sync Mandate

**CRITICAL:** `/flow:sync` reconciles the markdown task checklist in `spec.md` with the individual task files under `.agents/bundles/specs/<flow_id>/tasks/`.

---

## Phase 1: Run Reconciler Script

Run the unified python sync tool to reconcile task statuses and auto-scaffold missing task files.

```bash
# If a flow ID argument is provided ($ARGUMENTS)
python3 tools/sync.py "$ARGUMENTS"

# If no argument is provided
python3 tools/sync.py
```

## Phase 2: Run Integrity Validation

Run the repository validation script to check OKF spec/task frontmatter schemas, link resolution, and referenced files:

```bash
SKIP_CLAUDE_VALIDATE=1 python3 tools/validate.py
```

If validation fails, fix any reported formatting or schema violations in the spec or task files before proceeding.

## Phase 3: Context Drift Check

Verify if any core project configuration or dependencies have drifted since the last execution:

1. Compare dependency files (`package.json`, `pyproject.toml`, etc.) with `.agents/tech-stack.md`.
2. Inspect workflow drift across `Makefile`, `justfile`, `tasks.json`, etc.
3. If drift is detected, report to the developer and request validation of `.agents/workflow.md`.
