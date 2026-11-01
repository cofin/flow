---
name: flow-planning
description: "Use when drafting Master PRDs (/flow:prd), authoring feature specifications and task worksheets (/flow:plan), revising plans (/flow:revise), or conducting technical research (/flow:research)."
disable-model-invocation: true
---

# Flow Planning

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,plan,revise,refine,research,task -->

## Trigger

Use for `prd` ([`../flow/references/prd.md`](../flow/references/prd.md)), `plan` ([`../flow/references/plan.md`](../flow/references/plan.md)), `revise` / `refine` ([`../flow/references/revise.md`](../flow/references/revise.md)), and `research` / `task` ([`../flow/references/research.md`](../flow/references/research.md)).

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, draft, gap_scan, zero_context_review, adjudication, approved, revise, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task, fragile_line_numbers]
    require: [requirement_to_task_traceability, symbol_anchored_targets, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [rewrite_in_present_tense, increment_plan_revision_once, sync_revision_to_spec_and_tasks, reanchor_plan_commit]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    adjudication: [ADOPT, CONTEST]
```

## Planning Hierarchy (`PRD` &rarr; `Plan (Spec)` &rarr; `Task Worksheet`)

| Level | Artifact | Command & Owner | Scope & Altitude |
| --- | --- | --- | --- |
| **1. Initiative Roadmap (`PRD`)** | `.agents/bundles/specs/<prd_id>/spec.md` | `/flow:prd <goal>` (`@prd-orchestrator`) | Multi-flow initiative roadmap with locked cross-cutting architectural decisions and ordered `state: draft` child flow charters (`specs/<child_id>/spec.md`). Never contains code-level task worksheets. |
| **2. Feature Specification (`Plan`)** | `.agents/bundles/specs/<flow_id>/spec.md` | `/flow:plan <goal_or_flow_id>` (`@plan-generator`) | Single cohesive feature/PR (`1–8` tasks): `1. Specification & Context` (`Upstream Execution Baseline`, `Code Analysis Summary` table with `path/to/file::Symbol`, `Relevant Patterns`), `2. Requirements` (`R1..RN`, constraints, scenarios, alternatives), `3. Requirement-to-Task Traceability Matrix`, `4. Implementation Plan` (phased checklist with mandatory `Phase Recovery Checkpoints`), `5. Continuity Snapshot`. |
| **3. Task Worksheet (`Task`)** | `.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md` | Authored by `/flow:plan`, revised by `/flow:revise`, executed by `/flow:implement` (`@executor`) | One stateless subagent turn and one atomic Git commit (vertical slice of production code + canonical module unit tests anchored to `path/to/file::Symbol`). |

## Workflow

1. **Ground in Bundle & Codebase**: Read `.agents/bundles/index.md`, applicable `knowledge/**` chapters, `.agents/skills/index.md`, and target source files. Dispatch `@researcher` subagents only for independent external or cross-subsystem unknowns, promoting findings to `research/<topic>_<YYYYMMDD>.md`.
2. **Resolve Design Frontier (`structured-choice-v1`)**: Present unresolved architectural decisions one at a time with opinionated recommendations (`<Label> (Recommended)`).
3. **Author Rich Spec & Disjoint Vertical-Slice Worksheets**: Write `spec.md` and `tasks/<id>-<slug>.md` under `.agents/bundles/specs/<flow_id>/`.
4. **Dynamic, Zero-Context Focused Review & Finding Adjudication**:
   - Dispatch zero-context reviewers (using Antigravity's `run_workflow` `parallel()` with `schema=FINDINGS_SCHEMA` and persistent multi-turn reviewer handles when available, or isolated `@code-reviewer` / `.agents/agents/<domain>-reviewer` subagents) passing **only disk paths** (`spec.md`, `tasks/*.md`, matching `.agents/skills/`, and `knowledge/` chapters)—never chat history.
   - Adjudicate every finding explicitly: **`ADOPT`** valid findings by updating `spec.md` and `tasks/<id>-<slug>.md` in present tense, or **`CONTEST`** false positives by citing exact `path/to/file::Symbol` code or `false-positive-suppressions.md` rules.
5. **Approval Gate**: Present the Adjudication Ledger and `Approve | Revise`. Upon approval, stamp `plan_commit = HEAD` across `spec.md` and all `tasks/*.md` and hand off to `/flow:implement`.

## Verification Strategy Selection

| Strategy | Change Class | Initial Evidence | Final Evidence |
| --- | --- | --- | --- |
| `behavior_tdd` | New observable behavior | Focused behavior test fails (Red) because behavior is absent. | Focused test and aggregate verification pass (Green). |
| `regression_tdd` | Defect correction | Focused reproduction test fails (Red) with the reported symptom. | Regression and aggregate verification pass (Green). |
| `characterization` | Behavior-preserving refactor or deletion | Existing focused behavior baseline passes before change. | Same behavior baseline passes unchanged after refactor. |
| `static_validation` | Manifest, config, schema, or tooling | Native validator, linter, or typechecker runs. | Representative violation fails as expected; restored gates pass. |
| `documentation_validation` | Links, examples, or OKF bundle docs | Documentation/link validator runs. | Markdown lint, link resolution, and OKF validation pass. |
| `integration_acceptance` | Multi-component composition | Focused integration baseline runs. | End-to-end scenario and negative refusal paths pass. |

## Guardrails

- Planning modifies files exclusively under `.agents/bundles/specs/<flow_id>/` (plus `bundles/index.md`, `bundles/log.md`, and `bundles/research/`). Never edit application source code during planning.
- Anchor all targets to `path/to/file::Symbol`; never rely on fragile line numbers.
- Place all planned unit tests inside existing canonical module test files (never standalone `test_*remediation*.py` or `test_*audit*.py` files).

## Output

Return the authored `spec.md` path, task worksheet summary table, Review Adjudication Ledger (`ADOPT` vs. `CONTEST`), and the `Approve | Revise` prompt.

## Validation

Confirm `spec.md` and every `tasks/<id>-<slug>.md` carry valid OKF v0.2 frontmatter, `plan_revision` matches across `spec.md` and all tasks, every requirement maps to at least one task worksheet, and all target files are anchored to `path/to/file::Symbol`.
