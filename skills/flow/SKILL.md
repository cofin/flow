---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, OKF bundle task tracking, spec-first planning, TDD implementation, sync/status, review, finish, archive, or /flow:* help."
disable-model-invocation: true
---

# Flow Router

<!-- lifecycle-ownership: owner=flow; operations= -->

## Trigger

Use Flow when `.agents/` exists, spec bundles live under `.agents/bundles/specs/`, or the user requests a Flow action. Flow is a skill, not a CLI; never run `flow` as a shell command.

## Workflow

Route the requested operation directly to its owning lifecycle skill:

- `setup` &rarr; `flow-setup`
- `prd|plan|refine|revise|research|task` &rarr; `flow-planning`
- `implement` &rarr; `flow-execution`
- `sync|status|refresh` &rarr; `flow-sync-status`
- `review|finish|archive|revert|docs|cleanup|validate` &rarr; `flow-completion`

The router owns no operations and performs no disk mutations.

## Guardrails

- Load only the selected lifecycle skill; let it resolve needed context.
- Task files under `.agents/bundles/specs/<flow_id>/tasks/` are the sole authority for task state.
- Preserve Git history and tag immutability.

## Output

Identify the selected lifecycle skill and hand off the request immediately.

## Validation

Confirm exactly one lifecycle owner matches the requested operation.

## Example

For a request like "implement the active flow", route to `flow-execution` without applying claim mutations in the router.

## References

- [Archive](references/archive.md)
- [Cleanup](references/cleanup.md)
- [Discipline](references/discipline.md)
- [Docs](references/docs.md)
- [Finish](references/finish.md)
- [Implement](references/implement.md)
- [Interaction](references/interaction.md)
- [Plan](references/plan.md)
- [PRD](references/prd.md)
- [Refine](references/refine.md)
- [Refresh](references/refresh.md)
- [Research](references/research.md)
- [Revert](references/revert.md)
- [Review](references/review.md)
- [Revise](references/revise.md)
- [Setup](references/setup.md)
- [State](references/state.md)
- [Status](references/status.md)
- [Sync](references/sync.md)
- [Task](references/task.md)
- [Validate](references/validate.md)
