---
type: Guide
title: Project Workflow
description: Canonical build, lint, typecheck, test, and Flow execution rules for this repository.
status: stable
tags: [workflow, commands, verification]
---

# Project Workflow

<!-- truth: start -->
- Task worksheets under `.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md` and `spec.md` checklists are the sole authority for task state and commits.
- Run the repository's verified setup, lint, typecheck, focused test, and aggregate verification commands below.
- Every task worksheet declares one `verification_strategy` (`behavior_tdd`, `regression_tdd`, `characterization`, `static_validation`, `documentation_validation`, `integration_acceptance`).
- Test through confirmed public seams in existing canonical module test files; never mock the System Under Test, write tautological assertions, or create standalone `test_*remediation*.py` / `test_*audit*.py` files.
- Project-local domain and review skills live under `.agents/skills/` and paired subagents under `.agents/agents/`.
- Never create or mutate Git tags, and never push or open PRs without explicit user instruction.
<!-- truth: end -->

## Canonical Commands

Replace the placeholders below during `/flow:setup` or `/flow:learn` with verified host commands:

```bash
# setup: make install | uv sync | npm install
# lint & typecheck: make lint
# focused test: uv run pytest tests/unit/test_module.py -q
# full verification gate: make check
```

## Direct Markdown Continuity & Execution Loop

1. Resolve `.agents/setup-state.json` (default `.agents/bundles/`), read `index.md`, and inspect active `specs/<flow_id>/spec.md` and `tasks/<id>-<slug>.md`.
2. Run the 5-check preflight (`dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`) before claiming the ready `pending`/`open` task.
3. Execute one vertical-slice worksheet per isolated `@executor` subagent turn (`model: inherit`), verify exit code `0`, stage only task-owned paths, create one atomic signed commit, and update task frontmatter (`state: completed`, `commit: <sha>`) and `spec.md` (`- [x] [<sha>] ...`).
4. Run `/flow:learn` at any time to reconcile cross-machine/cross-harness drift, harvest mid-flow discoveries, resynthesize `.agents/bundles/knowledge/**`, and synchronize `.agents/skills/` and `.agents/agents/`.
