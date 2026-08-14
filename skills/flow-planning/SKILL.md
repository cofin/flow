---
name: flow-planning
description: "Use when drafting PRDs, researching, planning, refining, revising, or creating .agents/bundles/specs/<flow_id>/spec.md worksheets for Flow."
---

# Flow Planning

Use this lifecycle skill for PRDs, research, single-flow planning, refinement, revisions, and task creation.

`skills/flow/references/interaction.md` is the sole procedure authority for
every human decision and approval/refinement gate. `skills/flow/references/state.md`
is the authority for plan identity and Markdown mutations. Apply both with
ordinary agent tools; installed workflows never call a planning evaluator.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, draft, gap_scan, refine, revision_update, review, approved, revise, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task]
    require: [requirement_to_task_traceability, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [increment_plan_revision_once, copy_revision_to_spec_and_all_tasks, clear_plan_commit, rerun_validation]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    on_limit: blocked
```

## Workflow

1. **Close research.** Read project context, knowledge, existing specs, source,
   tests, CI, and relevant current external documentation. Resolve
   repository-answerable questions instead of deferring them to implementation.
   Ask only product/trade-off decisions, one at a time, through
   `structured-choice-v1`.
2. **Draft.** Create PRDs as roadmap specs and single-flow specs as executable
   worksheets. Include explicit requirement-to-task/test traceability and one
   complete authoritative task file per checklist item.
3. **Scan gaps.** Deterministically reject deferred research, unresolved
   decisions, stub bodies, vague verification, missing verification strategies,
   overlapping ownership, missing requirement coverage, or a task too large
   for one invocation and one commit.
4. **Refine.** Resolve one gap at a time. Research facts, ask the next
   structured decision when required, and split/rewrite tasks until all include
   concrete files, behavior, tests, commands, expected outcomes, and acceptance
   criteria.
5. **Update revision.** When plan-bearing content changes, apply one `revise`
   transaction: increment `plan_revision`, copy it to the spec and every task,
   clear `plan_commit`, and rerun validation. Preserve identity when no plan
   content changed; only a verified plan-bind checkpoint updates `plan_commit`.
6. **Review.** Request a fresh `code-reviewer` result, apply all actionable
   findings, update/revalidate, and request fresh review. Stop after three
   external rounds; unresolved Critical/Important findings return `blocked`
   with their exact list and require user direction. Never label that plan
   Ready.
7. **Gate with the user.** Before quality passes offer only `Revise|Refine`;
   after it passes offer exactly `Approve|Revise|Refine`. Put the contextual
   recommendation first. Approve advances; Revise asks one
   `open(revision_details)` follow-up; Refine asks the next structured gap; both
   edit, update identity as applicable, revalidate, and re-present. Cancellation
   stops without approval.
8. Reconcile `spec.md` checklist state from authoritative task files. Never
   persist an unapproved crucial artifact as approved.

## Interrogate Before Finalizing (Grill)

Before locking a PRD, spec, or refined worksheet, interrogate the plan until every decision branch is resolved. This is how Flow meets the Zero-Ambiguity Standard and the Stateless Executor Test — apply it in `flow-prd`, `flow-plan`, and especially `flow-refine`.

- Ask **one question at a time** through `structured-choice-v1` and wait for its
  normalized result before the next. Walk the decision tree top-down.
- For **every** question, give your **recommended answer** and the trade-off, so the user confirms rather than composes from scratch.
- If a question is answerable from the repo, **explore the codebase / `patterns.md` / `knowledge/` / `tech-stack.md` instead of asking**. Only ask product or trade-off questions a human must decide.
- Challenge the plan against the project's **domain language**: reuse the terminology already in `patterns.md` and `knowledge/` chapters, and flag/resolve term conflicts before finalizing.
- Record decisions that are **hard to reverse, surprising, and a real trade-off** into `knowledge/` (or `learnings.md`); skip low-value notes.
- Stop only when no open branch remains, a zero-context executor could
  implement from the artifact alone, the current revision has passed review,
  and the user selected Approve.
- The finished spec/worksheet doubles as a **handoff**: reference existing artifacts (PRD, patterns, knowledge, affected files) rather than duplicating them, and name the next skill to invoke. (If the harness exposes `grill-me` / `grill-with-docs` / `handoff` skills, you may invoke them to drive these steps; otherwise apply the discipline directly.)

## Guardrails

- Planning must be decision-complete; do not defer obvious research to implementation.
- A plan is not Ready while any task file lacks its worksheet sections; refinement is part of planning, not an optional follow-up.
- A task is not Ready without a declared verification strategy, exact
  verification outcome, exclusive file ownership, and one-invocation/one-commit
  scope.
- Ask only product or tradeoff questions that cannot be answered from the repo.
- Store plans under `.agents/bundles/specs/<flow_id>/`, not ad hoc docs paths.
- Do not modify production code during planning.

## Validation

- Confirm every requirement maps to an implementation task and test scenario.
- Confirm tasks are small enough for a low-context executor to complete without guessing — each task is one small, dispatchable chunk.
- Confirm every task file carries Objective, Context, Steps, Verification, and Acceptance Criteria sections.
- Run validation and a fresh code-reviewer round on the current plan revision.
  Three unresolved Critical/Important rounds hard-block Ready.

## References Index

- [PRD](../flow/references/prd.md)
- [Plan](../flow/references/plan.md)
- [Research](../flow/references/research.md)
- [Refine](../flow/references/refine.md)
- [Interaction](../flow/references/interaction.md)
- [Revise](../flow/references/revise.md)
- [Task](../flow/references/task.md)

## Example

User: "Plan skill trigger optimization."

Action: inspect current skills and validators, ask unresolved product tradeoffs, create a Flow spec with per-task bundle files, and refine until the implementation path is explicit.
