# Flow Finish (`/flow:finish`)

Complete a flow on the current branch after verifying that all task worksheets are `completed` (or `deferred`/`skipped`), full verification gates pass, and zero-context correctness and quality reviews (`quality-review-v1`) are clean.

## Phase 1: Scope-Cap & Pragmatic Branch-Local Closure

1. Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/*.md`.
2. Confirm every task worksheet is `state: completed` (or `closed` / `deferred` / `skipped`) and matches its `spec.md` checklist marker (`[x] [<sha>]` or `[-]`).
3. **Branch-Local Closure & Scope-Cap Discipline**:
   - Flow completion (`state: completed`) and archival (`/flow:archive`) are strictly branch-local transitions—never block completion waiting for a remote PR merge.
   - If the original problem is solved and remaining open tasks represent newly discovered follow-up scope, offer via `structured-choice-v1` to mark those tasks `state: deferred` (`[-]` in `spec.md`), close the current flow cleanly, and seed a follow-up spec via `/flow:plan <new_flow_id>`.

## Phase 2: Full Verification, Review & ADR Gate

1. **Full Verification Gate**: Run the repository's canonical verification commands from `.agents/bundles/knowledge/workflow.md` (lint, typecheck, validator, and full unit/integration test suite) and confirm exit code `0`.
2. **Correctness & Quality Review Gate (`quality-review-v1`)**: If `/flow:review <flow_id>` has not yet passed on the current `base_commit..HEAD` range, execute [`review.md`](review.md) (`@code-reviewer` + `@quality-reviewer`) and resolve any adopted findings before proceeding.
3. **ADR Filter (`knowledge/decisions/adr-NNN-<slug>.md`)**:
   - Evaluate whether the flow introduced a decision that meets **all three** criteria:
     1. *Hard to reverse* (changes storage schema, public wire protocol, cross-module seam, or core dependency),
     2. *Surprising without context* (a future engineer or isolated agent might try to "simplify" or undo it), and
     3. *Genuine trade-off* (two viable alternatives existed with real pros and cons).
   - If all three hold, author `.agents/bundles/knowledge/decisions/adr-NNN-<slug>.md` with `Context`, `Decision`, `Alternatives Rejected`, and `Consequences`.

## Phase 3: Mark Spec Completed & Present Completion Options (`structured-choice-v1`)

1. Update `.agents/bundles/specs/<flow_id>/spec.md` frontmatter (`state: completed`, `current_task: null`, `last_verified_checkpoint: <HEAD_SHA>`, `updated_at`) and `.agents/bundles/log.md`.
2. Present the completion options via `structured-choice-v1` ([`interaction.md`](interaction.md)):
   1. `archive` — **Archive flow now on current branch (Recommended)**: Run [`archive.md`](archive.md) (`/flow:archive <flow_id>`) on this branch to synthesize durable learnings into `.agents/bundles/knowledge/**` and `.agents/skills/**` and remove the completed spec directory.
   2. `pr` — **Archive and open/update Pull Request**: Run `/flow:archive <flow_id>`, push the branch (with user confirmation), and create/update the PR following [`../../flow-docs/references/prs-commits-and-changelogs.md`](../../flow-docs/references/prs-commits-and-changelogs.md) (`<type>(<scope>): <concise summary>` title, `## Summary` and `## Key Changes` only, zero internal review/audit ceremony, and no `## Verification` block).
   3. `merge` — **Merge back to base branch locally and archive**: Run `/flow:archive <flow_id>`, merge the feature branch into the local base branch (`main`/`master`), re-run verification on the merged base branch, and clean up the feature branch/worktree if applicable.
   4. `discard` — **Discard work**: Require explicit typed `"discard"` confirmation from the user before resetting or removing branch/worktree state.
3. **Git Worktree Cleanup**: If the flow ran inside an isolated `git worktree`, offer to remove the worktree cleanly after branch merge or PR push.
