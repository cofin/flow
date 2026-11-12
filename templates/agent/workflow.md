---
type: Guide
title: Project Workflow
description: Canonical build, fast lint, targeted unit test, full release gate, and Flow chapter-batch execution rules.
status: stable
tags: [workflow, commands, verification]
---

# Project Workflow

<!-- truth: start -->
- Specifications (`specs/<flow_id>/spec.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) are the sole authority for Flow state and commits.
- Batch edits across the active chapter (`1..4` tasks) in a single warm pass so shared files are edited once, then validate once with the **Fast Chapter Gate** (`< 60s`: static lint/typecheck + targeted unit test file).
- Minimize **Full Release Gate** runs (`> 60s` or container-backed full test suites): run full suites once at `/flow:finish` (or CI), never between tasks or intermediate chapters.
- Test through confirmed public seams in existing canonical module test files; never mock the System Under Test, write tautological assertions, or create standalone `test_*remediation*.py` / `test_*audit*.py` files.
- In linked `git worktree` checkouts, reuse the symlinked `.venv` via `uv run --no-sync` (do not run `make install`); edit worktree `.agents/` when `ignore_policy` is `shared`, and edit the main checkout's `.agents/` when `ignore_policy` is `local-only`.
- Never mark chapters or tasks `deferred`/`skipped` without `deferred_by: user`, never create or mutate Git tags, and never push or open PRs without explicit user instruction.
<!-- truth: end -->

## Canonical Verification Tiers

Replace the placeholders below during `/flow:setup` or `/flow:learn` with verified host commands:

```bash
# bootstrap (primary checkout only; symlinked automatically in worktrees): make install | uv sync
# fast chapter gate (< 60s — run once per chapter batch): make lint && uv run --no-sync pytest tests/unit/test_module.py -q
# scoped module gate (cross-module seam changes only): uv run --no-sync pytest tests/unit/pkg/ -q
# full release gate (run once at /flow:finish or CI, never per-step): make check
```

## Direct Markdown Continuity & Chapter-Batch Loop

1. Resolve `.agents/setup-state.json` (or linked main-worktree `.agents/` when `local-only`), read `index.md`, and load only the active chapter's `spec.md` and `tasks/*.md`.
2. Run preflight (`chapter_dependencies_closed_and_reviewed`, `chapter_planning_status_complete`, `dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`).
3. Apply the chapter's `1..4` task slices in one cohesive batch, run the **Fast Chapter Gate** (`exit 0`), commit owned code/test paths first to capture `<CODE_SHA>`, and record `<CODE_SHA>` + present-tense Markdown/OKF updates in the pre-review sync commit before Zero-Context Chapter Review.
4. Run `/flow:learn` at any time to reconcile drift, harvest discoveries, and synchronize `.agents/bundles/knowledge/**`, `.agents/skills/`, and `.agents/agents/`.
