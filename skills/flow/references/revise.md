# Flow Revise (`/flow:revise`, `/flow:refine`)

Update, split, or deepen a root spec (`specs/<flow_id>/spec.md`), chapter spec (`specs/<flow_id>/chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) **in place in present tense**.
Use this before execution (`/flow:refine`), when promoting an `empirical_dependent` chapter, when upgrading a `planning_quality: degraded` plan on the strongest model, or mid-execution after code drift (`/flow:revise`).

## Workflow

### Phase 1: Scoped Inspection & Scope Check

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and only the target `chapters/<ch_id>/spec.md`, `planner-notes.md`, and `tasks/*.md`.
2. Inspect `blocked_reason` and `unblock_condition` when `state: blocked`, or upstream measurements in `replan_trigger` when `planning_status: empirical_dependent` (promoting to `planning_status: complete` and `replan_trigger: null`).
3. When `planning_quality: degraded`, re-verify the plan on the strongest model and upgrade to `planning_quality: standard` with `planning_degraded_reason: null`.
4. **Plan the Whole Scope**: Never drop capabilities, docs, or edge cases, and never split one cohesive feature into unnecessary tiny chapters.
5. Keep tasks sized to the feature with their own tests (no artificial caps on chapter task count, `read_set`, or `estimated_loc`; `compact` worksheets are allowed everywhere), and keep checkpoints under `< 60s`.

### Phase 2: Present-Tense Rewrite & Roadmap Sync

1. Rewrite affected `chapters/<ch_id>/spec.md` and `tasks/<id>-<slug>.md` (`compact` or `full` per [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md)) in place in present tense.
2. Include OKF v0.2 `sources:` + `[^id]:` footnotes, `<= 40`-line `<!-- truth: start -->` truth blocks, and zero standalone `---` body rules.
3. If a `completed` chapter is reopened, reset `state: planned | active` and clear `last_reviewed_commit: null`.
4. Rewrite root `specs/<flow_id>/spec.md` and `specs/<flow_id>/chapters/index.md` in place in present tense (`chapters:`, `current_chapter`, shared contracts, `[k/N files documented]`, checklist, and `## 6. Current State & Remaining Plan Snapshot`).
5. Sync any impacted downstream chapters `chK..chNN` without leaving `Revision History` sections or struck-through `~~` items.
6. Never mark any chapter or task `deferred` or `skipped` without `deferred_by: "user"` and `deferred_reason`.

### Phase 3: Validation, Independent Review & Anchor

1. Increment `plan_revision` once across root `spec.md`, revised `chapters/<ch_id>/spec.md`, and their `tasks/*.md`, reset unblocked tasks to `state: pending`, and run `/flow:validate` (`exit 0`).
2. Dispatch `1` combined Independent Reviewer (`type_name="self"` on Google Antigravity) scoped to root `spec.md`, `chapters/index.md`, and the revised chapter(s).
3. Decide on each finding (`ADOPT` / `CONTEST` / `ESCALATE`), surface any `planning_quality: degraded` warning, and stamp `status: stable` plus `plan_commit: <HEAD_SHA>` upon `Approve`.
