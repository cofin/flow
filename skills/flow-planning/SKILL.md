---
name: flow-planning
description: "Use when drafting PRDs, researching, planning, refining, revising, or creating .agents/bundles/specs/<flow_id>/spec.md worksheets for Flow."
disable-model-invocation: true
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

1. **Research & Frontier Analysis**: Close codebase facts autonomously using background `@researcher` subagents. Map design choices as an unblocked frontier with opinionated recommendations (`❓ Choice [ID] ... ➡️ Recommendation`).
2. **Multi-Interface Exploration**: Explore competing interface designs and evaluate structural boundaries using `architecture-critic` before spec lock.
3. **Draft Spec & Worksheets**: Write `spec.md` and complete worksheets in `tasks/<short_id>.md` specifying public interfaces, types, and testing seams.
4. **Adversarial Stress-Testing**: Apply the `devils-advocate` lens before presenting for approval to catch edge cases.
5. **Approval Gate**: Present `Approve|Revise|Refine`. Upon approval, hand off to `flow-execution`.

## Guardrails

- Planning modifies files exclusively under `.agents/bundles/specs/<flow_id>/`. Never edit application source code during planning.
- A plan is Ready only when a zero-context agent can implement every task correctly from the worksheet alone.
- Every task must be sized for exactly one subagent invocation and one atomic Git commit.

## Output

Return the finalized spec path, child tasks, review findings, and the next lifecycle command (`/flow:implement`).

## Validation

Confirm requirement-to-task traceability, complete worksheets, test command specifications, and user approval.

## Example

For a new subsystem, research codebase patterns, map design choices, draft `spec.md` with refined task worksheets, and present for user approval.
