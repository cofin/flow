# Flow PRD (`/flow:prd`)

Co-design a **Master PRD & Multi-Chapter Flow Roadmap** (`.agents/bundles/specs/<flow_id>/spec.md`), frontmatter-free chapter catalog (`specs/<flow_id>/chapters/index.md`), and upfront detailed chapter specifications and task blueprints (`specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/{spec.md,planner-notes.md,tasks/*.md}`) across `2..N` chapters (zero upper cap on chapter count).

Use [`interaction.md`](interaction.md) (`structured-choice-v1`), [`state.md`](state.md), and [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md). **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or the primary checkout's `.agents/bundles/` inside `local-only` git worktrees); never modify application source code during `/flow:prd`.

## Workflow

### Phase 1: Bundle Intelligence & Sharded `flow-scout` Reconnaissance (`Facts First`)

1. Read `.agents/bundles/index.md`, `product/**`, `knowledge/**`, `research/**`, and `.agents/skills/index.md`.
2. **Sharded Read-Only Scouts (`SubsystemDigest`)**:
   - Keep coordinator exploration under `< 25k` tokens by probing live quotas via `swarm(action="models", all=True)` + `tools/model_router.py` and calling `run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [...], "scout_agent": heavy_agent, "narrow_agent": narrow_agent})` on Google Antigravity (routing multi-turn scouts to high/extra-thinking Flash and `narrow_fetch` `<= 3`-file lookups to fast Flash) or parallel `@researcher` subagents (`model: "sonnet"` on Claude Code; never `"haiku"` for multi-module synthesis).
   - Promote external SDK/protocol audits into OKF v0.2 `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` notes ([`research.md`](research.md)).

### Phase 2: Design-Tree Frontier Discovery & Coverage Gate (`structured-choice-v1`)

1. Ask `1` question at dependent architectural forks and batch `2–3` orthogonal leaf questions once on a settled frontier ([`interaction.md`](interaction.md)), placing `<Label> (Recommended)` first.
2. Resolve seam selection + rejected alternatives, concrete shared types & edge-case semantics, public-seam test surfaces, fast (`< 60s`) chapter lint/test checkpoints, `docs/**` + OKF targets, and `ch01..chNN` decomposition (with any `empirical_dependent` triggers) before drafting.

### Phase 3: Lock Root Roadmap & Invoke `flow-spec-planning`

1. Write `.agents/bundles/specs/<flow_id>/spec.md` (`type: Spec`, `flow_id: <flow_id>`, `status: draft`, `state: planned`, `planning_quality: standard`, `has_chapters: true`, `chapters: [ch01-<slug>, ...]`, `current_chapter: ch01-<slug>`, `sources:` + `[^id]:` footnotes, `<= 40`-line `<!-- truth: start -->` block, zero standalone `---` body rules) covering all 6 normative sections from [`state.md`](state.md), including **North Star Goal & Problem Framing** in plain English, shared contracts, Flow-Wide Documentation & OKF Knowledge Plan (`[0/N files documented]`), and fast (`< 60s`) Chapter Recovery Checkpoints.
2. Write frontmatter-free `.agents/bundles/specs/<flow_id>/chapters/index.md` cataloging `ch01-<slug>..chNN-<slug>`.
3. **Upfront Chapter Blueprint Generation & Deterministic OKF Gate**:
   - On Google Antigravity, invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-spec-planning/workflow.py", Args={"flow_id": "<flow_id>", "chapters": [...], "planner_mode": "per_chapter", "review": "per_chapter", "planner_agent": resolved_planner_agent, "reviewer_agent": resolved_spec_rev_agent, "planner_degraded": is_degraded})` keeping Planner and Spec Review on `>= 25%` Pro quota whenever available, and declare non-overlapping task `files:`/`tests:` paths across chapters where architecture permits so `/flow:implement` qualifies for bounded `small_swarm` execution.
   - On other harnesses, fan out parallel `@plan-generator` subagents on the primary frontier thinking model (`inherit` / Opus family / `high`), passing root `spec.md`, [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and scoped subsystem digests. Each planner writes `chapters/<ch_id>/planner-notes.md` on disk before returning.
   - Fold any `Root Spec Issues` from `planner-notes.md` into root `spec.md` and run `/flow:validate` (`exit 0`).

### Phase 4: Zero-Context Review & Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)

1. Run `1` combined reviewer for `<= 4` chapters (`review="single"`) or parallel per-chapter + cross-chapter reviewers for `> 4` chapters (`review="per_chapter"`), passing strictly on-disk paths ([`spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)).
2. Adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`), rewriting affected chapter and root files in place in present tense, incrementing `plan_revision` once, re-validating OKF via `/flow:validate`, and running a second review round only on chapters modified by `ADOPT` fixes.

### Phase 5: Degraded-Model Disclosure, Approval Gate, & Chapter 1 Handoff

1. Whenever `planning_quality == "degraded"` (quota fallback or disk-timeout recovery prevented planning on the primary frontier thinking model), surface an explicit warning banner stating `planning_degraded_reason` before presenting `Approve | Revise | Refine`.
2. Upon approval, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across root `spec.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`, update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off `ch01-<slug>` to `/flow:implement <flow_id>`.
