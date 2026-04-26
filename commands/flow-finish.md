---
description: Complete flow work - verify, review, merge/PR/keep/discard
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Flow Finish

Completing flow: **$ARGUMENTS**

## The Closer Mandate

**CRITICAL:** `/flow:finish` ensures the Beads source of truth is finalized and the human view is synced before the flow is integrated.

---

## 3.0 Verification & Sync

1. **Final Verification**: Run all tests and coverage.
2. **Beads Finalization**: Close all remaining tasks.
3. **Sync**: Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow:sync` to update `spec.md` with final commit SHAs and statuses.

---

## 7.0 Cleanup

- **Close Epic**: `bd close <epic_id> --reason "Flow finished and merged."`
- **Archive**: Recommend `/flow:archive` to move artifacts to history.
