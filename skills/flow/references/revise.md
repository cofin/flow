# Flow Revise (`/flow:revise`, alias `/flow:refine`)

Update, split, or deepen a root specification (`specs/<flow_id>/spec.md`), nested chapter specification (`specs/<flow_id>/chapters/<ch_id>/spec.md`), and task blueprints (`tasks/<id>-<slug>.md`) **in place in present tense**—before execution (`/flow:refine`), when promoting an `empirical_dependent` chapter, when upgrading a `planning_quality: degraded` fallback plan on the primary frontier thinking model, or mid-execution when a chapter/task hits code drift (`/flow:revise`).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - zero-decision-implementation-readiness
  - anti-truncation-chapter-expansion
  - present-tense-full-plan-sync
  - write-time-okf-validation
  - fail-closed-no-production-mutation
  - fresh-validated-plan-resume
authority: skills/flow/references/revise.md
```
<!-- flow-execution-policy: end -->

## Workflow

### Phase 1: Scoped Inspection, Gap Scan, & Chapter Expansion Check

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and only the target `chapters/<ch_id>/spec.md`, `planner-notes.md`, and `tasks/*.md`.
2. Inspect `blocked_reason`/`unblock_condition` (when `state: blocked`), upstream empirical measurements in `replan_trigger` (when `planning_status: empirical_dependent`, promoting to `planning_status: complete` and `replan_trigger: null`), or `planning_degraded_reason` (upgrading to `planning_quality: standard` + `planning_degraded_reason: null` once re-verified on the primary frontier thinking model).
3. **Anti-Truncation Check**: Never compress capabilities or omit docs/edge cases to fit `4` tasks; split oversized chapters (`> 4` tasks, `read_set > 6`, `estimated_loc > 250`) into additional `chNN-<slug>` chapters, and ensure checkpoints use fast (`< 60s`) lint + targeted unit test commands.

### Phase 2: Present-Tense Rewrite & Mandatory Root Roadmap Sync (Zero History)

1. Rewrite affected `chapters/<ch_id>/spec.md` and `tasks/<id>-<slug>.md` (`compact` or `full` per [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md)) in place in present tense with OKF v0.2 `sources:` + `[^id]:` footnotes, `<= 40`-line `<!-- truth: start -->` blocks, and zero standalone `---` body rules. If a `completed` chapter is reopened, reset `state: planned | active` and clear `last_reviewed_commit: null`.
2. Simultaneously rewrite root `specs/<flow_id>/spec.md` and `specs/<flow_id>/chapters/index.md` in place in present tense (`chapters:`, `current_chapter`, shared contracts, `[k/N files documented]`, checklist, and `## 6. Current State & Remaining Plan Snapshot`), reconciling any impacted downstream chapters `chK..chNN` without leaving `Revision History` sections or struck-through `~~` items. Never mark any chapter or task `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

### Phase 3: Deterministic OKF Validation, Scoped Review, & Re-Anchor `plan_commit`

1. Increment `plan_revision` once across root `spec.md`, revised `chapters/<ch_id>/spec.md`, and their `tasks/*.md`, reset unblocked tasks to `state: pending`, and run `/flow:validate` (`exit 0`).
2. Dispatch `1` combined Zero-Context Reviewer (`type_name="self"` on Google Antigravity) scoped strictly to root `spec.md`, `chapters/index.md`, and the revised chapter(s), adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`), surface any `planning_quality: degraded` warning, and stamp `status: stable` + `plan_commit: <HEAD_SHA>` upon `Approve`.
