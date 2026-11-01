# Flow Revert (`/flow:revert`)

Safely revert a task, phase, or flow using `git revert` and synchronize `.agents/bundles/specs/<flow_id>/` task frontmatter and checklist state.

## Usage

- `/flow:revert task <flow_id> <task_id>` — Revert a single completed task's commit.
- `/flow:revert phase <flow_id> <phase_number>` — Revert all completed task commits in a phase.
- `/flow:revert flow <flow_id>` — Revert all completed task commits in a flow.

## Workflow

1. **Resolve Target Commits**:
   - Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/*.md` and collect the `commit` SHAs for the target task(s) in reverse chronological order.
   - Verify via `git cat-file -t <sha>` that each commit exists on the current branch.
2. **Confirm Revert Scope (`structured-choice-v1`)**:
   - Display the exact commits, task IDs, and affected files to be reverted and confirm with the user via [`interaction.md`](interaction.md).
3. **Execute `git revert --no-commit` & Synchronize Markdown State**:
   - Run `git revert --no-commit <commit_shas>`. If a revert conflict occurs, stop immediately, report the conflicting paths, and ask the user whether to resolve or `git revert --abort`.
   - Update each reverted task worksheet (`state: pending`, `commit: null`, `last_verified_at: null`, `last_verified_commit: null`, `verification_evidence: null`), reset its `spec.md` checklist marker to `- [ ]`, and update `spec.md` `current_task` and `## 5. Continuity Snapshot`.
   - Stage the reverted files together with the updated `tasks/*.md` and `spec.md`, and commit `revert(<scope>): <reason>`.
4. **Post-Revert Verification**:
   - Run the repository's fast verification gate (`make lint` / targeted tests from `knowledge/workflow.md`) to confirm a clean working tree and passing baseline.
