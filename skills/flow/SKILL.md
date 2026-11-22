---
name: flow
description: "Use when a repository has .agents, or when routing Flow lifecycle tasks (setup, prd, spec, plan, revise, research, implement, status, dispatch, delegate, coordinate, learn, refresh, sync, docs, pr, review, simplify, finish, archive, cleanup, revert, validate, studio). Don't use for direct coding without specs or standalone plugin authoring (use multi-harness-plugins)."
---

# Flow Router

<!-- lifecycle-ownership: owner=flow; operations= -->

## Trigger

Use Flow when `.agents/` exists (in the workspace or linked primary Git worktree), spec bundles live under `.agents/bundles/specs/`, or the user requests a Flow action. Pair interactive `/flow:*` skills with the `flow` CLI (`bin/flow.mjs`, or install to `~/.local/bin/flow` via `flow install-cli`) for sync, multi-branch spec discovery, review notes, setup alignment, and catalog linting.

## Workflow

Route the requested operation directly to its owning lifecycle skill:

- `setup` &rarr; [`flow-setup`](../flow-setup/SKILL.md) ([`references/setup.md`](references/setup.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `prd` | `spec` (alias `plan`) | `revise` (alias `refine`) | `research` (alias `task`) &rarr; [`flow-planning`](../flow-planning/SKILL.md) ([`references/prd.md`](references/prd.md), [`references/spec.md`](references/spec.md), [`references/revise.md`](references/revise.md), [`references/research.md`](references/research.md))
- `implement` | `status` &rarr; [`flow-execution`](../flow-execution/SKILL.md) ([`references/implement.md`](references/implement.md), [`references/status.md`](references/status.md))
- `dispatch` | `delegate` | `coordinate` &rarr; [`flow-dispatch`](../flow-dispatch/SKILL.md) ([`references/orchestration.md`](references/orchestration.md))
- `learn` (aliases `refresh`, `sync`) &rarr; [`flow-learn`](../flow-learn/SKILL.md) ([`references/learn.md`](references/learn.md), [`multi-harness-plugins`](../multi-harness-plugins/SKILL.md))
- `docs` | `pr` &rarr; [`flow-docs`](../flow-docs/SKILL.md) ([`prose-and-documentation.md`](../flow-docs/references/prose-and-documentation.md), [`agent-context.md`](../flow-docs/references/agent-context.md), [`prs-commits-and-changelogs.md`](../flow-docs/references/prs-commits-and-changelogs.md))
- `review` | `simplify` | `finish` | `archive` | `cleanup` | `revert` | `validate` &rarr; [`flow-completion`](../flow-completion/SKILL.md) ([`references/review.md`](references/review.md), [`references/finish.md`](references/finish.md), [`references/archive.md`](references/archive.md), [`references/cleanup.md`](references/cleanup.md), [`references/revert.md`](references/revert.md), [`references/validate.md`](references/validate.md))

The router owns no disk mutations directly; it resolves the target lifecycle skill and reference procedure immediately.

## Example

```bash
flow status --branches
flow sync --dry-run --json
```

## Guardrails

- Load only the selected lifecycle skill and its reference procedure so unrelated prompt budgets stay free.
- Keep root specifications (`specs/<flow_id>/spec.md`), chapter catalogs (`chapters/index.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) synchronized in place in present tense ([`references/state.md`](references/state.md)). This prevents spec drift from live Git state; validate OKF writes with `/flow:validate`.
- Scale process and models proportionally ([`orchestration.md`](references/orchestration.md), [`skills-subagents-and-mcp-limits.md`](../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)). Call shipped workflows (`flow-scout`, `flow-spec-planning`, `flow-chapter-pipeline`, `flow-dual-review`) with `type_name="self"` on Google Antigravity so tools stay active.
- Keep planning and spec review on the `strong` model role and warn when `planning_quality: degraded`. Use briefs and let `flow sync` update checklists between steps. Never mark chapters or tasks `deferred` without `deferred_by: "user"`.
- In linked `git worktree` checkouts, reuse the symlinked `.venv` via `uv run --no-sync` to avoid redundant environment builds. Edit worktree `.agents/` when `ignore_policy` is `shared`, and edit the primary checkout's `.agents/` when `local-only`.
- Preserve Git history and tag immutability to protect release provenance. Never push or open remote PRs without explicit user instruction.

## Output

Identify the selected lifecycle skill and reference procedure and execute the requested stage.

## Validation

Confirm one lifecycle owner matches the requested operation and that the active harness loads the corresponding skill and reference document.

## References

- [Archive](references/archive.md) — Capture completed specs into knowledge before removing the spec directory.
- [Cleanup](references/cleanup.md) — Run groundskeeping and debloat across touched files.
- [Discipline](references/discipline.md) — Verify tests against the real module and enforce bug diagnosis rules.
- [Finish](references/finish.md) — Complete release checks, ADR filtering, and one-pass closeout.
- [Implement](references/implement.md) — Execute chapter task worksheets in parallel or sequential steps.
- [Interaction](references/interaction.md) — Format structured decision prompts and multi-choice options.
- [Learn](references/learn.md) — Sync specs with Git, catch up across harnesses, and update knowledge.
- [Orchestration](references/orchestration.md) — Scale workflows, model roles, and bounded parallel workers.
- [PRD](references/prd.md) — Author multi-chapter product requirement documents.
- [Research](references/research.md) — Run source-verified research spikes and promote findings.
- [Revert](references/revert.md) — Revert task, chapter, phase, or flow commits safely.
- [Review](references/review.md) — Plan and run isolated conformance, quality, and simplify reviews.
- [Revise](references/revise.md) — Update specs, chapters, or task worksheets when scope shifts.
- [Setup](references/setup.md) — Initialize or align `.agents/bundles/` and project skills.
- [Spec](references/spec.md) — Draft single-chapter or multi-chapter implementation specs.
- [State](references/state.md) — Reference the canonical YAML frontmatter and task state contract.
- [Status](references/status.md) — Report active specs, ready tasks, and cross-branch visibility.
- [Studio](references/studio.md) — Operate the Flow Studio sidecar panel and local catalog views.
- [Validate](references/validate.md) — Check OKF bundles, manifests, workflows, hooks, and links.
- [Vocabulary](references/vocabulary.md) — Enforce plain wording and avoid retired terms.
