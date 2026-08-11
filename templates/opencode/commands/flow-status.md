---
description: Display progress overview dashboard for active flows
---

# Flow Status

Display progress overview dashboard for all active flows.

## Phase 1: Run Dashboard Script

Execute the developer status dashboard tool to aggregate and display active flows, ready queues, blocked queues, and recent notes:

```bash
python3 tools/status.py
```

If the dashboard shows any out-of-sync indicators or if you have recently modified task files directly, run `/flow-sync` to reconcile them first.
