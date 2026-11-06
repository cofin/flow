# Flow Direct Markdown & Git State Contract

Specifications (`.agents/bundles/specs/<flow_id>/spec.md`), chapter specifications (`.agents/bundles/specs/<flow_id>/chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are the sole authority for Flow state and continuity. Agents read and update these Markdown files directly in present tense and verify continuity against Git commit history (`HEAD`, task `commit` SHAs, and `last_reviewed_commit`).

## Root Resolution & Bundle Layout

- `<configured-root>` is `root_directory` from `.agents/setup-state.json` (default `.agents`).
- `<bundle-root>` is `bundle_root` from `.agents/setup-state.json` (default `.agents/bundles`).
- `<flow-root>` is `<bundle-root>/specs/<flow_id>`. Every resolved path must stay inside the repository root, contain no `..`, and traverse no escaping symlink.
- **Single-Chapter Flow (`1–4` tasks within one subsystem)**:
  - `<flow-root>/spec.md` (`has_chapters: false`) + `<flow-root>/tasks/t01-<slug>.md..t04-<slug>.md`.
- **Multi-Chapter Flow (`> 4` tasks, `>= 2` module boundaries, or `/flow:prd` — `2..N` chapters with zero upper cap)**:
  - `<flow-root>/spec.md` — Authoritative full-plan roadmap (`has_chapters: true`, `current_chapter`, `chapters: [ch01-<slug>, ...]`, cross-chapter public seams and shared types, Flow-Wide Documentation & OKF Knowledge Plan, full chapter checklist, and present-tense state snapshot).
  - `<flow-root>/chapters/index.md` — Frontmatter-free OKF v0.2 directory catalog (`# Chapters: <Title>` + `* [ch01 — <Title>](ch01-<slug>/spec.md) — [<state>] <one-sentence present-tense scope>`).
  - `<flow-root>/chapters/chNN-<slug>/spec.md` + `chapters/chNN-<slug>/tasks/t01-<slug>.md..t04-<slug>.md` (`1–4` vertical-slice tasks per chapter; never mix root `specs/<flow_id>/tasks/` with `chapters/`).

## Lifecycle Enums, OKF v0.2 Status, & Checklist Mapping

```yaml
spec_states: [draft, planned, active, completed]
chapter_planning_statuses: [complete, empirical_dependent]
okf_document_statuses: [draft, stable, deprecated]
task_states: [pending, open, in_progress, completed, closed, blocked, deferred, skipped]
priorities: [P0, P1, P2, P3, P4]
verification_strategies:
  - behavior_tdd
  - regression_tdd
  - characterization
  - static_validation
  - documentation_validation
  - integration_acceptance
```

| Chapter / Task `state` | `spec.md` Checklist Marker | Meaning |
| --- | --- | --- |
| `pending`, `open`, or `planned` | `- [ ] <id> — <summary> (<rel-path>)` | Ready once `depends_on` / `depends_on_chapters` are `completed` and `planning_status: complete`. |
| `in_progress` or `active` | `- [~] <id> — <summary> (<rel-path>)` | Claimed by the active chapter or executor turn. |
| `completed` or `closed` | `- [x] [<sha>] <id> — <summary> (<rel-path>)` | Verified (`exit 0`), committed (and chapter-reviewed at `<sha>`). |
| `blocked` | `- [!] <id> — <summary> (<rel-path>)` | Halted on a documented mismatch (`blocked_reason` + `unblock_condition`). |
| `deferred` or `skipped` | `- [-] <id> — <summary> (<rel-path>)` | Descoped or moved to an explicit follow-up flow. |

- **State vs. Status**: Workflow execution state belongs strictly in `state:`; OKF v0.2 document maturity (`draft | stable | deprecated`) belongs strictly in `status:`.
- **Empirical Dependency Annotation**: Append `[empirical_dependent: <replan_trigger>]` on root `spec.md` checklist lines whose chapter has `planning_status: empirical_dependent`.
- **Present-Tense Living Markdown Rule**: Root `spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, `tasks/*.md`, `knowledge/**`, and `docs/**` state **current verified reality, remaining work, and the full plan** in present tense. Never include `Revision History` / `Changelog` headings, historical narrative (`"in chapter 1 we..."`, `"previously..."`), struck-through checklist remnants (`~~...~~`), or standalone `---` horizontal rules inside bundle Markdown bodies; record chronological history solely in `.agents/bundles/log.md` and Git commits.

## Normative Document Schemas

### 1. Root or Single-Chapter Specification (`specs/<flow_id>/spec.md`)

```yaml
---
type: Spec
flow_id: user-auth
title: User Authentication and Session Middleware
description: Repository-native JWT signing, session middleware, and token rotation.
status: stable
state: active
has_chapters: true
chapters: [ch01-token-signer, ch02-session-middleware, ch03-docs-and-okf]
current_chapter: ch02-session-middleware
current_task: user-auth:ch02:t01
parent_prd: null
research: [research/jwt-eddsa_20261106.md]
plan_revision: 1
plan_commit: 8775d6c
state_revision: 2
last_verified_checkpoint: 4f91c2a
last_reviewed_chapter: ch01-token-signer
last_reviewed_commit: 4f91c2a
created_at: 2026-11-06T00:00:00Z
updated_at: 2026-11-06T01:00:00Z
generated: { by: flow/0.26.0, at: 2026-11-06T00:00:00Z }
verified:
  - by: agent:code-reviewer
    at: 2026-11-06T01:00:00Z
    commit: 4f91c2a
sources:
  - id: auth-entry
    resource: src/auth/middleware.py::AuthMiddleware
    title: Existing HTTP authentication middleware seam
tags: [feature, auth, security]
---
```

### 2. Nested Chapter Specification (`specs/<flow_id>/chapters/<ch_id>/spec.md`)

Carries the same OKF v0.2 provenance keys (`type: Spec`, `title`, `description`, `status`, `state`, `plan_revision`, `plan_commit`, `current_task`, `last_verified_checkpoint`, `last_reviewed_commit`, `generated`, `verified`, `sources`, `tags`) plus:

```yaml
parent_flow: user-auth
chapter_id: ch02-session-middleware
planning_status: complete       # complete | empirical_dependent
depends_on_chapters: [ch01-token-signer]
replan_trigger: null            # required string when planning_status == empirical_dependent
```

### Required `spec.md` Body Structure (Root & Chapter)

Open the body with a bounded `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block summarizing non-negotiable invariants and `[^source-id]` citations, followed by six present-tense sections:

1. `## 1. Specification, Context & Provenance` — Plain-English Problem Statement & Objectives, Non-Goals, Upstream Baseline, Symbol-Anchored `Code Analysis & Seam Summary` cited via `[^id]` footnotes, and Relevant OKF Knowledge Chapters & Skills.
2. `## 2. Requirements, Concrete Contracts & Architecture` — `R1..RN`, **Full Public Type/Struct/Schema & Signature Contracts**, **Caller -> Seam -> Collaborator Integration Map**, Non-Functional Constraints, **Edge-Case, Failure-Mode & Invariant Matrix**, Acceptance Scenarios, and **Mandatory Alternatives Comparison**.
3. `## 3. Documentation & OKF Knowledge Plan` — `[k/N files documented]` manifest of user-facing `README.md` / `docs/**` pages and `.agents/bundles/knowledge/**` + `.agents/skills/` chapters created or updated by this flow/chapter.
4. `## 4. Requirement-to-Task Traceability Matrix` — `Requirement | Owning Chapter / Task | Verification Strategy | Canonical Test / Doc Gate`.
5. `## 5. Implementation Plan` — Full chapter roadmap checklist (`chapters/<ch_id>/spec.md` on root `spec.md`; `tasks/<id>-<slug>.md` `1–4` items on chapter or single-chapter `spec.md`) plus the mandatory **Chapter / Phase Recovery Checkpoint** command.
6. `## 6. Current State & Remaining Plan Snapshot` — Bounded (`<= 25` lines) present-tense summary overwritten at every chapter boundary and `/flow:revise`: verified baseline at `HEAD`, remaining chapters/tasks across the full plan, open `[k/N]` doc/OKF items, and active invariants or `empirical_dependent` triggers.

### 3. Task Worksheet (`tasks/<id>-<slug>.md`)

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
depends_on: []
read_set:
  - src/auth/middleware.py
  - src/auth/tokens.py
  - tests/auth/test_middleware.py
files:
  - src/auth/middleware.py
tests:
  - tests/auth/test_middleware.py
estimated_loc: 140
plan_revision: 1
plan_commit: 8775d6c
state_revision: 0
claimed_by: null
claimed_at: null
blocked_reason: null
unblock_condition: null
next_step: null
last_verified_at: null
last_verified_commit: null
verification_evidence: null
created_at: 2026-11-06T00:00:00Z
updated_at: 2026-11-06T00:00:00Z
commit: null
sources:
  - id: auth-mw
    resource: src/auth/middleware.py::AuthMiddleware
    title: Request authentication middleware
tags: [feature, auth, tdd]
---
```

Every task worksheet (`1–3` production files, `read_set <= 6` files, `estimated_loc <= 250`) MUST contain these 8 headings:

1. `## Objective & Scope Boundary` — Exact vertical-slice outcome and explicit out-of-scope boundaries.
2. `## Bounded Read Manifest` — The `<= 6` repository/OKF files the isolated executor needs to read (`path/to/file::Symbol`).
3. `## Symbol & Signature Contracts` — Exact class/struct fields, function/method signatures, parameter types, return types, and call-site wiring.
4. `## Edge Cases & Error Semantics` — Concrete boundary inputs, empty/null/timeout/permission cases, and exact exception or error return contracts.
5. `## Public-Seam Test Blueprint` — Canonical test file path, seam dependency category, and a non-tautological **Worked Test Matrix** (`Case | Input | Expected Output / Error`) with concrete literals (or manifest/link/OKF assertions for `documentation_validation`).
6. `## Verification` — Exact initial (Red/baseline) and final (Green + lint/typecheck) CLI commands.
7. `## Acceptance Criteria` — Checkboxes (`- [ ]`) mapped to parent requirements.
8. `## Notes & Discoveries` — Concise implementation findings (`- [YYYY-MM-DD HH:MM] ...`).

## Direct State Mutations, Pre-Review Sync, & Continuity Recovery

1. **Approve Plan (`plan` / `prd` / `revise`)**: Author all chapters and task worksheets upfront, run zero-context spec review, and stamp `status: stable`, `plan_commit: <HEAD_SHA>`, and matching `plan_revision` across `spec.md` and its owned tasks.
2. **Claim & Complete Task (`implement`)**: Claim (`state: in_progress`, checklist `[~]`); after verification exits `0`, update `tasks/<id>-<slug>.md` (`state: completed`, `commit: <sha>`, `last_verified_commit`) and owning `spec.md` checklist (`- [x] [<sha>] ...`) atomically in one signed commit.
3. **Close Chapter (`implement`)**: Run the Chapter Recovery Checkpoint, rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, root `specs/<flow_id>/spec.md`, `knowledge/**`, and `docs/**` **in place in present tense** (current state + remaining full plan), pass Zero-Context Chapter Code & Doc-Sync Review (`@code-reviewer` + `@quality-reviewer`), stamp `last_reviewed_commit: <REVIEWED_SHA>` + `state: completed` on the chapter, mark `[x] [<REVIEWED_SHA>]` and advance `current_chapter` in root `spec.md`, and stop at the chapter boundary.
4. **Revise Plan (`revise`)**: Rewrite affected chapter specs/worksheets AND root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense without historical sediment; clear `last_reviewed_commit: null` on any reopened chapter.
5. **Session Continuity Recovery**: After compaction or restart, inspect `git status --short -b`, `git log -n 5 --oneline`, root `specs/*/spec.md`, `chapters/index.md`, and active chapter `tasks/*.md` to reconcile landed commits and resume cleanly.
