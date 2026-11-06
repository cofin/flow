# Flow Cleanup (`/flow:cleanup`)

Run groundskeeping across `.agents/` and branch-touched files to reconcile active specs, verify bundle integrity, synthesize and archive completed flows, and debloat touched code, tests, and documentation via [`../../debloat/SKILL.md`](../../debloat/SKILL.md).

## Phase 1: Reconcile Active Specs, Chapters, & Present-Tense Snapshots

1. Run the spec/chapter/task reconciliation pass from [`learn.md`](learn.md) across `.agents/bundles/specs/*/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md` so checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `current_chapter`, and `chapters/index.md` match worksheet frontmatter and Git commit history.
2. Refresh `## 6. Current State & Remaining Plan Snapshot` (`<= 25` lines, present tense, zero revision history) in active root and chapter `spec.md` files, strip any standalone `---` body horizontal rules or frontmatter on subdirectory `index.md` files, and remove any legacy `.agents/transactions/` directories or obsolete `.agents/skills/flow-memory-keeper/` copies.
3. Prune completed throwaway spikes in `.agents/scratch/` after confirming with the user.

## Phase 2: Verify Bundle, Chapter, Task & Link Integrity

1. Check that all relative Markdown links across `.agents/bundles/**/*.md` and `.agents/skills/index.md` resolve to existing files on disk.
2. Verify that every `knowledge/**`, `product/**`, and `spec.md` file has a bounded `<= 40`-line `<!-- truth: start -->` block, `status: draft | stable | deprecated`, and valid `sources:` + `[^id]:` citations.

## Phase 3: Synthesize & Archive Completed Flows

1. Identify all flows in `.agents/bundles/specs/*/` where `state: completed` (or where all chapters and tasks are `completed`/`closed`/`deferred`/`skipped`).
2. Offer via `structured-choice-v1` to archive them via [`archive.md`](archive.md). When `3+` completed flows are ready, run a subagent-sharded contraction pass that synthesizes their combined discoveries into `knowledge/**` and `.agents/skills/**` before removing the completed `specs/<flow_id>/` directories.

## Phase 4: Proactive Code, Test & Prose Debloat Sweep (`skills/debloat/SKILL.md`)

1. Inspect modified or branch-touched files (`git status --short` / `git diff`).
2. Apply [`../../debloat/SKILL.md`](../../debloat/SKILL.md):
   - Remove dead code, shallow pass-through wrappers failing the deletion test, unused imports, leftover compatibility shims, and inline `#` restatement comments in Python.
   - Consolidate standalone `test_*remediation*.py` / `test_*audit*.py` files into canonical module test files and replace tautological mock-echo assertions with public-seam behavior checks.
   - Strip AI prose slop, numbered buzzwords, and chronological revision notes from docs and `.agents/` chapters.
3. Run `make lint` (or the repository's fast lint/test gates from `knowledge/workflow.md`) to confirm zero regressions.
