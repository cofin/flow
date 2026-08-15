---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, OKF bundle task tracking, spec-first planning, TDD implementation, sync/status, review, finish, archive, or /flow:* help."
---

# Flow Router

<!-- lifecycle-ownership: owner=flow; operations= -->

## Trigger

Use Flow when `.agents/` exists, task bundles live under
`.agents/bundles/specs/`, or the request names a Flow lifecycle action. Flow is
a skill, not a CLI; never run `flow` as a shell command.

## Workflow

Route exactly one operation family to its owning lifecycle skill:

- `setup` -> `flow-setup`
- `prd|plan|refine|revise|research|task` -> `flow-planning`
- `implement` -> `flow-execution`
- `sync|status|refresh` -> `flow-sync-status`
- `review|finish|archive|revert|docs|cleanup|validate` -> `flow-completion`

The router owns no operation and performs no lifecycle procedure.

## Guardrails

- Load only the selected lifecycle skill; let it link the required contracts.
- Treat hook or conversation context as routing hints, never task-state authority.
- Preserve unrelated work and never push or mutate Git tags automatically.

## Output

Name the selected lifecycle skill and hand off the unchanged request.

## Validation

Confirm exactly one lifecycle owner matches the requested operation.

## Conditional References

- [Setup](../flow-setup/SKILL.md)
- [Planning](../flow-planning/SKILL.md)
- [Execution](../flow-execution/SKILL.md)
- [Sync and status](../flow-sync-status/SKILL.md)
- [Completion](../flow-completion/SKILL.md)

## Example

For “implement the current spec,” route to `flow-execution` without applying a
claim, editing a task, or loading completion procedures in the router.
