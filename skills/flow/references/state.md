# Flow Markdown & Git State Contract

Specs (`.agents/bundles/specs/<flow_id>/spec.md`), chapter specs (`.agents/bundles/specs/<flow_id>/chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are the sole authority for Flow state.
Agents read and update these Markdown files in present tense and verify continuity against Git history (`HEAD`, task `commit` SHAs, and `last_reviewed_commit`).

## Root Resolution, Worktrees & Bundle Layout

- `<configured-root>` is `root_directory` from `.agents/setup-state.json` (default `.agents`).
- `<bundle-root>` is `bundle_root` from `.agents/setup-state.json` (default `.agents/bundles`).
- `<flow-root>` is `<bundle-root>/specs/<flow_id>`.
- Resolved paths stay inside the repository root or, in a linked `git worktree` (`git rev-parse --git-common-dir`), a symlink to the primary checkout's `.agents` or `.venv`:
  - **`ignore_policy: shared`**: `.agents/` is tracked in Git; work directly in the worktree's `.agents/bundles/` Markdown.
  - **`ignore_policy: local-only`**: `.agents/` lives in the primary checkout (`$MAIN_WORKTREE/.agents`, symlinked at `$WORKTREE/.agents`); read and write Flow Markdown in the primary checkout.
- **Single-Chapter Flow (Default for Cohesive Features)**:
  - `<flow-root>/spec.md` (`has_chapters: false`) + `<flow-root>/tasks/tNN-<slug>.md` (`worksheet_format: compact` or `full`).
- **Multi-Chapter Flow (Staged Checkpoints, Parallel Subsystems, `empirical_dependent` Checks, or `/flow:prd`)**:
  - `<flow-root>/spec.md` — Full roadmap (`has_chapters: true`, `current_chapter`, `chapters: [ch01-<slug>, ...]`, shared module interfaces and types, `Documentation & OKF Knowledge Plan`, chapter checklist, and `Current State & Remaining Plan Snapshot`).
  - `<flow-root>/chapters/index.md` — Frontmatter-free OKF v0.2 catalog (`# Chapters: <Title>` + `* [ch01 — <Title>](ch01-<slug>/spec.md) — [<state>] <one-sentence scope>`).
  - `<flow-root>/chapters/chNN-<slug>/{spec.md,planner-notes.md,tasks/tNN-<slug>.md}` (never mix root `specs/<flow_id>/tasks/` with `chapters/`).

## Lifecycle Enums, OKF Status & Completion Rules

```yaml
spec_states: [draft, planned, active, paused, completed]
chapter_planning_statuses: [complete, empirical_dependent]
planning_qualities: [standard, degraded]
okf_document_statuses: [draft, stable, deprecated]
task_states: [pending, open, in_progress, completed, closed, blocked, deferred, skipped]
worksheet_formats: [full, compact]
priorities: [P0, P1, P2, P3, P4]
verification_strategies: [behavior_tdd, regression_tdd, characterization, static_validation, documentation_validation, integration_acceptance]
```

| Chapter / Task `state` | `spec.md` Checklist Marker | Meaning |
| --- | --- | --- |
| `pending`, `open`, or `planned` | `- [ ] <id> — <summary> (<rel-path>)` | Ready once `depends_on` / `depends_on_chapters` are `completed` and `planning_status: complete`. |
| `in_progress` or `active` | `- [~] <id> — <summary> (<rel-path>)` | Claimed by the active chapter or worker turn. |
| `completed` or `closed` | `- [x] [<sha>] <id> — <summary> (<rel-path>)` | Verified (`exit 0`), backed by Git diff ownership on declared `files:`/`tests:`, and reviewed at `<sha>`. |
| `blocked` | `- [!] <id> — <summary> (<rel-path>)` | Halted on a documented mismatch (`blocked_reason` + `unblock_condition`). |
| `deferred` or `skipped` | `- [-] <id> — <summary> (<rel-path>)` | User-authorized deferral only (`deferred_by: "user"` + non-empty `deferred_reason`). |

- **State vs. Status & Plan Quality**: Workflow state belongs in `state:`; OKF v0.2 maturity (`draft | stable | deprecated`) belongs in `status:`.
- **Degraded Plan Quality**: Set `planning_quality: degraded` and a non-empty `planning_degraded_reason` whenever quota fallback or timeout recovery prevented planning on the strongest model.
- **Completion Check Rules**: Root `spec.md` cannot be `state: completed` while any chapter is open, and a chapter `spec.md` cannot be `state: completed` with `0` or open tasks.
- **Deferral & Commit Rules**: `deferred` or `skipped` requires `deferred_by: "user"` and `deferred_reason`, and every `completed` task commit SHA must touch at least one non-ignored path in `files:` or `tests:`.
- **Pause, Handoff & Stop-Check Overrides**: Set `state: paused` (or `paused: true` / `handoff: true`) on a spec when pausing for human handoff, or set `stop_check: advisory | off` in frontmatter.
- **Project Stop-Check Config**: Configure project-wide stop checks via `.agents/setup-state.json` (`stop_check: "enforce" | "advisory" | "off"`, `workflow_preferences.sha_tracking: "strict" | "advisory" | "off"`) or `FLOW_STOP_CHECK=off|advisory`.
- **SHA Tracking**: Under default `strict` SHA tracking, `patch-id` equivalence and rewritten-`HEAD` detection tolerate rebased, amended, cherry-picked, and squash-merged commits while preserving stale-review checks on linear history.
- **Current-State Markdown Rule**: Root `spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, `tasks/*.md`, `knowledge/**`, and `docs/**` state current reality and remaining work in present tense—no `Revision History` / `Changelog` headings, no `~~` items, and no standalone `---` rules.

## Normative Document Schemas

### 1. Root or Chapter Spec (`spec.md`)

```yaml
---
type: Spec
flow_id: user-auth
title: User Authentication and Session Middleware
description: Repository-native JWT signing, session middleware, and token rotation.
status: stable
state: active
planning_quality: standard
planning_degraded_reason: null
has_chapters: true
chapters: [ch01-token-signer, ch02-session-middleware]
current_chapter: ch02-session-middleware
current_task: user-auth:ch02:t01
parent_flow: null
chapter_id: null
planning_status: complete
depends_on_chapters: []
replan_trigger: null
plan_revision: 1
plan_commit: 8775d6c
last_verified_checkpoint: 4f91c2a
last_reviewed_chapter: ch01-token-signer
last_reviewed_commit: 4f91c2a
generated: { by: flow/<version>, at: 2026-11-12T00:00:00Z }
verified: [{ by: agent:code-reviewer, at: 2026-11-12T01:00:00Z, commit: 4f91c2a }]
sources:
  - id: auth-entry
    resource: src/auth/middleware.py::AuthMiddleware
    title: Existing HTTP authentication middleware interface
tags: [feature, auth, security]
---
```

Open every `spec.md` body with a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` truth block followed by six sections:

1. `## 1. Specification, Context & Provenance`
2. `## 2. Requirements, Concrete Contracts & Architecture`
3. `## 3. Documentation & OKF Knowledge Plan` (`[k/N files documented]`)
4. `## 4. Requirement-to-Task Traceability Matrix`
5. `## 5. Implementation Plan` (checklist + fast `< 60s` **Chapter / Phase Recovery Checkpoint**)
6. `## 6. Current State & Remaining Plan Snapshot`

### 2. Task Worksheet (`tasks/<id>-<slug>.md`)

```yaml
---
type: Task
id: user-auth:ch02:t01
chapter_id: ch02-session-middleware
title: Implement ASGI session middleware and public interface tests
description: Validate bearer tokens via TokenSigner and attach Principal to request scope.
status: stable
state: pending
priority: P1
verification_strategy: behavior_tdd
worksheet_format: full
depends_on: []
read_set: [src/auth/middleware.py, src/auth/tokens.py, tests/auth/test_middleware.py]
files: [src/auth/middleware.py]
tests: [tests/auth/test_middleware.py]
estimated_loc: 140
plan_revision: 1
plan_commit: 8775d6c
claimed_by: null
claimed_at: null
commit: null
sources: [{ id: auth-mw, resource: src/auth/middleware.py::AuthMiddleware, title: Request middleware }]
tags: [feature, auth, tdd]
---
```

- **Task Claim Identity**: When claiming a task (`state: in_progress`), set `claimed_by: <harness>:<session_id>[:<role_or_worktree>]` (`<harness> ∈ {agy, claude, codex, cursor, opencode, vscode, cli}`) and `claimed_at: <ISO-8601 UTC>`. Reset both to `null` when releasing or completing the task.
- **Full Worksheet Headings (`worksheet_format: full` — Complex Contracts)**:
  1. `## Objective & Scope Boundary`
  2. `## Bounded Read Manifest`
  3. `## Symbol & Signature Contracts`
  4. `## Edge Cases & Error Semantics`
  5. `## Public-Seam Test Blueprint`
  6. `## Verification`
  7. `## Acceptance Criteria`
  8. `## Notes & Discoveries`
- **Compact Worksheet Headings (`worksheet_format: compact` — Default)**:
  1. `## Objective & Scope Boundary`
  2. `## Bounded Read Manifest`
  3. `## Contracts & Edge Cases`
  4. `## Test Matrix`
  5. `## Verification`
  6. `## Acceptance Criteria`
  *(Add `## Notes & Discoveries` during implementation when needed.)*

## State Mutations & Commit Sequencing

1. **Plan & Validate**: Write specs, task worksheets, and `chapters/<ch_id>/planner-notes.md`, run `/flow:validate` (`exit 0`), pass independent review, and stamp `status: stable` plus `plan_commit: <HEAD_SHA>`.
2. **Run Parallel Steps & CLI Sync**: Build task briefs with `flow tasks plan --flow <flow_id> --briefs --json`, run up to `4` workers per step editing separate files, and sync checklists between steps with `flow sync` (or `flow spec sync`). Also track per-author out-of-tree review notes under `<git-common-dir>/spec-feedback/<flow_id>/<author_slug>.json` (merging sibling stores on read) and optional orphan collaboration snapshots on `flow-specs`.
3. **Commit Code First**: Validate at closeout, commit owned `files:`/`tests:` first to obtain `<CODE_SHA>`, and stamp `commit: <CODE_SHA>`, `[x] [<CODE_SHA>]`, and present-tense Markdown/OKF updates in the pre-review sync commit (never `git commit --amend`) before stamping `last_reviewed_commit`.
