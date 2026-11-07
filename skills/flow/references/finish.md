# Flow Finish (`/flow:finish`)

Complete a flow on the current branch after verifying that every chapter (`chapters/<ch_id>/spec.md`) and task blueprint (`tasks/*.md`) is `completed` (or `deferred`/`skipped`), `[N/N files documented]` in `## 3. Documentation & OKF Knowledge Plan` is satisfied, full verification gates pass, and zero-context correctness, Markdown-sync, and quality reviews (`quality-review-v1`) carry valid `last_reviewed_commit` stamps.

## Phase 1: Chapter & Task Closure Audit and Scope-Cap Discipline

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), all `chapters/<ch_id>/spec.md` files, and all `tasks/*.md` files.
2. Confirm:
   - Every task worksheet across single-chapter `tasks/*.md` or nested `chapters/<ch_id>/tasks/*.md` is `state: completed` (or `closed` / `deferred` / `skipped`) and matches its owning `spec.md` checklist marker (`[x] [<sha>]` or `[-]`).
   - When `has_chapters: true`, every `chapters/<ch_id>/spec.md` is `state: completed` (`[-]` if deferred), carries a hex `last_reviewed_commit` covering all completed task commits in that chapter, and is marked `- [x] [<sha>]` in root `specs/<flow_id>/spec.md` and `completed` in `chapters/index.md`.
   - Every documentation and OKF knowledge target in `## 3. Documentation & OKF Knowledge Plan` is checked (`[N/N files documented]`), present-tense, and free of historical prose.
3. **Branch-Local Closure & Scope-Cap Discipline**:
   - Flow completion (`state: completed`) and archival (`/flow:archive`) are strictly branch-local transitions—never block completion waiting for a remote PR merge.
   - If the original problem is solved and remaining open chapters or tasks represent newly discovered follow-up scope, offer via `structured-choice-v1` to mark them `state: deferred` (`[-]` in `spec.md`), rewrite `## 6. Current State & Remaining Plan Snapshot` in present tense, close the current flow cleanly, and seed a follow-up spec via `/flow:spec <new_flow_id>`.

## Phase 2: Full Verification, Flow-Wide Review & ADR Gate

1. **Full Verification Gate**: Run the repository's canonical verification commands from `.agents/bundles/knowledge/workflow.md` (lint, typecheck, bundle/doc validator, and full unit/integration test suite) and confirm exit code `0`.
2. **Correctness, Markdown-Sync, & Quality Review Gate (`quality-review-v1`)**: If any chapter lacks a valid `last_reviewed_commit` or post-review commits landed since `last_reviewed_commit`, execute [`review.md`](review.md) (`@code-reviewer` + `@quality-reviewer`) across `base_commit..HEAD`, resolve any adopted findings, and stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>`.
3. **ADR Filter (`knowledge/decisions/adr-NNN-<slug>.md`)**:
   - Evaluate whether the flow introduced a decision that meets **all three** criteria:
     1. *Hard to reverse* (changes storage schema, public wire protocol, cross-module seam, or core dependency),
     2. *Surprising without context* (a future engineer or isolated agent might try to "simplify" or undo it), and
     3. *Genuine trade-off* (two viable alternatives existed with real pros and cons).
   - If all three hold, author `.agents/bundles/knowledge/decisions/adr-NNN-<slug>.md` in present tense with `Context`, `Decision`, `Alternatives Rejected`, `Consequences`, and OKF v0.2 `sources:` + `[^id]:` citations.

## Phase 3: Mark Spec Completed & Present Completion Options (`structured-choice-v1`)

1. Update `.agents/bundles/specs/<flow_id>/spec.md` frontmatter (`state: completed`, `current_chapter: null`, `current_task: null`, `last_verified_checkpoint: <HEAD_SHA>`, `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, `updated_at`), rewrite `## 6. Current State & Remaining Plan Snapshot` (`Remaining Plan: none`), prepend a `finish` entry to `.agents/bundles/log.md`, and commit metadata if updated.
2. Present the completion options via `structured-choice-v1` ([`interaction.md`](interaction.md)):
   1. `archive` — **Archive flow now on current branch (Recommended)**: Run [`archive.md`](archive.md) (`/flow:archive <flow_id>`) on this branch to synthesize durable learnings into `.agents/bundles/knowledge/**` and `.agents/skills/**` and remove the completed spec directory.
   2. `pr` — **Archive and open/update Pull Request**: Run `/flow:archive <flow_id>`, push the branch (with user confirmation), and create/update the PR following [`../../flow-docs/references/prs-commits-and-changelogs.md`](../../flow-docs/references/prs-commits-and-changelogs.md) (`<type>(<scope>): <concise summary>` title, `## Summary` and `## Key Changes` only, zero internal review/audit ceremony, and no `## Verification` block).
   3. `merge` — **Merge back to base branch locally and archive**: Run `/flow:archive <flow_id>`, merge the feature branch into the local base branch (`main`/`master`), re-run verification on the merged base branch, and clean up the feature branch/worktree if applicable.
   4. `discard` — **Discard work**: Require explicit typed `"discard"` confirmation from the user before resetting or removing branch/worktree state.
3. **Git Worktree Cleanup**: If the flow ran inside an isolated `git worktree`, offer to remove the worktree cleanly after branch merge or PR push.
