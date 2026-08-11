---
description: Display progress overview dashboard for active flows
allowed-tools: Read, Glob, Grep, Bash
---

# Flow Status

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Displaying progress dashboard for active flows.

## The Dashboard Mandate

**CRITICAL:** `/flow:status` is the developer dashboard. It aggregates status metrics and notes from local task markdown files under `.agents/bundles/specs/*/tasks/*.md`.

---

## Phase 1: Run Dashboard Script

Execute the developer status dashboard tool to aggregate and display active flows, ready queues, blocked queues, and recent notes:

```bash
python3 tools/status.py
```

If the dashboard shows any out-of-sync indicators or if you have recently modified task files directly, run `/flow:sync` to reconcile them first.
