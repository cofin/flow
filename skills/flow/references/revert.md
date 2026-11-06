# Flow Revert (`/flow:revert`)

Safely revert a task, chapter, phase, or flow using `git revert` and synchronize `.agents/bundles/specs/<flow_id>/` task frontmatter, chapter specifications, `chapters/index.md`, and root `spec.md` roadmap state in present tense.

## Usage

- `/flow:revert task <flow_id> <task_id>` — Revert a single completed task's commit.
- `/flow:revert chapter <flow_id> <chapter_id>` — Revert all completed task and sync/closeout commits in a chapter (`specs/<flow_id>/chapters/<chapter_id>/`).
- `/flow:revert phase <flow_id> <phase_number>` — Revert all completed task commits in a phase.
- `/flow:revert flow <flow_id>` — Revert all completed chapter and task commits in a flow.

## Workflow

1. **Resolve Target Commits**:
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), target `chapters/<chapter_id>/spec.md`, and `tasks/*.md`, collecting all `commit` SHAs (plus any chapter sync/closeout commits in that chapter's range) in reverse chronological order.
   - Verify via `git cat-file -t <sha>` that each commit exists on the current branch.
2. **Confirm Revert Scope (`structured-choice-v1`)**:
   - Display the exact commits, chapter/task IDs, and affected files to be reverted and confirm with the user via [`interaction.md`](interaction.md).
3. **Execute `git revert --no-commit` & Synchronize Present-Tense Markdown State**:
   - Run `git revert --no-commit <commit_shas>`. If a revert conflict occurs, stop immediately, report the conflicting paths, and ask the user whether to resolve or `git revert --abort`.
   - Update each reverted task worksheet (`state: pending`, `commit: null`, `last_verified_at: null`, `last_verified_commit: null`, `verification_evidence: null`) and reset its owning `spec.md` checklist marker to `- [ ]`.
   - For a reverted chapter (or a `completed` chapter containing a reverted task), set `chapters/<chapter_id>/spec.md` `state: planned` (or `active`), clear `last_reviewed_commit: null`, update `chapters/index.md`, reset the chapter's root `specs/<flow_id>/spec.md` checklist marker to `- [ ]`, set `current_chapter: <earliest_non_completed_chapter>`, and rewrite `## 6. Current State & Remaining Plan Snapshot` in present tense without historical narrative (prepending a `revert` entry to `.agents/bundles/log.md`).
   - Stage the reverted files together with the updated `tasks/*.md`, `chapters/index.md`, chapter `spec.md`, root `spec.md`, and `log.md`, and create a signed commit `git commit -S -m "revert(<scope>): <reason>"`.
4. **Post-Revert Verification**:
   - Run the repository's fast verification gate (`make lint` / targeted tests from `knowledge/workflow.md`) to confirm a clean working tree and passing baseline.
