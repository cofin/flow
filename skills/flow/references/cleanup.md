# Flow Cleanup Reference

Proactive maintenance, knowledge synthesis, transcript compaction, and code/prose debloat across `.agents/` and branch-touched files.

## Contents

- [1.0 The Cleanup Mandate](#10-the-cleanup-mandate)
- [2.0 Workflow](#20-workflow)
- [3.0 Critical Rules](#30-critical-rules)

---

## 1.0 THE CLEANUP MANDATE

The Groundskeeping & Polish routine ensures that:

- All active `spec.md` checklists, frontmatter revisions, and `Continuity Snapshot` sections match `tasks/*.md` truth.
- Completed specs (including specs whose tasks are all `closed`/`skipped` on an unmerged feature branch) undergo rigorous 5-dimension knowledge and pattern synthesis into `.agents/bundles/knowledge/` before contraction.
- Stale transaction transcripts under `<configured-root>/transactions/` and verbose historical task notes are compacted so agents see only crisp, current-state instructions.
- No orphaned task files or broken Markdown links remain in `.agents/bundles/`.
- Uncommitted or branch-touched code and documentation are swept for dead code, over-engineering, inline comment clutter, and AI prose slop via `skills/debloat/SKILL.md`.

---

## 2.0 WORKFLOW

### Phase 1: Reconcile Specs & Prune Transcript Clutter

1. **Reconcile Active Specs**: Execute the `/flow:sync` (`reconcile`) algorithm across all active spec directories so every `spec.md` checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `current_task`, `state_revision`, and `Continuity Snapshot` matches `tasks/*.md`.
2. **Detect Unclosed Completed Specs**: If an `active` spec has every task in `state: closed` or `skipped` (even on a local branch whose PR is not yet merged to `main`), transition it through `/flow:finish` (`complete`) or offer to split any lingering out-of-scope tasks into a new spec so the completed work is not stuck open.
3. **Prune Transaction Transcripts**: Scan `<configured-root>/transactions/*/`. Keep any nonterminal journal (`prepared`, `task_writes_started`, `recovery_required`, `rollback_in_progress`) and the single newest terminal journal per active flow; remove older superseded/committed/rolled-back transaction directories so hundreds of historical transcripts do not accumulate.
4. **Compact Spec & Task Bodies**: Ensure active `spec.md` and `tasks/*.md` contain present-tense executable instructions rather than multi-page transcripts of superseded revisions, and cap `Continuity Snapshot` at the 5 newest discoveries.

### Phase 2: Bundle & Knowledge Integrity Check

Perform validation checks using file-manipulation tools:

1. **Verify Orphaned Task Files**: Scan `.agents/bundles/specs/*/tasks/*.md` and ensure every task file has a corresponding checklist item in its parent `spec.md`.
2. **Verify File and Test Paths**: For each `closed` task in an active spec, verify that all paths in its `files` and `tests` arrays exist on disk.
3. **Verify Markdown Links & Knowledge Index**: Verify that all relative links in `spec.md`, `.agents/bundles/index.md`, and `.agents/bundles/knowledge/**/*.md` resolve to existing files, and that every chapter under `knowledge/` is indexed in `knowledge/index.md`.

Fix any broken links, missing frontmatter fields, or unindexed knowledge chapters before proceeding.

### Phase 3: Rigorous Knowledge Synthesis & Archive of Completed Flows

1. Scan `.agents/bundles/specs/*/spec.md` for specs with `state: completed` (eligibility is branch-local and **never** blocked on merging to `main`).
2. **Mandatory Pre-Deletion Knowledge & Pattern Synthesis**:
   - Never delete a spec directory before extracting its durable knowledge, and never settle for appending a few superficial bullets to a single pattern file.
   - For each completed flow, extract findings from `spec.md`, all `tasks/*.md` (`## Notes & Discoveries`), `learnings.md`, and promoted `research/` across all 5 dimensions:
     1. **Domain Model & Invariants** (`knowledge/domains/<domain>.md`)
     2. **Architecture & Deep Module Seams** (`knowledge/architecture/<area>.md`)
     3. **Idiomatic Code Patterns & Anti-Patterns** (`knowledge/patterns/<topic>.md`)
     4. **Build, Verification & Testing Recipes** (`knowledge/testing/<topic>.md` or `knowledge/workflow.md`)
     5. **Hard-Won Gotchas & Edge Cases** (`knowledge/gotchas/<topic>.md` or `knowledge/patterns/<topic>.md`)
   - Reorganize flat or bloated knowledge chapters (`> 200` lines or multi-topic) into nested subdirectories and update `knowledge/index.md`.
3. **Single vs. Batch Contraction**:
   - **1–2 completed flows**: Run `/flow:archive <flow_id>` to write the synthesized knowledge chapters first, append `.agents/bundles/log.md` second, and delete the spec directory last.
   - **3+ completed flows (archive backlog)**: Consolidate learnings across the whole set first, rewrite each affected `knowledge/**` chapter once in cohesive present-tense prose, append `log.md` entries newest-first, and contract all completed spec directories in a single journaled archive pass.

### Phase 4: Proactive Code & Prose Debloat Sweep

When `/flow:cleanup` is invoked after implementation or with a file/branch scope:

1. Load `skills/debloat/SKILL.md` and inspect modified or branch-touched files (`git status --porcelain` / `git diff`).
2. Strip dead code, redundant wrappers, single-use trivial helpers, duplicate/low-signal tests, forbidden inline comments, and AI prose slop (puffery, negative parallelisms, formulaic transitions, bold-bullet spam) in touched docs and docstrings.
3. Run fast verification (`make lint` and affected unit tests) to confirm zero regressions.

---

## 3.0 CRITICAL RULES

1. **KNOWLEDGE BEFORE CONTRACTION** — Never delete a completed spec before synthesizing its domain invariants, architecture seams, patterns, testing recipes, and gotchas into `knowledge/**` and updating `knowledge/index.md` and `log.md`.
2. **BRANCH-LOCAL ELIGIBILITY** — Never refuse to complete or archive a spec just because its branch or PR is not yet merged into `main`.
3. **NO ORPHANED TASKS OR STALE TRANSCRIPTS** — Prune orphaned task files and obsolete terminal transaction journals so the workspace stays lean.
4. **DO NOT DESTRUCTIVELY CLEAN ACTIVE WORK** — Never delete open/in-progress specs or uncommitted user code changes.
