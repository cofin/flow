---
name: flow-planning
description: "Use when co-designing Master PRDs (/flow:prd), authoring feature specifications and vertical-slice task worksheets (/flow:plan), revising or refining plans (/flow:revise, /flow:refine), or running primary-source research and throwaway prototypes (/flow:research, /flow:task)."
disable-model-invocation: true
---

# Flow Planning (Co-Design & Zero-Context Verification)

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,plan,revise,refine,research,task -->

## Trigger

Use for `prd` ([`../flow/references/prd.md`](../flow/references/prd.md)), `plan` ([`../flow/references/plan.md`](../flow/references/plan.md)), `revise` / `refine` ([`../flow/references/revise.md`](../flow/references/revise.md)), and `research` / `task` ([`../flow/references/research.md`](../flow/references/research.md)).

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, frontier_discovery, draft, gap_scan, zero_context_review, adjudication, approved, revise, refine, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task, fragile_line_numbers, shallow_passthrough_seam]
    require: [problem_framing, alternatives_evaluated, deep_module_seams, requirement_to_task_traceability, symbol_anchored_targets, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [rewrite_in_present_tense, increment_plan_revision_once, sync_revision_to_spec_and_tasks, reanchor_plan_commit]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    adjudication: [ADOPT, CONTEST, ESCALATE]
```

## Stateful Planning vs. Zero-Context Verification

- **Stateful Planner & Adjudicator (`@prd-orchestrator`, `@plan-generator`)**: Holds conversational history, `.agents/bundles/` context, codebase findings, and trade-offs. Explores the design tree with the user, drafts self-contained specs and worksheets, and adjudicates review findings. **Never writes or modifies production source code during planning.**
- **Zero-Context Verifier (`@code-reviewer`, `<domain>-reviewer`)**: Runs in a fresh, isolated subagent context (`model: inherit`) with **only on-disk repository paths** (`spec.md`, `tasks/*.md`, `.agents/bundles/knowledge/**`, `.agents/skills/**`, and source files)—never chat history. Pressure-tests the spec across **Cold-Reader Comprehension**, **Architectural & Deep-Module Seam Review**, **Zero-Decision Implementation Readiness**, and **Prose & Style Debloat**.

## Planning Hierarchy (`PRD` &rarr; `Plan (Spec)` &rarr; `Task Worksheet`)

| Level | Artifact | Command & Owner | Scope & Altitude |
| --- | --- | --- | --- |
| **Initiative Roadmap (`PRD`)** | `.agents/bundles/specs/<prd_id>/spec.md` | `/flow:prd <goal>` (`@prd-orchestrator`) | Multi-flow initiative roadmap (`2–8` chapters) framing the problem and objectives in plain English, locking cross-cutting architectural seams, and seeding `state: draft` child flow charters (`specs/<child_id>/spec.md`). Never contains code-level task worksheets. |
| **Feature Specification (`Plan`)** | `.agents/bundles/specs/<flow_id>/spec.md` | `/flow:plan <goal_or_flow_id>` (`@plan-generator`) | Single cohesive feature/PR (`1–8` tasks): `1. Specification & Context` (`Upstream Execution Baseline`, `Code Analysis Summary` with `path/to/file::Symbol`, `Relevant Patterns & Domain Glossary`), `2. Requirements & Architecture` (`R1..RN`, public seams & adapters, scenarios, `Alternatives Considered`), `3. Requirement-to-Task Traceability Matrix`, `4. Implementation Plan` (phased checklist with `Phase Recovery Checkpoints`), `5. Continuity Snapshot`. |
| **Task Worksheet (`Task`)** | `.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md` | Authored by `/flow:plan`, refined by `/flow:revise`, executed by `/flow:implement` (`@executor`) | One isolated executor turn and one atomic Git commit (vertical slice of production code + public-seam tests in canonical module test files anchored to `path/to/file::Symbol`). |

## Workflow

1. **Ground in Bundle, Domain Glossary, & Codebase (`Facts First`)**:
   - Read `.agents/bundles/index.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, `.agents/skills/index.md`, and target source files.
   - Never ask the user for facts discoverable in the repository. Dispatch `@researcher` subagents (`model: inherit`) for external SDK/API primary sources or multi-subsystem unknowns, or run a time-boxed throwaway prototype in `.agents/scratch/<slug>/` ([`../flow/references/research.md`](../flow/references/research.md)).
2. **Walk the Design-Tree Frontier (`structured-choice-v1`)**:
   - Map unresolved product, seam, and trade-off choices as a design tree. Ask one `structured-choice-v1` decision at a time on the current prerequisite-settled frontier ([`../flow/references/interaction.md`](../flow/references/interaction.md)), citing `path/to/file::Symbol` and placing `<Label> (Recommended)` first.
   - For non-trivial new interfaces, compare at least two distinct interface shapes on **depth** (leverage hidden behind a small interface), **locality**, and **seam/adapter placement**, and confirm the public seams under test.
3. **Author Self-Contained Spec & Vertical-Slice Worksheets (Zero-Decision Rule)**:
   - Write `spec.md` and `tasks/<id>-<slug>.md` under `.agents/bundles/specs/<flow_id>/` leaving **zero architectural or design decisions** to the implementer.
4. **Zero-Context Verification & Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - Dispatch isolated zero-context reviewers (via Antigravity's `run_workflow` `parallel()` with `schema=SPEC_REVIEW_SCHEMA` and persistent reviewer handles when available, or isolated `@code-reviewer` / `.agents/agents/<domain>-reviewer` subagents, or emit a copyable 5-backtick review prompt if requested for a separate window) passing **only disk paths**.
   - Adjudicate every finding: **`ADOPT`** valid fixes in present tense, **`CONTEST`** false positives or YAGNI scope creep with `path/to/file::Symbol` or `FP-*` evidence, or **`ESCALATE`** genuine product trade-offs to the user.
5. **Approval Gate (`Approve | Revise | Refine`)**:
   - Present the Adjudication Ledger and `Approve | Revise | Refine`. Upon approval, stamp `plan_commit = HEAD` across `spec.md` and all `tasks/*.md` and hand off to `/flow:implement`.

## Guardrails

- **No Production Code During Planning**: Modify files exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during a throwaway prototype spike).
- **Symbol-Anchored Targets & Canonical Tests**: Anchor all targets to `path/to/file::Symbol` (never fragile line numbers) and place all planned tests at confirmed public seams inside existing canonical module test files.

## Output

Return the authored `spec.md` path, task worksheet summary table, Review Adjudication Ledger (`ADOPT` / `CONTEST` / `ESCALATE`), and the `Approve | Revise | Refine` gate.

## Validation

Confirm `spec.md` and every `tasks/<id>-<slug>.md` carry valid OKF v0.2 frontmatter, `plan_revision` matches across `spec.md` and all tasks, alternatives are documented, every requirement maps to a task worksheet and public-seam test surface, and all targets use `path/to/file::Symbol`.
