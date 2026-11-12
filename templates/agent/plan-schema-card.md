# Flow Planning Schema Card

Self-contained reference for authoring Flow specifications, chapter specifications, task worksheets, and planner notes. Read only this card, the root `specs/<flow_id>/spec.md`, and the bounded repository source files for your chapter—never browse plugin reference documentation.

## 1. OKF v0.2 & Present-Tense Invariants

- **Status vs. State**: `status` holds document maturity only (`draft | stable | deprecated`); workflow execution belongs strictly in `state` (`draft | planned | active | completed` on `Spec`; `pending | open | in_progress | completed | closed | blocked | deferred | skipped` on `Task`).
- **Degraded Planning Disclosure**: Set `planning_quality: standard` when planned on the primary frontier thinking model. Whenever quota fallback, model downgrade, or timeout recovery occurs, set `planning_quality: degraded` and record the exact cause in `planning_degraded_reason` (plus `planned_with_model`).
- **Provenance & Truth Block**: Every `spec.md` (`type: Spec`) carries `1..8` lowercase hyphenated `tags` (free of state/status words), non-empty `sources: [{ id, resource, title }]` matched 1:1 with `[^id]:` body footnotes, and a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block at the top of the body.
- **Formatting Hygiene**: Subdirectory `index.md` files (`chapters/index.md`, `specs/index.md`) and `log.md` carry zero YAML frontmatter. Never place standalone `---` horizontal rules, `Revision History` / `Changelog` sections, or struck-through `~~` items in bundle Markdown bodies.
- **Anti-Skip Rule**: Never set `state: deferred` or `state: skipped` without `deferred_by: "user"` and non-empty `deferred_reason`.

## 2. Specification Schema (`spec.md` — Root & Chapter)

- **Required Frontmatter Keys**: `type: Spec`, `title`, `description`, `status`, `state`, `planning_quality`, `planning_degraded_reason`, `plan_revision`, `plan_commit`, `current_task`, `last_verified_checkpoint`, `last_reviewed_commit`, `generated`, `verified`, `sources`, `tags`.
  - Root multi-chapter specs add: `flow_id`, `has_chapters: true`, `chapters: [ch01-<slug>, ...]`, `current_chapter`, `last_reviewed_chapter`.
  - Nested chapter specs (`chapters/<ch_id>/spec.md`, `1..4` tasks max) add: `parent_flow`, `chapter_id`, `planning_status: complete | empirical_dependent`, `depends_on_chapters: [...]`, `replan_trigger` (non-empty when `empirical_dependent`).
- **Required Body Headings**:
  - `## 1. Specification, Context & Provenance`
  - `## 2. Requirements, Concrete Contracts & Architecture`
  - `## 3. Documentation & OKF Knowledge Plan`
  - `## 4. Requirement-to-Task Traceability Matrix`
  - `## 5. Implementation Plan` (checklist + fast **Chapter / Phase Recovery Checkpoint** `< 60s`: lint + targeted unit file, never a slow full test suite)
  - `## 6. Current State & Remaining Plan Snapshot`

## 3. Task Worksheet Schema (`tasks/<id>-<slug>.md`)

- **Budgets & Deduplication**: `read_set` (`<= 6` files), `files` (`<= 3` production files), `tests` (canonical module test files), `estimated_loc` (`<= 250`). Reference concrete types/signatures defined in owning `spec.md` by name rather than duplicating multi-line struct definitions across tasks.
- **Required Frontmatter Keys**: `type: Task`, `id`, `chapter_id`, `title`, `description`, `status`, `state`, `priority`, `verification_strategy`, `worksheet_format: full | compact`, `depends_on`, `read_set`, `files`, `tests`, `estimated_loc`, `plan_revision`, `plan_commit`, `commit`, `sources`, `tags`.

### Full Task Blueprint Headings (`worksheet_format: full` — Medium & Large Tiers)

- `## Objective & Scope Boundary`
- `## Bounded Read Manifest`
- `## Symbol & Signature Contracts`
- `## Edge Cases & Error Semantics`
- `## Public-Seam Test Blueprint`
- `## Verification`
- `## Acceptance Criteria`
- `## Notes & Discoveries`

### Compact Task Worksheet Headings (`worksheet_format: compact` — Small Tier `<= 400` LOC)

- `## Objective & Scope Boundary`
- `## Bounded Read Manifest`
- `## Contracts & Edge Cases`
- `## Test Matrix`
- `## Verification`
- `## Acceptance Criteria`

## 4. Planner Disk Receipt (`chapters/<ch_id>/planner-notes.md`)

Write `chapters/<ch_id>/planner-notes.md` (frontmatter-free) on disk **before** returning so findings survive timeouts:

- `## Files Written` — Relative paths of `spec.md` and `tasks/*.md` written.
- `## Task Summaries` — One-line summary per task worksheet.
- `## Root Spec Issues` — Cross-chapter signature conflicts requiring root `spec.md` updates, or `None`.
- `## Open Questions` — Unresolved empirical triggers or user decisions, or `None`.
