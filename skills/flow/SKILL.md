---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, OKF v0.2 bundle task tracking, spec-driven planning, TDD implementation, status, learn/resynthesize, review, finish, archive, or /flow:* help."
---

# Flow Router

<!-- lifecycle-ownership: owner=flow; operations= -->

## Trigger

Use Flow when `.agents/` exists, spec bundles live under `.agents/bundles/specs/`, or the user requests a Flow action. Flow is a skill and subagent workflow, not a shell executable; never run `flow` as a shell command.

## Workflow

Route the requested operation directly to its owning lifecycle skill:

- `setup` &rarr; [`flow-setup`](../flow-setup/SKILL.md) ([`references/setup.md`](references/setup.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `prd` | `plan` | `revise` (alias `refine`) | `research` (alias `task`) &rarr; [`flow-planning`](../flow-planning/SKILL.md) ([`references/prd.md`](references/prd.md), [`references/plan.md`](references/plan.md), [`references/revise.md`](references/revise.md), [`references/research.md`](references/research.md))
- `implement` | `status` &rarr; [`flow-execution`](../flow-execution/SKILL.md) ([`references/implement.md`](references/implement.md), [`references/status.md`](references/status.md))
- `learn` (aliases `resynthesize`, `refresh`, `sync`) &rarr; [`flow-learn`](../flow-learn/SKILL.md) ([`references/learn.md`](references/learn.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `docs` | `pr` &rarr; [`flow-docs`](../flow-docs/SKILL.md) ([`prose-and-documentation.md`](../flow-docs/references/prose-and-documentation.md), [`agent-context.md`](../flow-docs/references/agent-context.md), [`prs-commits-and-changelogs.md`](../flow-docs/references/prs-commits-and-changelogs.md))
- `review` | `finish` | `archive` | `cleanup` | `revert` | `validate` &rarr; [`flow-completion`](../flow-completion/SKILL.md) ([`references/review.md`](references/review.md), [`references/finish.md`](references/finish.md), [`references/archive.md`](references/archive.md), [`references/cleanup.md`](references/cleanup.md), [`references/revert.md`](references/revert.md), [`references/validate.md`](references/validate.md))

The router owns no disk mutations directly; it resolves the target lifecycle skill and reference procedure immediately.

## Guardrails

- Load only the selected lifecycle skill and its reference procedure.
- Root specifications (`specs/<flow_id>/spec.md`), chapter catalogs (`chapters/index.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are kept synchronized in place in present tense—stating current verified state, remaining chapters, and the full plan without historical sediment ([`references/state.md`](references/state.md)).
- Keep the coordinator thin (`< 25k` exploration tokens) by scaling horizontally across isolated subagents: on Google Antigravity, use `run_workflow` (`phase()`, `parallel()`, `pipeline()`, `agent(..., type_name="self", schema=..., model="inherit")`) or `invoke_subagent(TypeName="self", Model="inherit", ...)` bound to `agents/<role>.md` contracts for sharded scouts, upfront parallel chapter authoring (`ch01..chNN`, `1–4` tasks/chapter, zero upper cap), per-chapter zero-context reviews, single-chapter task execution, and OKF/doc synthesis.
- Preserve Git history and tag immutability. Never push or open remote PRs without explicit user instruction.

## Output

Identify the selected lifecycle skill and reference procedure and execute the requested stage.

## Validation

Confirm one lifecycle owner matches the requested operation and that the active harness loads the corresponding skill and reference document.

## References

- [Archive](references/archive.md)
- [Cleanup](references/cleanup.md)
- [Discipline](references/discipline.md)
- [Finish](references/finish.md)
- [Implement](references/implement.md)
- [Interaction](references/interaction.md)
- [Learn](references/learn.md)
- [Plan](references/plan.md)
- [PRD](references/prd.md)
- [Research](references/research.md)
- [Revert](references/revert.md)
- [Review](references/review.md)
- [Revise](references/revise.md)
- [Setup](references/setup.md)
- [State](references/state.md)
- [Status](references/status.md)
- [Validate](references/validate.md)
