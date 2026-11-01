# Flow Revert (`/flow:revert`)

Safely revert a task, phase, or flow using `git revert` and synchronize `.agents/bundles/specs/<flow_id>/` task frontmatter and checklist state.

## Usage

- `/flow:revert task <flow_id> <task_id>` — Revert a single completed task's commit.
- `/flow:revert phase <flow_id> <phase_number>` — Revert all completed task commits in a phase.
- `/flow:revert flow <flow_id>` — Revert all completed task commits in a flow.

## Workflow

1. **Resolve Target Commits**:
   - Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/*.md` and collect the `commit` SHAs for the target task(s) in reverse chronological order.
2. **Confirm Revert Scope (`structured-choice-v1`)**:
   - Display the exact commits and files to be reverted and confirm with the user via [`interaction.md`](interaction.md).
3. **Execute `git revert` & Synchronize Markdown State**:
   - Run `git revert --no-commit <commit_shas>` and commit `revert(<scope>): <reason>`.
   - Update each reverted task worksheet (`state: pending`, `commit: null`, `last_verified_at: null`, `last_verified_commit: null`, `verification_evidence: null`) and reset its `spec.md` checklist marker to `- [ ]`.
   - Run the repository's fast verification gate (`make lint` / targeted tests) to confirm a clean working tree.
