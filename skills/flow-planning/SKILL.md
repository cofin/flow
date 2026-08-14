---
name: flow-planning
description: "Use when drafting PRDs, researching, planning, refining, revising, or creating .agents/bundles/specs/<flow_id>/spec.md worksheets for Flow."
---

# Flow Planning

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,plan,refine,revise,research,task -->

## Trigger

Use for `prd|plan|refine|revise|research|task`.

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

1. Close repository-answerable research; ask only unresolved product or
   trade-off decisions through `structured-choice-v1`, one at a time.
2. Draft traceable PRDs or executable specs with complete authoritative task
   worksheets and exclusive one-invocation/one-commit ownership.
3. Reject deferred facts, unresolved decisions, stubs, vague verification,
   missing strategies, ownership overlap, coverage gaps, and oversized tasks.
4. Refine one gap at a time. A plan-bearing change applies one `revise`
   transaction, increments plan identity, updates every task, and revalidates.
5. Request fresh review. Three rounds with unresolved Critical/Important
   findings block Ready. Present `Approve|Revise|Refine` only after quality
   passes; approval advances, revision/refinement loops and revalidates.

## Guardrails

- Store plans only under `.agents/bundles/specs/<flow_id>/`.
- Never modify production code or defer obvious research to implementation.
- Do not label a plan Ready until a zero-context executor could run it exactly.

## Output

Return the current plan identity, review result, unresolved decisions, and exact
next lifecycle action. Approved work names `flow-execution` as the handoff.

## Validation

Confirm requirement-to-task/test traceability, worksheet completeness,
verification strategy, exclusive ownership, bounded task size, fresh review,
and explicit approval on the current revision.

## Conditional References

- [PRD](../flow/references/prd.md)
- [Plan](../flow/references/plan.md)
- [Research](../flow/references/research.md)
- [Refine](../flow/references/refine.md)
- [Revise](../flow/references/revise.md)
- [Task](../flow/references/task.md)
- [Interaction](../flow/references/interaction.md)
- [State](../flow/references/state.md)

## Example

For a feature plan, close factual gaps, write complete worksheets, refine until
the gap scan and review pass, then ask for approval on that exact revision.
