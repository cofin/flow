# Flow Planning Schema Card

Self-contained reference for authoring Flow specs, chapter specs, task worksheets, and planner notes.
Read only this card, root `specs/<flow_id>/spec.md`, and the source files for your chapter.
Never browse plugin reference docs.

## 1. OKF v0.2 and Present-Tense Rules

- **Status vs. State**: `status` tracks document maturity (`draft | stable | deprecated`). Workflow state belongs in `state` (`draft | planned | active | completed` on `Spec`; `pending | open | in_progress | completed | closed | blocked | deferred | skipped` on `Task`).
- **Degraded Planning**: Set `planning_quality: standard` on the `strong` model role (`flow_plan_strong`). On quota fallback, model downgrade, or timeout recovery, set `planning_quality: degraded` and record the cause in `planning_degraded_reason` and `planned_with_model`.
- **Provenance and Truth Block**: Every `spec.md` (`type: Spec`) carries `1..8` lowercase hyphenated `tags` without state words, `sources: [{ id, resource, title }]` matched 1:1 with `[^id]:` footnotes, and a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block.
- **Formatting**: Subdirectory `index.md` files (`chapters/index.md`, `specs/index.md`) and `log.md` carry no YAML frontmatter. Never place standalone `---` body rules, `Revision History` or `Changelog` headings, or struck-through `~~` items in bundle bodies.
- **Completion Check**: Never set `state: deferred` or `state: skipped` without `deferred_by: "user"` and a non-empty `deferred_reason`.

## 2. Writing Rules for Generated Specs

- Put what changes for the reader first.
- Write one idea per sentence, at most 35 words.
- Keep headings to at most 8 words and one topic.
- State a number once, in a table or one bullet.
- Name a class, function, or flag only when the reader needs to type it or find it.
- Avoid stacked qualifiers and retired scheduling jargon; use plain Flow words (`step`, `task`, `brief`, `worker`, `check`, `sync`, `independent`).

## 3. Specification Schema (`spec.md`)

- **Required Frontmatter Keys**: `type: Spec`, `title`, `description`, `status`, `state`, `planning_quality`, `planning_degraded_reason`, `plan_revision`, `plan_commit`, `current_task`, `last_verified_checkpoint`, `last_reviewed_commit`, `generated`, `verified`, `sources`, `tags`.
- **Root Multi-Chapter Keys**: `flow_id`, `has_chapters: true`, `chapters: [ch01-<slug>, ...]`, `current_chapter`, `last_reviewed_chapter`.
- **Nested Chapter Keys**: `parent_flow`, `chapter_id`, `planning_status: complete | empirical_dependent`, `depends_on_chapters: [...]`, `replan_trigger` (required when `empirical_dependent`).
- **Chapter Sizing**: Use `1..N` tasks per chapter with no task-count cap. Split chapters only for real review checkpoints, independent parallel subsystems, or `empirical_dependent` checks.
- **Required Body Headings**:
  - `## 1. Specification, Context & Provenance`
  - `## 2. Requirements, Concrete Contracts & Architecture`
  - `## 3. Documentation & OKF Knowledge Plan`
  - `## 4. Requirement-to-Task Traceability Matrix`
  - `## 5. Implementation Plan` (checklist plus fast `< 60s` chapter check: lint and targeted unit test files, never a slow full suite)
  - `## 6. Current State & Remaining Plan Snapshot`

## 4. Task Worksheet Schema (`tasks/<id>-<slug>.md`)

- **Sizing**: Keep each task cohesive around one feature increment (`read_set`, `files`, `tests`, and `estimated_loc` have no arbitrary hard caps).
- **Deduplication**: Reference types and signatures defined in owning `spec.md` by name instead of repeating multi-line definitions across tasks.
- **Required Frontmatter Keys**: `type: Task`, `id`, `chapter_id`, `title`, `description`, `status`, `state`, `priority`, `verification_strategy`, `worksheet_format: full | compact`, `depends_on`, `read_set`, `files`, `tests`, `estimated_loc`, `plan_revision`, `plan_commit`, `commit`, `sources`, `tags`.

### Full Worksheet Headings (`worksheet_format: full`)

Use for complex public interfaces and multi-interface edge-case tables:

- `## Objective & Scope Boundary`
- `## Bounded Read Manifest`
- `## Symbol & Signature Contracts`
- `## Edge Cases & Error Semantics`
- `## Public-Seam Test Blueprint`
- `## Verification`
- `## Acceptance Criteria`
- `## Notes & Discoveries`

### Compact Worksheet Headings (`worksheet_format: compact`)

Default for straightforward cohesive tasks:

- `## Objective & Scope Boundary`
- `## Bounded Read Manifest`
- `## Contracts & Edge Cases`
- `## Test Matrix`
- `## Verification`
- `## Acceptance Criteria`

## 5. Planner Disk Receipt (`chapters/<ch_id>/planner-notes.md`)

Write `chapters/<ch_id>/planner-notes.md` (no frontmatter) on disk **before** returning so findings survive timeouts:

- `## Files Written` — Relative paths of `spec.md` and `tasks/*.md` written.
- `## Task Summaries` — One-line summary per task worksheet.
- `## Root Spec Issues` — Cross-chapter signature conflicts needing root `spec.md` updates, or `None`.
- `## Open Questions` — Unresolved empirical triggers or user decisions, or `None`.
