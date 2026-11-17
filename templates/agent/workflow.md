---
type: Guide
title: Project Workflow
description: Verified build, fast lint, targeted unit test, full release check, and Flow chapter-batch execution rules.
status: stable
tags: [workflow, commands, verification]
---

# Project Workflow

<!-- truth: start -->
- Specifications (`specs/<flow_id>/spec.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are the sole authority for Flow state and commits.
- Group edits across the active chapter (`<= 4` tasks per worker via `tasks_per_worker`) in one pass so shared files are edited once.
- Validate once per group with the **Fast Chapter Check** (`< 60s`: static lint/typecheck plus targeted unit test files).
- Reserve **Full Release Check** runs (`> 60s` or container-backed full test suites) for `/flow:finish` or CI, never between tasks or intermediate chapters.
- Test through confirmed public interfaces in canonical module test files; never mock real code, write mock-only tests, or create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- In linked `git worktree` checkouts, reuse the symlinked `.venv` via `uv run --no-sync` (do not run `make install`).
- Edit worktree `.agents/` when `ignore_policy` is `shared`, and edit the main checkout's `.agents/` when `ignore_policy` is `local-only`.
- Never mark chapters or tasks `deferred` or `skipped` without `deferred_by: user`, never mutate Git tags, and never push or open PRs without explicit user instruction.
<!-- truth: end -->

## Verification Checks

Replace the placeholders below during `/flow:setup` or `/flow:learn` with verified host commands:

```bash
# bootstrap (primary checkout only; symlinked automatically in worktrees): make install | uv sync
# fast chapter check (< 60s — run once per chapter group): make lint && uv run --no-sync pytest tests/unit/test_module.py -q
# scoped module check (cross-module interface changes only): uv run --no-sync pytest tests/unit/pkg/ -q
# full release check (run once at /flow:finish or CI, never per-step): make check
```

## Direct Markdown Continuity and Chapter Loop

1. Resolve `.agents/setup-state.json` (or linked main-worktree `.agents/` when `local-only`), read `index.md`, and load only the active chapter's `spec.md` and `tasks/*.md`.
2. Run preflight (`chapter_dependencies_closed_and_reviewed`, `chapter_planning_status_complete`, `dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`).
3. Implement the chapter's tasks in grouped passes (`tasks_per_worker`) or parallel steps on separate files (`parallel_tasks`, `workers`), then run the **Fast Chapter Check** (`exit 0`).
4. Commit owned code and test paths first to capture `<CODE_SHA>`, then record `<CODE_SHA>` and present-tense Markdown and OKF updates in the sync commit before independent chapter review.
5. Run `/flow:learn` at any time to sync drift, capture discoveries, and update `.agents/bundles/knowledge/**`, `.agents/skills/`, and `.agents/agents/`.
