---
type: Spec
flow_id: demo-flow
title: Demo Flow
state: active
plan_revision: 2
plan_commit: null
state_revision: 3
current_task: "1.2"
last_operation: 20260814T120000Z-flow-executor-claim-1-2-00
operation_targets: ["1.2"]
last_verified_checkpoint: "task:1.1@abc1234"
created_at: 2026-08-14T11:00:00Z
updated_at: 2026-08-14T12:00:00Z
---

# Demo Flow

## Implementation Plan

- [x] Task 1.1: Foundation [abc1234]
- [~] Task 1.2: Continue work

## Continuity Snapshot

- **Active flow:** `demo-flow` (`active`)
- **Current task/claim:** Task `1.2`, claimed by `flow-executor`
- **Last verified checkpoint:** `task:1.1@abc1234`
- **Decisions:** keep Markdown canonical
- **Recent discoveries:** none
- **Blockers/unblock conditions:** none
- **Next exact step:** execute the first numbered worksheet step
- **Plan identity:** revision `2`; `plan_commit: null` in frontmatter and every task
- **State identity:** revision `3`; `last_operation: 20260814T120000Z-flow-executor-claim-1-2-00`; `operation_targets: ["1.2"]`
- **Relevant rules/knowledge:** `AGENTS.md`
