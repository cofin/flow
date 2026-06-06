---
name: flow-planning
description: "Use when drafting PRDs, researching, planning, refining, revising, or creating .agents/specs/<flow_id>/spec.md worksheets for Flow."
---

# Flow Planning

Use this lifecycle skill for PRDs, research, single-flow planning, refinement, revisions, and task creation.

## Workflow

1. Read project context, patterns, knowledge chapters, and relevant existing specs before asking questions.
2. Research code paths and external APIs before locking implementation decisions.
3. Create PRDs as roadmap epics and single-flow specs as implementation worksheets.
4. Refine until tasks include concrete files, behavior, tests, commands, and acceptance criteria.
5. Create Beads epics/tasks and sync markdown views according to policy.

## Interrogate Before Finalizing (Grill)

Before locking a PRD, spec, or refined worksheet, interrogate the plan until every decision branch is resolved. This is how Flow meets the Zero-Ambiguity Standard and the Stateless Executor Test — apply it in `flow-prd`, `flow-plan`, and especially `flow-refine`.

- Ask **one question at a time** and wait for the answer before the next. Walk the decision tree top-down, resolving dependencies between decisions in order.
- For **every** question, give your **recommended answer** and the trade-off, so the user confirms rather than composes from scratch.
- If a question is answerable from the repo, **explore the codebase / `patterns.md` / `knowledge/` / `tech-stack.md` instead of asking**. Only ask product or trade-off questions a human must decide.
- Challenge the plan against the project's **domain language**: reuse the terminology already in `patterns.md` and `knowledge/` chapters, and flag/resolve term conflicts before finalizing.
- Record decisions that are **hard to reverse, surprising, and a real trade-off** into `knowledge/` (or `learnings.md`); skip low-value notes.
- Stop only when no open branch remains and a zero-context executor could implement from the artifact alone.
- The finished spec/worksheet doubles as a **handoff**: reference existing artifacts (PRD, patterns, knowledge, affected files) rather than duplicating them, and name the next skill to invoke. (If the host exposes `grill-me` / `grill-with-docs` / `handoff` skills, you may invoke them to drive these steps; otherwise apply the discipline directly.)

## Guardrails

- Planning must be decision-complete; do not defer obvious research to implementation.
- Ask only product or tradeoff questions that cannot be answered from the repo.
- Store plans under `.agents/specs/<flow_id>/`, not ad hoc docs paths.
- Do not modify production code during planning.

## Validation

- Confirm every requirement maps to an implementation task and test scenario.
- Confirm tasks are small enough for a low-context executor to complete without guessing.
- Run spec review or code-reviewer validation before presenting final planning artifacts when available.

## References Index

- [PRD](../flow/references/prd.md)
- [Plan](../flow/references/plan.md)
- [Research](../flow/references/research.md)
- [Refine](../flow/references/refine.md)
- [Revise](../flow/references/revise.md)
- [Task](../flow/references/task.md)

## Example

User: "Plan skill trigger optimization."

Action: inspect current skills and validators, ask unresolved product tradeoffs, create a Flow spec with Beads tasks, and refine until the implementation path is explicit.
