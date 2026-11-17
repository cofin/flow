# Flow Revert (`/flow:revert`)

Revert a task, chapter, phase, or flow with `git revert` and sync `.agents/bundles/specs/<flow_id>/` task frontmatter, chapter specs, `chapters/index.md`, and root `spec.md` in present tense.

## Usage

- `/flow:revert task <flow_id> <task_id>` — Revert one completed task's commit.
- `/flow:revert chapter <flow_id> <chapter_id>` — Revert all completed task and sync/closeout commits in a chapter (`specs/<flow_id>/chapters/<chapter_id>/`).
- `/flow:revert phase <flow_id> <phase_number>` — Revert all completed task commits in a phase.
- `/flow:revert flow <flow_id>` — Revert all completed chapter and task commits in a flow.

## Workflow

1. **Resolve Target Commits**:
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), target `chapters/<chapter_id>/spec.md`, and `tasks/*.md`.
   - Collect all `commit` SHAs and any chapter sync or closeout commits in reverse chronological order.
   - Verify via `git cat-file -t <sha>` that each commit exists on the current branch.
2. **Confirm Revert Scope**:
   - Display the exact commits, chapter/task IDs, and affected files to revert.
   - Confirm with the user using the interactive prompt format in [`interaction.md`](interaction.md).
3. **Run `git revert --no-commit` & Sync State**:
   - Run `git revert --no-commit <commit_shas>`.
   - If a conflict occurs, stop, report the conflicting paths, and ask whether to resolve or run `git revert --abort`.
   - Reset each reverted task worksheet (`state: pending`, `commit: null`, `last_verified_at: null`, `last_verified_commit: null`, `verification_evidence: null`) and set its owning `spec.md` checklist marker to `- [ ]`.
   - For a reverted chapter (or a `completed` chapter with a reverted task), set `chapters/<chapter_id>/spec.md` to `state: planned` or `active` and clear `last_reviewed_commit: null`.
   - Update `chapters/index.md`, reset the chapter's root `specs/<flow_id>/spec.md` checklist marker to `- [ ]`, and set `current_chapter` to the earliest open chapter.
   - Rewrite `## 6. Current State & Remaining Plan Snapshot` in present tense without historical narrative, and prepend a `revert` entry to `.agents/bundles/log.md`.
   - Stage the reverted files with the updated `tasks/*.md`, `chapters/index.md`, chapter `spec.md`, root `spec.md`, and `log.md`.
   - Create a signed commit with `git commit -S -m "revert(<scope>): <reason>"`.
4. **Post-Revert Verification**:
   - Run the repository's fast check (`make lint` and targeted tests from `knowledge/workflow.md`) to confirm a clean working tree and passing baseline.
