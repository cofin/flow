---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, Beads-backed task memory, spec-first planning, TDD implementation, sync/status, review, finish, archive, or /flow:* help."
---

# Flow Router

Flow coordinates Context-Driven Development in `.agents/` repositories. Keep this skill small: use it to identify the active lifecycle phase, enforce the Beads-first invariants, and load the matching lifecycle skill.

## Workflow

1. Check hook-provided Flow context first; otherwise detect `.agents/`, Beads (`bd`), git branch, and repo-native commands.
2. Route the request:
   - Setup, validation, install, context initialization: use `flow-setup`.
   - PRD, research, plan, refine, revise, task creation: use `flow-planning`.
   - Implement, claim ready tasks, TDD, commit, task close: use `flow-execution`.
   - Sync, status, refresh, cleanup, context drift: use `flow-sync-status`.
   - Review, finish, archive, revert, docs, phase completion: use `flow-completion`.
3. Record durable discoveries and task state in Beads. Markdown files are synchronized views.
4. Prefer repo-native commands from `.agents/workflow.md` or hook context for validation.

## Guardrails

- Never edit task markers (`[ ]`, `[~]`, `[x]`, `[!]`, `[-]`) manually in `spec.md`.
- Do not run backend export, auto-stage, Dolt push, or git operations through Beads unless `.agents/beads.json` allows it or the user asks.
- Store Flow specs and planning artifacts under `.agents/specs/<flow_id>/`.
- Make minimal targeted changes and record findings with `bd note <id> "..."` when work exceeds a quick fix.

## Validation

- For planning: verify the plan is decision-complete before presenting it.
- For implementation: verify red-green-refactor evidence, full relevant tests, and Beads task closure before claiming completion.
- For sync/status: read backend state first and report drift instead of guessing.
- For this repository: run `make validate-skills` and `make validate-codex-manifest` after skill or command changes.

## References Index

- [Setup](../flow-setup/SKILL.md)
- [Planning](../flow-planning/SKILL.md)
- [Execution](../flow-execution/SKILL.md)
- [Sync and Status](../flow-sync-status/SKILL.md)
- [Completion](../flow-completion/SKILL.md)
- [Discipline](references/discipline.md)

## Example

User: "Use Flow to implement the current spec."

Action: load `flow-execution`, claim a ready Beads task, add investigation notes, follow TDD, close the task with evidence, then sync according to policy.
