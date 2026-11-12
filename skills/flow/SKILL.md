---
name: flow
description: "Use when a repository has .agents, when the user asks for Flow lifecycle routing, OKF v0.2 bundle task tracking, spec-driven planning, TDD implementation, status, learn/resynthesize, review, finish, archive, or /flow:* help."
---

# Flow Router

<!-- lifecycle-ownership: owner=flow; operations= -->

## Trigger

Use Flow when `.agents/` exists (in the workspace or linked primary Git worktree), spec bundles live under `.agents/bundles/specs/`, or the user requests a Flow action. Flow is a skill and subagent workflow, not a shell executable; never run `flow` as a shell command.

## Workflow

Route the requested operation directly to its owning lifecycle skill:

- `setup` &rarr; [`flow-setup`](../flow-setup/SKILL.md) ([`references/setup.md`](references/setup.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `prd` | `spec` (alias `plan`) | `revise` (alias `refine`) | `research` (alias `task`) &rarr; [`flow-planning`](../flow-planning/SKILL.md) ([`references/prd.md`](references/prd.md), [`references/spec.md`](references/spec.md), [`references/revise.md`](references/revise.md), [`references/research.md`](references/research.md))
- `implement` | `status` &rarr; [`flow-execution`](../flow-execution/SKILL.md) ([`references/implement.md`](references/implement.md), [`references/status.md`](references/status.md))
- `learn` (aliases `resynthesize`, `refresh`, `sync`) &rarr; [`flow-learn`](../flow-learn/SKILL.md) ([`references/learn.md`](references/learn.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `docs` | `pr` &rarr; [`flow-docs`](../flow-docs/SKILL.md) ([`prose-and-documentation.md`](../flow-docs/references/prose-and-documentation.md), [`agent-context.md`](../flow-docs/references/agent-context.md), [`prs-commits-and-changelogs.md`](../flow-docs/references/prs-commits-and-changelogs.md))
- `review` | `finish` | `archive` | `cleanup` | `revert` | `validate` &rarr; [`flow-completion`](../flow-completion/SKILL.md) ([`references/review.md`](references/review.md), [`references/finish.md`](references/finish.md), [`references/archive.md`](references/archive.md), [`references/cleanup.md`](references/cleanup.md), [`references/revert.md`](references/revert.md), [`references/validate.md`](references/validate.md))

The router owns no disk mutations directly; it resolves the target lifecycle skill and reference procedure immediately.

## Guardrails

- Load only the selected lifecycle skill and its reference procedure.
- Keep root specifications (`specs/<flow_id>/spec.md`), chapter catalogs (`chapters/index.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) synchronized in place in present tense ([`references/state.md`](references/state.md)), validating OKF writes with `/flow:validate`.
- Scale process and models proportionally ([`skills-subagents-and-mcp-limits.md`](../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)): call shipped packaged workflows (`flow-scout`, `flow-spec-planning`, `flow-chapter-pipeline`, `flow-dual-review`) with `type_name="self"` on Google Antigravity, restrict `haiku`/`flash_lite` strictly to narrow (`<= 3`-file) fetches, surface an explicit warning whenever `planning_quality: degraded` indicates a spec was not planned on the primary frontier thinking model, batch edits across each active chapter with a single fast (`< 60s`) lint + targeted unit gate, and never mark chapters or tasks `deferred` without `deferred_by: "user"`.
- In linked `git worktree` checkouts, reuse the symlinked `.venv` via `uv run --no-sync` (never run `make install` unless dependencies changed); edit worktree `.agents/` when `ignore_policy` is `shared`, and edit the primary checkout's `.agents/` when `local-only`.
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
- [PRD](references/prd.md)
- [Research](references/research.md)
- [Revert](references/revert.md)
- [Review](references/review.md)
- [Revise](references/revise.md)
- [Setup](references/setup.md)
- [Spec](references/spec.md)
- [State](references/state.md)
- [Status](references/status.md)
- [Studio](references/studio.md)
- [Validate](references/validate.md)
