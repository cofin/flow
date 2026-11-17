# Flow Cleanup (`/flow:cleanup`)

Run groundskeeping across `.agents/` and branch-touched files to sync active specs, verify bundle integrity, capture learnings, archive completed flows, and debloat code, tests, and docs via [`../../debloat/SKILL.md`](../../debloat/SKILL.md).

## Phase 1: Sync Active Specs & Current State

1. Run the spec, chapter, and task sync pass from [`learn.md`](learn.md) across `.agents/bundles/specs/*/spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`.
2. Ensure checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `current_chapter`, and `chapters/index.md` match worksheet frontmatter and Git commit history.
3. Refresh `## 6. Current State & Remaining Plan Snapshot` (`<= 25` lines, present tense, no revision history) in active root and chapter `spec.md` files.
4. Strip standalone `---` body rules or frontmatter on subdirectory `index.md` files, and remove legacy `.agents/transactions/` directories.
5. Prune completed throwaway spikes in `.agents/scratch/` after confirming with the user.

## Phase 2: Verify Bundle & Link Integrity

1. Check that all relative Markdown links across `.agents/bundles/**/*.md` and `.agents/skills/index.md` resolve to existing files on disk.
2. Verify that every `knowledge/**`, `product/**`, and `spec.md` file has a `<= 40`-line `<!-- truth: start -->` truth block, `status: draft | stable | deprecated`, and valid `sources:` plus `[^id]:` citations.

## Phase 3: Capture Learnings & Archive Flows

1. Identify all flows in `.agents/bundles/specs/*/` where `state: completed` (or where all chapters and tasks are `completed`/`closed`/`deferred`/`skipped`).
2. Offer an interactive prompt to archive them via [`archive.md`](archive.md).
3. When `3+` completed flows are ready, run parallel domain subagents to capture their combined discoveries into `knowledge/**` and `.agents/skills/**` before removing the completed `specs/<flow_id>/` directories.

## Phase 4: Code, Test & Prose Debloat Sweep

1. Inspect modified or branch-touched files (`git status --short` / `git diff`).
2. Apply [`../../debloat/SKILL.md`](../../debloat/SKILL.md):
   - Remove dead code, shallow pass-through wrappers failing the deletion test, unused imports, leftover compatibility shims, and inline `#` restatement comments in Python.
   - Consolidate standalone `test_*remediation*.py` or `test_*audit*.py` files into canonical module test files and replace mock-only assertions with public interface behavior checks.
   - Strip filler prose, numbered buzzwords, and chronological revision notes from docs and `.agents/` chapters.
3. Run `make lint` (or the repository's fast lint and test checks from `knowledge/workflow.md`) to confirm zero regressions.
