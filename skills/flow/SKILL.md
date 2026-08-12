---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, OKF bundle task tracking, spec-first planning, TDD implementation, sync/status, review, finish, archive, or /flow:* help."
---

# Flow Router

Flow coordinates Context-Driven Development in `.agents/` repositories. Keep this skill small: use it to identify the active lifecycle phase, enforce the bundle-first invariants, and load the matching lifecycle skill.

> **Flow is a skill, not a CLI.** There is no `flow` executable. Never run `flow`, `flow sync`, `flow prd`, etc. as shell commands. Invoke this skill (or the matching lifecycle skill), or use the `/flow:*` slash commands where the harness supports them.
>
> **Task state lives in files.** Specs and tasks are OKF v0.2 bundle files under `.agents/bundles/specs/<flow_id>/` (`spec.md` + `tasks/<short_id>.md`). Task files are the source of truth; the `spec.md` checklist is a synchronized view. There is no task database or CLI.

## Workflow

1. Check hook-provided Flow context first; otherwise detect `.agents/`, the git branch, and repo-native commands.
2. Route the request:
   - Setup, validation, install, context initialization: use `flow-setup`.
   - PRD, research, plan, refine, revise, task creation: use `flow-planning`.
   - Implement, claim ready tasks, TDD, commit, task close: use `flow-execution`.
   - Sync, status, refresh, cleanup, context drift: use `flow-sync-status`.
   - Review, finish, archive, revert, docs, phase completion: use `flow-completion`.
3. Record durable discoveries in the owning task file's `## Notes & Discoveries` section and task state in its `state:` frontmatter.
4. Prefer repo-native commands from `.agents/bundles/knowledge/workflow.md` or hook context for validation.

## Guardrails

- Never edit task markers (`[ ]`, `[~]`, `[x]`, `[!]`, `[-]`) in `spec.md` without the matching task-file `state:` change; reconcile via `/flow:sync` rules.
- Store Flow specs and planning artifacts under `.agents/bundles/specs/<flow_id>/`.
- Workflow state belongs in the `state:` frontmatter key; the OKF `status:` key is reserved for document lifecycle (draft, stable, deprecated).
- Make minimal targeted changes and record findings in the task file when work exceeds a quick fix.
- Do not commit, stage, or push automatically unless the user asks.

## Validation

- For planning: verify the plan is decision-complete before presenting it.
- For implementation: verify red-green-refactor evidence, full relevant tests, and task-file closure (`state: closed` + commit SHA) before claiming completion.
- For sync/status: read the bundle files first and report drift instead of guessing.
- For this repository: run `make validate` and `make codex-package-check` after skill or command changes.

## References Index

- [Setup](../flow-setup/SKILL.md)
- [Planning](../flow-planning/SKILL.md)
- [Execution](../flow-execution/SKILL.md)
- [Sync and Status](../flow-sync-status/SKILL.md)
- [Completion](../flow-completion/SKILL.md)
- [Discipline](references/discipline.md)

## Example

User: "Use Flow to implement the current spec."

Action: load `flow-execution`, claim a ready task by setting its file to `state: in_progress`, add investigation notes, follow TDD, close the task with evidence and the commit SHA, then reconcile the spec checklist.
