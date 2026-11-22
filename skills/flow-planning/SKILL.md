---
name: flow-planning
description: "Use when writing Master PRDs, authoring feature or chapter specifications and task worksheets, revising plans in present tense, or running primary-source research. Don't use for writing production code (use flow-execution), initializing .agents/ (use flow-setup), or final review (use flow-completion)."
disable-model-invocation: true
---

# Flow Planning

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,spec,plan,revise,refine,research,task -->

## Trigger

Use for `prd` ([`../flow/references/prd.md`](../flow/references/prd.md)), `spec` / `plan` ([`../flow/references/spec.md`](../flow/references/spec.md)), `revise` / `refine` ([`../flow/references/revise.md`](../flow/references/revise.md)), and `research` / `task` ([`../flow/references/research.md`](../flow/references/research.md)).

## Planning Sizes & Full Scope

Scale planning ceremony (`Small`, `Medium`, `Large`) to match the change without trimming requirements, edge cases, or documentation targets.
See the full sizing table (`Trigger`, `Research`, `Layout`, `Worksheet`, `Planners`, `Review`) in [`spec.md`](../flow/references/spec.md#planning-sizes-small--medium--large):

- **Small / Single-Chapter**: Cohesive change with `spec.md` (`has_chapters: false`), `compact` worksheets by default, planned directly in the coordinator.
- **Medium (`2..4` chapters)**: Genuine stages, parallel subsystems, or `empirical_dependent` boundaries; planned in parallel with `flow-spec-planning` and `1` combined reviewer.
- **Large (`> 4` chapters or `/flow:prd`)**: Full chaptered spec with no chapter cap; per-chapter and cross-chapter independent reviewers.

## Workflow

1. **Ground in Bundle & Right-Sized Research**:
   - Read `.agents/bundles/index.md`, applicable `knowledge/**` chapters, and `.agents/skills/index.md`. In `local-only` git worktrees, read from the primary checkout's `.agents/`.
   - For `<= 8` files across `<= 2` modules, read source files directly in the coordinator. For larger surfaces, invoke `workflows/flow-scout/workflow.py` on Google Antigravity or parallel `@researcher` subagents ([`orchestration.md`](../flow/references/orchestration.md)).
2. **Resolve Open Decisions Only**:
   - Skip questioning for areas already settled by the prompt and repository code. Ask `1` question at unresolved dependent forks and batch `2-3` independent questions into one round ([`../flow/references/interaction.md`](../flow/references/interaction.md)), placing `<Label> (Recommended)` first.
   - Make module interfaces, contracts, public-interface tests, fast (`< 60s`) lint/test checkpoints, `docs/**` + OKF targets, and chapter breakdown concrete before drafting.
3. **Author OKF v0.2 Specs, Planner Notes, & Validation**:
   - **Single-Chapter (`has_chapters: false`)**: Author `specs/<flow_id>/spec.md` and `specs/<flow_id>/tasks/tNN-*.md` (`worksheet_format: compact` by default; `full` for complex public contracts) directly in the coordinator and run `/flow:validate`.
   - **Multi-Chapter (`Medium` & `Large`)**: Write root `specs/<flow_id>/spec.md` and frontmatter-free `specs/<flow_id>/chapters/index.md`. Then run `workflows/flow-spec-planning/workflow.py` on Google Antigravity, or parallel `@plan-generator` subagents passing [`plan-schema-card.md`](../../templates/agent/plan-schema-card.md) elsewhere. Each planner writes `chapters/<ch_id>/planner-notes.md` on disk, and `/flow:validate` runs before spec review.
   - **Strongest Model & Degraded Warning**: Resolve planner and spec-review routes via `flow models route --task-kind planning --json` (`strong` role). Keep task `files:`/`tests:` on separate files (`<= 250` LOC, `<= 3` files) so execution runs in parallel steps ([`orchestration.md`](../flow/references/orchestration.md)). If quota fallback prevents the `strong` model, stamp `planning_quality: degraded` + `planning_degraded_reason` in `spec.md` and warn before approval.
4. **Independent Spec Review (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - Default to `1` combined independent reviewer (`review="single"`) for single-chapter and `Medium` plans (`<= 4` chapters). Run a second round only if `Critical` or `Important` findings are adopted, scoped to modified chapters.
5. **Approval Check (`Approve | Revise | Refine`)**:
   - Present `planning_quality` (with any degraded warning), the chapter/task summary table, `[0/N files documented]` checklist, and review summary. Upon approval, stamp `status: stable` and `plan_commit: <HEAD_SHA>` and hand off to `/flow:implement <flow_id>`.

## Guardrails

- **No Production Code During Planning**: Modify files only under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` spikes) so user plan review covers intent before repository mutations.
- **Plan the Whole Scope & Keep Checkpoints Fast**: Never truncate scope or impose artificial caps on task count, `read_set`, `files`, or `estimated_loc`. Allow `compact` worksheets for any size, omit standalone `---` rules and `Revision History` sections from bundle bodies so YAML frontmatter parsers stay unambiguous, and keep chapter checkpoints under `60s`.

## Example

```bash
flow models route --task-kind planning --json
flow spec preflight <flow_id> --json
```

## Output

Return the root `spec.md` path, `planning_quality` status (with warning if `degraded`), chapter/task table, `[0/N files documented]` summary, review summary, and the `Approve | Revise | Refine` choice.

## Validation

Confirm `/flow:validate` passes with zero errors across root `spec.md`, frontmatter-free `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`. Verify `plan_revision` matches and any fallback from `strong` sets `planning_quality: degraded` with `planning_degraded_reason`.
