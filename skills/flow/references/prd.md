# Flow PRD (`/flow:prd`)

Design a **Master PRD & Multi-Chapter Roadmap** (`.agents/bundles/specs/<flow_id>/spec.md`), frontmatter-free chapter catalog (`specs/<flow_id>/chapters/index.md`), and chapter specs plus task worksheets (`specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/{spec.md,planner-notes.md,tasks/*.md}`) across `2..N` chapters.

Use [`interaction.md`](interaction.md), [`state.md`](state.md), and [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md).
**No Production Code Rule**: Planning writes only under `.agents/bundles/` (or the primary checkout's `.agents/bundles/` in `local-only` git worktrees); never edit application source code during `/flow:prd`.

## Workflow

### Phase 1: Bundle Review & Parallel Research

1. Read `.agents/bundles/index.md`, `product/**`, `knowledge/**`, `research/**`, and `.agents/skills/index.md`.
2. **Parallel Read-Only Research**:
   - Keep coordinator exploration small by dispatching `flow-scout` (`run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [...], "query": "..."})`) on Google Antigravity or parallel `@researcher` subagents elsewhere ([`orchestration.md`](orchestration.md)).
   - Promote external SDK or protocol audits into OKF v0.2 `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` notes ([`research.md`](research.md)).

### Phase 2: Open Decisions & Pre-Draft Check

1. Skip questioning for already-clear areas.
2. Ask `1` question at unresolved dependent architectural forks, and batch `2-3` independent leaf questions once on settled choices ([`interaction.md`](interaction.md)), putting `<Label> (Recommended)` first.
3. Settle interface selection and alternatives, shared types and edge cases, public interface tests, fast (`< 60s`) lint/test checkpoints, `docs/**` and OKF targets, and `ch01..chNN` chapters (including any `empirical_dependent` triggers) before drafting.
4. Keep no artificial caps on task count, `read_set`, or `estimated_loc`, and allow `compact` worksheets for straightforward tasks.

### Phase 3: Lock Roadmap & Run `flow-spec-planning`

1. Write `.agents/bundles/specs/<flow_id>/spec.md` (`type: Spec`, `flow_id: <flow_id>`, `status: draft`, `state: planned`, `planning_quality: standard`, `has_chapters: true`, `chapters: [ch01-<slug>, ...]`, `current_chapter: ch01-<slug>`).
2. Include `sources:` + `[^id]:` footnotes, a `<= 40`-line `<!-- truth: start -->` truth block, zero standalone `---` body rules, and all six sections from [`state.md`](state.md).
3. Include plain-English goal and problem framing, shared contracts, `## 3. Documentation & OKF Knowledge Plan` (`[0/N files documented]`), and fast (`< 60s`) Chapter Recovery Checkpoints.
4. Write frontmatter-free `.agents/bundles/specs/<flow_id>/chapters/index.md` cataloging `ch01-<slug>..chNN-<slug>`.
5. **Upfront Chapter Worksheet Generation & Validation**:
   - On Google Antigravity, invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-spec-planning/workflow.py", Args={"flow_id": "<flow_id>", "chapters": [...], "seed_files": [...], "planner_mode": "per_chapter", "review": "per_chapter"})` with Planner and Spec Review on the `strong` model role ([`orchestration.md`](orchestration.md)).
   - Declare separate-file tasks around `<= 250` LOC and `<= 3` files so `/flow:implement` can run workers in parallel steps.
   - On other harnesses, fan out parallel `@plan-generator` subagents using resolved `strong` profiles, passing root `spec.md`, [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and scoped subsystem summaries. Each planner writes `chapters/<ch_id>/planner-notes.md` on disk before returning.
   - Fold any `Root Spec Issues` from `planner-notes.md` into root `spec.md` and run `/flow:validate` (`exit 0`).

### Phase 4: Independent Review & Decisions

1. Run `1` combined reviewer for `<= 4` chapters (`review="single"`) or parallel per-chapter and cross-chapter reviewers for `> 4` chapters (`review="per_chapter"`), passing only on-disk paths ([`spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)).
2. Decide on each finding (`ADOPT` / `CONTEST` / `ESCALATE`), rewriting affected chapter and root files in place in present tense.
3. Increment `plan_revision` once, re-run `/flow:validate`, and run a second review round only on chapters modified by `ADOPT` fixes.

### Phase 5: Approval & Chapter 1 Handoff

1. Whenever `planning_quality == "degraded"`, display a warning banner stating `planning_degraded_reason` before presenting `Approve | Revise | Refine`.
2. Upon approval, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across root `spec.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`.
3. Update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off `ch01-<slug>` to `/flow:implement <flow_id>`.
