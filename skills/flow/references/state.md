# Flow Direct Markdown & Git State Contract

Task worksheets (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`) and specifications (`.agents/bundles/specs/<flow_id>/spec.md`) are the sole authority for Flow state and continuity. Agents read and update these Markdown files directly using standard file tools and verify continuity against Git history (`HEAD` and task `commit` SHAs).

## Root Resolution

- `<configured-root>` is `root_directory` from `.agents/setup-state.json` (default `.agents`).
- `<bundle-root>` is `bundle_root` from `.agents/setup-state.json` (default `.agents/bundles`).
- `<flow-root>` is `<bundle-root>/specs/<flow_id>`.
- Every resolved path must stay inside the repository root, contain no `..`, and traverse no escaping symlink.

## Lifecycle State Enums & Checklist Mapping

```yaml
spec_states: [draft, planned, active, completed]
task_states: [pending, open, in_progress, completed, closed, blocked, deferred, skipped]
priorities: [P0, P1, P2, P3, P4]
default_priority: P2
verification_strategies:
  - behavior_tdd
  - regression_tdd
  - characterization
  - static_validation
  - documentation_validation
  - integration_acceptance
```

| Task `state` Frontmatter | `spec.md` Checklist Marker | Meaning |
| --- | --- | --- |
| `pending` or `open` | `- [ ] <id> — <summary> (tasks/<id>-<slug>.md)` | Ready once all `depends_on` tasks are `completed`/`closed`. |
| `in_progress` | `- [~] <id> — <summary> (tasks/<id>-<slug>.md)` | Claimed by an active executor turn. |
| `completed` or `closed` | `- [x] [<sha>] <id> — <summary> (tasks/<id>-<slug>.md)` | Verified with exit code `0` and committed at `<sha>`. |
| `blocked` | `- [!] <id> — <summary> (tasks/<id>-<slug>.md)` | Halted on a documented mismatch (`blocked_reason` + `unblock_condition`). |
| `deferred` or `skipped` | `- [-] <id> — <summary> (tasks/<id>-<slug>.md)` | Explicitly descoped or moved to a follow-up spec. |

When `spec.md` checklist markers and `tasks/<id>-<slug>.md` frontmatter disagree, the task worksheet frontmatter + Git commit history are authoritative; reconcile `spec.md` to match.

## Normative Document Schemas

### 1. Specification (`specs/<flow_id>/spec.md`)

```yaml
---
type: Spec
flow_id: user-auth
title: User Authentication
description: Repository-native JWT authentication and session middleware.
state: planned                  # draft | planned | active | completed
parent_prd: null                # <prd_id> when seeded by /flow:prd, else null
research: []                    # relative paths under specs/<flow_id>/research/
plan_revision: 1
plan_commit: null               # Git HEAD SHA stamped when plan is approved
state_revision: 0
current_task: null
last_verified_checkpoint: null
created_at: 2026-11-01T00:00:00Z
updated_at: 2026-11-01T00:00:00Z
tags: [feature, auth, security]
---
```

Required sections for a **Feature Specification (`/flow:plan`)**:

1. `## 1. Specification & Context` (`1.1 Upstream Execution Baseline`, `1.2 Code Analysis Summary` table with `path/to/file::Symbol` anchors, `1.3 Relevant Patterns` linking `.agents/bundles/knowledge/**`)
2. `## 2. Requirements` (`2.1 Functional Requirements` `R1..RN`, `2.2 Non-Functional & Safety Constraints`, `2.3 Acceptance Scenarios (Given / When / Then)`, `2.4 Alternatives Considered`)
3. `## 3. Requirement-to-Task Traceability Matrix` (`Requirement | Owning Task(s) | Verification Strategy | Canonical Test / Gate Surface`)
4. `## 4. Implementation Plan` (grouped by `### Phase 1..N` with `- [ ] <id> — <summary> (tasks/<id>-<slug>.md)` and a mandatory **Phase N Recovery Checkpoint** naming exact verification commands)
5. `## 5. Continuity Snapshot` (active state, current task, last verified checkpoint, key architectural decisions, and up to 5 newest discoveries)

Required sections for a **Master PRD (`/flow:prd`)**:

1. `## 1. North Star Goal & Context`
2. `## 2. Locked Architectural Decisions`
3. `## 3. Master Roadmap (Ordered Child Flows)` (`Chapter | Flow ID | Title | Key Deliverables | Dependencies | State`)
4. `## 4. Global Constraints (Applicable to All Child Flows)`
5. `## 5. Backlog (Deferred Items)`
6. `## Implementation Plan` & `## Continuity Snapshot`

### 2. Task Worksheet (`specs/<flow_id>/tasks/<id>-<slug>.md`)

```yaml
---
type: Task
id: user-auth:t01
title: Add JWT token signer and canonical unit tests
state: pending                  # pending | open | in_progress | completed | closed | blocked | deferred | skipped
priority: P1
verification_strategy: behavior_tdd
depends_on: []
files:
  - src/auth/tokens.py
tests:
  - tests/auth/test_tokens.py
plan_revision: 1
plan_commit: 164b07f
state_revision: 0
claimed_by: null
claimed_at: null
blocked_reason: null
unblock_condition: null
next_step: null
last_verified_at: null
last_verified_commit: null
verification_evidence: null
created_at: 2026-11-01T00:00:00Z
updated_at: 2026-11-01T00:00:00Z
commit: null
tags: [feature, auth, tdd]
---
```

Required sections in every task worksheet:

1. `## Objective` — Single vertical-slice outcome.
2. `## Context` — Verification strategy rationale, architectural invariants from `.agents/bundles/knowledge/**`, and canonical test module targets.
3. `## Steps` — Ordered steps (`1. Write failing unit tests (RED)`, `2. Implement ... (GREEN)`, `3. Refactor & verify`) anchored to `path/to/file::Symbol` (never fragile line numbers).
4. `## Verification` — Exact initial and final CLI commands and expected exit codes/diagnostics.
5. `## Acceptance Criteria` — Checkboxes (`- [ ]`) mapped to parent requirements.
6. `## Notes & Discoveries` — Append-only timestamped implementation findings (`- [YYYY-MM-DD HH:MM] ...`).

## Direct State Mutations & Continuity Recovery

1. **Approve Plan (`plan` / `revise`)**: Stamp `plan_commit: <HEAD_SHA>` and identical `plan_revision` across `spec.md` and all `tasks/<id>-<slug>.md`.
2. **Claim Task (`implement`)**: Set task `state: in_progress`, `claimed_by`, `claimed_at`, increment `state_revision`, and update `spec.md` (`state: active`, `current_task: <id>`, checklist `[~]`).
3. **Complete Task (`implement`)**: After verification exits `0`, update the task worksheet (`state: completed`, `commit: <sha>`, `last_verified_at`, `last_verified_commit`, `verification_evidence`) and `spec.md` checklist (`- [x] [<sha>] ...`) and commit the task's owned files atomically.
4. **Block Task (`implement` &rarr; `revise`)**: Without mutating production files, set task `state: blocked`, `blocked_reason`, `unblock_condition`, `next_step: "/flow:revise <flow_id>"`, and `spec.md` checklist `[!]`.
5. **Session Continuity Recovery**: After context compaction or session restart, inspect `git status --short -b`, `git log -n 5 --oneline`, `.agents/bundles/specs/*/spec.md`, and `tasks/*.md`. If a task is `in_progress` and its target commit already landed in `git log`, update its `commit` and mark it `completed`; otherwise resume the `in_progress` worksheet from its `## Verification` baseline.
