# Flow Direct Markdown & Git State Contract

Specifications (`.agents/bundles/specs/<flow_id>/spec.md`), chapter specifications (`.agents/bundles/specs/<flow_id>/chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are the sole authority for Flow state and continuity. Agents read and update these Markdown files directly in present tense and verify continuity against Git commit history (`HEAD`, task `commit` SHAs, and `last_reviewed_commit`).

## Root Resolution, Worktree Routing, & Bundle Layout

- `<configured-root>` is `root_directory` from `.agents/setup-state.json` (default `.agents`).
- `<bundle-root>` is `bundle_root` from `.agents/setup-state.json` (default `.agents/bundles`).
- `<flow-root>` is `<bundle-root>/specs/<flow_id>`. Resolved paths stay inside the repository root or, inside a linked `git worktree` (`git rev-parse --git-common-dir`), a symlink targeting the primary checkout's `.agents` / `.venv` directory:
  - **`ignore_policy: shared`**: `.agents/` is tracked in Git; work directly in the worktree's `.agents/bundles/` Markdown.
  - **`ignore_policy: local-only`**: `.agents/` lives in the primary checkout (`$MAIN_WORKTREE/.agents`, symlinked at `$WORKTREE/.agents`); read and write all Flow Markdown in the primary checkout so zero diverging copies exist.
- **Single-Chapter Flow (`Small` Tier — `<= 400` LOC, `1` module, `1..4` tasks)**:
  - `<flow-root>/spec.md` (`has_chapters: false`) + `<flow-root>/tasks/t01-<slug>.md..t04-<slug>.md` (`worksheet_format: compact` or `full`).
- **Multi-Chapter Flow (`Medium` & `Large` Tiers — `> 4` tasks, `>= 2` module boundaries, or `/flow:prd`)**:
  - `<flow-root>/spec.md` — Full-plan roadmap (`has_chapters: true`, `current_chapter`, `chapters: [ch01-<slug>, ...]`, cross-chapter public seams and shared types, Flow-Wide Documentation & OKF Knowledge Plan, full chapter checklist, and present-tense state snapshot).
  - `<flow-root>/chapters/index.md` — Frontmatter-free OKF v0.2 directory catalog (`# Chapters: <Title>` + `* [ch01 — <Title>](ch01-<slug>/spec.md) — [<state>] <one-sentence present-tense scope>`).
  - `<flow-root>/chapters/chNN-<slug>/{spec.md,planner-notes.md,tasks/t01-<slug>.md..t04-<slug>.md}` (`1..4` tasks per chapter; never mix root `specs/<flow_id>/tasks/` with `chapters/`).

## Lifecycle Enums, OKF v0.2 Status, & Anti-Skip Rules

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
| `in_progress` or `active` | `- [~] <id> — <summary> (<rel-path>)` | Claimed by the active chapter or executor turn. |
| `completed` or `closed` | `- [x] [<sha>] <id> — <summary> (<rel-path>)` | Verified (`exit 0`), backed by Git diff ownership on declared `files:`/`tests:`, and chapter-reviewed at `<sha>`. |
| `blocked` | `- [!] <id> — <summary> (<rel-path>)` | Halted on a documented mismatch (`blocked_reason` + `unblock_condition`). |
| `deferred` or `skipped` | `- [-] <id> — <summary> (<rel-path>)` | User-authorized deferral only (`deferred_by: "user"` + non-empty `deferred_reason`). |

- **State vs. Status & Plan Quality**: Workflow state belongs strictly in `state:`; OKF v0.2 maturity (`draft | stable | deprecated`) belongs strictly in `status:`. Set `planning_quality: degraded` + non-empty `planning_degraded_reason` whenever quota fallback or timeout recovery prevented planning on the primary frontier thinking model.
- **Mechanical Anti-Skip Invariants**: Root `spec.md` cannot be `state: completed` while any chapter is open; a chapter `spec.md` cannot be `state: completed` with `0` tasks or open tasks; `deferred`/`skipped` requires `deferred_by: "user"` + `deferred_reason`; and every `completed` task commit SHA must touch at least one non-ignored declared path in `files:` or `tests:`.
- **Pause, Handoff, & Gate Overrides**: Set `state: paused` (or `paused: true` / `handoff: true`) on a root or chapter `spec.md` when deliberately pausing work for human handoff, or set `gate: advisory | off` in spec frontmatter to bypass Stop-gate blocking for that specification. Configure project-wide Stop-gate behavior via `.agents/setup-state.json` (`stop_gate: "enforce" | "advisory" | "off"`, `workflow_preferences.sha_tracking: "strict" | "advisory" | "off"`) or `FLOW_STOP_GATE=off|advisory`. Under default `strict` SHA tracking, `patch-id` equivalence and rewritten-`HEAD` detection tolerate rebased, amended, cherry-picked, and squash-merged commits without disabling stale-review checks on linear history.
- **Present-Tense Living Markdown Rule**: Root `spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, `tasks/*.md`, `knowledge/**`, and `docs/**` state current verified reality, remaining work, and the full plan in present tense—zero `Revision History` / `Changelog` headings, zero struck-through `~~` items, and zero standalone `---` body rules.

## Normative Document Schemas

### 1. Root or Nested Chapter Specification (`spec.md`)

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
generated: { by: flow/0.28.1, at: 2026-11-12T00:00:00Z }
verified: [{ by: agent:code-reviewer, at: 2026-11-12T01:00:00Z, commit: 4f91c2a }]
sources:
  - id: auth-entry
    resource: src/auth/middleware.py::AuthMiddleware
    title: Existing HTTP authentication middleware seam
tags: [feature, auth, security]
---
```

Open every `spec.md` body with a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block followed by six sections:

1. `## 1. Specification, Context & Provenance`
2. `## 2. Requirements, Concrete Contracts & Architecture`
3. `## 3. Documentation & OKF Knowledge Plan` (`[k/N files documented]`)
4. `## 4. Requirement-to-Task Traceability Matrix`
5. `## 5. Implementation Plan` (checklist + fast `< 60s` **Chapter / Phase Recovery Checkpoint**)
6. `## 6. Current State & Remaining Plan Snapshot`

### 2. Task Worksheet (`tasks/<id>-<slug>.md` — `full` & `compact`)

```yaml
---
type: Task
id: user-auth:ch02:t01
chapter_id: ch02-session-middleware
title: Implement ASGI session middleware and canonical public-seam tests
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
commit: null
sources: [{ id: auth-mw, resource: src/auth/middleware.py::AuthMiddleware, title: Request middleware }]
tags: [feature, auth, tdd]
---
```

- **Full Task Blueprint Headings (`worksheet_format: full` — `Medium` & `Large` Tiers)**:
  1. `## Objective & Scope Boundary`
  2. `## Bounded Read Manifest`
  3. `## Symbol & Signature Contracts`
  4. `## Edge Cases & Error Semantics`
  5. `## Public-Seam Test Blueprint`
  6. `## Verification`
  7. `## Acceptance Criteria`
  8. `## Notes & Discoveries`
- **Compact Task Worksheet Headings (`worksheet_format: compact` — `Small` Tier `<= 400` LOC)**:
  1. `## Objective & Scope Boundary`
  2. `## Bounded Read Manifest`
  3. `## Contracts & Edge Cases`
  4. `## Test Matrix`
  5. `## Verification`
  6. `## Acceptance Criteria`
  *(Add `## Notes & Discoveries` during implementation when needed.)*

## Direct State Mutations & Commit Sequencing

1. **Plan & Validate**: Author specs, task worksheets, and `chapters/<ch_id>/planner-notes.md`, run `/flow:validate` (`exit 0`), pass Zero-Context Review, and stamp `status: stable` + `plan_commit: <HEAD_SHA>`.
2. **Execute Chapter Batch & Sync**: Apply the active chapter's `1..4` tasks in one warm batch, run the Fast Chapter Gate (`< 60s`), commit owned `files:`/`tests:` first to obtain `<CODE_SHA>`, and stamp `commit: <CODE_SHA>` + `[x] [<CODE_SHA>]` + present-tense Markdown/OKF updates in the pre-review sync commit (never `git commit --amend`) before stamping `last_reviewed_commit`.
