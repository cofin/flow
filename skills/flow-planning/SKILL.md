---
name: flow-planning
description: "Use when co-designing Master PRDs (/flow:prd), authoring high-detail feature and chapter specifications and vertical-slice task blueprints (/flow:spec, alias /flow:plan), revising or refining plans in present tense (/flow:revise, /flow:refine), or running primary-source research and throwaway prototypes (/flow:research, /flow:task)."
disable-model-invocation: true
---

# Flow Planning (Proportional Co-Design, Quota-Aware Workflows, & Zero-Context Verification)

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,spec,plan,revise,refine,research,task -->

## Trigger

Use for `prd` ([`../flow/references/prd.md`](../flow/references/prd.md)), `spec` / `plan` ([`../flow/references/spec.md`](../flow/references/spec.md)), `revise` / `refine` ([`../flow/references/revise.md`](../flow/references/revise.md)), and `research` / `task` ([`../flow/references/research.md`](../flow/references/research.md)).

## Proportional Planning Tiers & Anti-Truncation

Scale orchestration ceremony and worksheet format to the size of the change while preserving **zero scope truncation** (every requirement, edge case, and documentation/OKF target maps to a concrete task):

| Tier | Trigger | Scouting | Layout & Worksheet | Planners | Spec Review |
| --- | --- | --- | --- | --- | --- |
| **Small / Single-Chapter** | Cohesive single deliverable (no intermediate checkpoint needed) | Coordinator direct read (`<= 8` files) or `flow-scout` | Single-chapter `spec.md` + `compact` worksheets by default (`full` only for complex public seams; [`plan-schema-card.md`](../../templates/agent/plan-schema-card.md)) | Coordinator directly (`0` subagents) | `1` combined reviewer (`1` round) |
| **Medium** | `2..4` genuine stages, parallel subsystems, or `empirical_dependent` gates | Direct read (`<= 8` files) or `flow-scout` (`flash`/`sonnet`) | Root `spec.md` + `chapters/index.md` + `2..4` chapters (`compact` or `full` worksheets) | `flow-spec-planning` (`per_chapter` parallel for `>= 2` chapters) | `1` combined reviewer (`2nd` round only on adopted `Critical`/`Important` findings) |
| **Large** | `> 4` chapters or `/flow:prd` | `flow-scout` parallel digests (`flash`/`sonnet`) | Root `spec.md` + `chapters/index.md` + `ch01..chNN` (`compact` or `full` worksheets, zero cap) | `flow-spec-planning` (`per_chapter` parallel) | Per-chapter + cross-chapter reviewers |

## Workflow

1. **Ground in Bundle & Right-Sized Scouting (`Facts First`)**:
   - Read `.agents/bundles/index.md`, applicable `knowledge/**` chapters, and `.agents/skills/index.md` (routing to the primary checkout's `.agents/` inside `local-only` git worktrees).
   - For `<= 8` files across `<= 2` modules, read source files directly in the coordinator. For larger surfaces, invoke the shipped `workflows/flow-scout/workflow.py` workflow on Google Antigravity (or parallel `@researcher` subagents on `sonnet`/`low` elsewhere; restrict `haiku`/`flash_lite` strictly to narrow `<= 3`-file fetches).
2. **Walk Unresolved Frontier Decisions Only (`structured-choice-v1`)**:
   - Skip questioning altogether for areas already settled by the prompt and repository code. Ask `1` question only at unresolved dependent design forks and batch `2–3` unresolved orthogonal questions into a single round ([`../flow/references/interaction.md`](../flow/references/interaction.md)), placing `<Label> (Recommended)` first.
   - Ensure seam choice, contracts, public-seam tests, fast (`< 60s`) lint/test checkpoints, `docs/**` + OKF targets, and concise chapter decomposition are concrete before drafting.
3. **Author OKF v0.2 Specs, Planner Notes, & Deterministic OKF Gate**:
   - **Single-Chapter (`has_chapters: false`)**: Author `specs/<flow_id>/spec.md` and `specs/<flow_id>/tasks/tNN-*.md` (`worksheet_format: compact` by default; `full` when needed for complex public contracts) directly in the coordinator and run `/flow:validate`.
   - **Multi-Chapter (`Medium` & `Large`)**: Write root `specs/<flow_id>/spec.md` and frontmatter-free `specs/<flow_id>/chapters/index.md`, then invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-spec-planning/workflow.py", Args={...})` (`auto` selects parallel `per_chapter` whenever `>= 2` chapters exist) on Google Antigravity, or parallel `@plan-generator` subagents passing [`plan-schema-card.md`](../../templates/agent/plan-schema-card.md) on other harnesses. Each planner writes `chapters/<ch_id>/planner-notes.md` on disk before finishing, and deterministic OKF validation runs before LLM review.
   - **Degraded-Model Warning (`planning_quality: degraded`)**: On Google Antigravity, probe live quotas (`swarm(action="models", all=True)`) and resolve via `tools/model_router.py`: route Coordinator, Planner, and Spec Review to the highest-quota frontier Pro model when remaining quota is `>= 25%` (`Opus` on Claude Code; `high` reasoning on Codex), and declare non-overlapping task `files:`/`tests:` paths wherever module boundaries allow so `/flow:implement` qualifies for parallel execution (`small_swarm` / `parallel_subagents`). Whenever Pro quota `< 25%`, fallback, or timeout disk-recovery forces planning onto Flash/Sonnet, stamp `planning_quality: degraded` + `planning_degraded_reason` in `spec.md` and display an explicit warning banner before approval.
4. **Zero-Context Spec Review & Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - Default to `1` combined Zero-Context Reviewer (`review="single"`) for single-chapter and `Medium` plans (`<= 4` chapters); run a second round only if `Critical` or `Important` findings are adopted, scoped strictly to modified chapters.
5. **Approval Gate (`Approve | Revise | Refine`)**:
   - Present `planning_quality` (and any degraded-model warning), the chapter/task summary table, `[0/N files documented]` manifest, and Adjudication Ledger. Upon approval, stamp `status: stable` and `plan_commit: <HEAD_SHA>` and hand off to `/flow:implement <flow_id>`.

## Guardrails

- **No Production Code During Planning**: Modify files exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` spikes).
- **Zero Scope Truncation, Zero Artificial Caps, & Fast Checkpoints**: Keep task worksheets cohesive with zero artificial caps on task count per chapter, `read_set`, `files`, or `estimated_loc`, allow `compact` worksheets across all tiers, never place standalone `---` rules or `Revision History` sections in bundle bodies, and never configure slow (`> 60s`) full test suites as intermediate chapter checkpoints.

## Output

Return the root `spec.md` path, `planning_quality` status (with prominent warning if `degraded`), chapter/task blueprint table, `[0/N files documented]` summary, Review Adjudication Ledger, and the `Approve | Revise | Refine` gate.

## Validation

Confirm `/flow:validate` passes with zero errors across root `spec.md`, frontmatter-free `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md` (`compact` or `full`), `plan_revision` matches, and any non-frontier fallback sets `planning_quality: degraded` with `planning_degraded_reason`.
