---
description: Reconcile flow specifications and task files (Beads-free OKF bundle)
---

# Flow Sync

Reconcile flow specifications and task files for flow: **$ARGUMENTS**

## Reconcile Protocol

Run the unified python sync reconciler to synchronize task statuses and auto-scaffold missing task files.

```bash
# If a flow ID argument is provided ($ARGUMENTS)
python3 tools/sync.py "$ARGUMENTS"

# If no argument is provided
python3 tools/sync.py
```

## Integrity Validation

Run the repository validation script to check OKF frontmatter schemas, link resolution, and referenced files:

```bash
SKIP_CLAUDE_VALIDATE=1 python3 tools/validate.py
```
