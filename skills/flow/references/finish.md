# Flow Finish (`/flow:finish`)

Complete a flow on the current branch after verifying that every chapter (`chapters/<ch_id>/spec.md`) and task worksheet (`tasks/*.md`) is `completed` (or `deferred`/`skipped`).
Confirm `[N/N files documented]` in `## 3. Documentation & OKF Knowledge Plan`, full checks pass, and independent correctness, Markdown-sync, and quality reviews carry valid `last_reviewed_commit` stamps.

## Phase 1: Completion, OKF & Closure Audit

1. Resolve the effective `.agents/` bundle root (handling linked `git worktree` `shared` vs. `local-only` primary-checkout routing) and run `/flow:validate` on `<flow_id>` (`--require-completed`) before mutating root `spec.md`.
2. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), all `chapters/<ch_id>/spec.md` files, and all `tasks/*.md` files, and confirm:
   - **Zero Skipped Chapters or Tasks**: Zero chapters or task worksheets remain `planned`, `active`, `pending`, `open`, `in_progress`, or `blocked`, and every `chapters/<ch_id>/` has `>= 1` task worksheet.
   - **Authorized Deferrals Only**: Any chapter or task in `state: deferred` (`[-]` in `spec.md`) carries `deferred_by: "user"` and a non-empty `deferred_reason`. Unapproved agent deferrals block completion.
   - **Git Commit & File-Ownership Proof**: Every `completed` task worksheet carries a valid hex `commit` SHA whose `git diff-tree` modified at least one path in `files:` or `tests:`, matching its `spec.md` marker (`[x] [<sha>]`).
   - **Chapter Review Stamps**: When `has_chapters: true`, every completed `chapters/<ch_id>/spec.md` carries a hex `last_reviewed_commit` covering all completed task commits in that chapter (`git merge-base --is-ancestor`), marked `- [x] [<sha>]` in root `spec.md` and `completed` in `chapters/index.md`.
   - **Documentation & Degraded-Planning Disclosure**: Every target in `## 3. Documentation & OKF Knowledge Plan` is checked (`[N/N files documented]`), present-tense, and free of historical prose. If `planning_quality: degraded` is set, display `planning_degraded_reason` before closing.
3. **Branch-Local Closure & Scope Discipline**:
   - Flow completion (`state: completed`) and archival (`/flow:archive`) are branch-local transitions—never block completion waiting for a remote PR merge.
   - If the original problem is solved and open chapters or tasks represent new follow-up scope, offer an interactive prompt to mark them `state: deferred` with `deferred_by: "user"` and `deferred_reason`.
   - Rewrite `## 6. Current State & Remaining Plan Snapshot` in present tense, close the current flow, and seed a follow-up spec via `/flow:spec <new_flow_id>`.

## Phase 2: Full Check, Review & ADR Check

1. **Full Release Check (`> 60s` Suite Run Once Here)**: Run the repository's full verification commands from `.agents/bundles/knowledge/workflow.md`—including any `> 60s` full test suite skipped during fast chapter checks—plus lint, typecheck, and `/flow:validate` (`exit 0`).
2. **Correctness, Markdown-Sync & Quality Review**: If any chapter lacks a valid `last_reviewed_commit` or new commits landed since `last_reviewed_commit`, run [`review.md`](review.md) (`@code-reviewer` + `@quality-reviewer`) across `base_commit..HEAD`, resolve adopted findings, and stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>`.
3. **ADR Filter (`knowledge/decisions/adr-NNN-<slug>.md`)**:
   - Evaluate whether the flow introduced a decision that meets **all three** criteria:
     1. *Hard to reverse* (changes storage schema, public wire protocol, cross-module interface, or core dependency),
     2. *Surprising without context* (a future engineer or isolated agent might try to "simplify" or undo it), and
     3. *Genuine trade-off* (two viable alternatives existed with real pros and cons).
   - If all three hold, author `.agents/bundles/knowledge/decisions/adr-NNN-<slug>.md` in present tense with `Context`, `Decision`, `Alternatives Rejected`, `Consequences`, and OKF v0.2 `sources:` + `[^id]:` citations.

## Phase 3: Mark Completed & Present Options

1. Update `.agents/bundles/specs/<flow_id>/spec.md` frontmatter (`state: completed`, `current_chapter: null`, `current_task: null`, `last_verified_checkpoint: <HEAD_SHA>`, `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, `updated_at`), rewrite `## 6. Current State & Remaining Plan Snapshot` (`Remaining Plan: none`), prepend a `finish` entry to `.agents/bundles/log.md`, and commit metadata if updated.
2. Present completion options via [`interaction.md`](interaction.md):
   1. `archive` — **Archive flow now on current branch (Recommended)**: Run [`archive.md`](archive.md) (`/flow:archive <flow_id>`) on this branch to capture durable learnings into `.agents/bundles/knowledge/**` and `.agents/skills/**` and remove the completed spec directory.
   2. `pr` — **Archive and open/update Pull Request**: Run `/flow:archive <flow_id>`, push the branch (with user confirmation), and open or update the PR per [`../../flow-docs/references/prs-commits-and-changelogs.md`](../../flow-docs/references/prs-commits-and-changelogs.md) (`<type>(<scope>): <concise summary>`, `## Summary` and `## Key Changes` only, no internal review ceremony or `## Verification` block).
   3. `merge` — **Merge back to base branch locally and archive**: Run `/flow:archive <flow_id>`, merge into the local base branch (`main`/`master`), re-run verification on the merged branch, and clean up the feature branch or worktree.
   4. `discard` — **Discard work**: Require explicit typed `"discard"` confirmation from the user before resetting or removing branch or worktree state.
3. **Git Worktree Cleanup**: If the flow ran inside an isolated `git worktree`, offer to remove the worktree after branch merge or PR push.
