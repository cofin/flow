---
description: Complete flow work - verify, review, merge/PR/keep/discard
---

# Flow Finish

Complete a Flow's development work: verify tests, dispatch code review, and integrate.

**CRITICAL:** `/flow-finish` ensures the OKF task files' state is finalized and the human view is synced before the flow is integrated.

## Usage
`/flow-finish {flow_id}`

## Phase 1: Load Context

1. **Flow ID:** Use argument or auto-discover by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active`.
2. **Read Artifacts:** `.agents/bundles/specs/{flow_id}/spec.md` and all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
3. **Task Validation:** Ensure every task file has `state: closed` or `skipped`. If open or in-progress tasks remain, warn the user.

## Phase 2: Verification Gate

**IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

1. Run full test suite. Read output. Confirm 0 failures.
2. Run coverage check. Confirm target met with actual numbers.
3. Run `/flow-sync` to reconcile the `spec.md` task checklist with the task files.
4. If any check fails, report actual results and STOP.

## Phase 3: Code Review

1. Get the git range from the task files: collect `commit:` SHAs from tasks with `state: closed`.
2. Dispatch code review subagent with: spec.md requirements, `knowledge/patterns.md`, git range.
3. Fix Critical issues before proceeding. Fix Important issues or confirm with user.
4. Log findings to `.agents/bundles/specs/{flow_id}/learnings.md`.

## Phase 4: Present Options

Present exactly 4 options:
1. Merge back to base branch locally
2. Push and create a Pull Request
3. Keep the branch as-is
4. Discard this work

## Phase 5: Execute Choice

- **Merge:** Checkout base, pull, merge, run tests on result, delete feature branch. Suggest `/flow-archive`.
- **PR:** Push with -u, create PR via `gh pr create`. Suggest `/flow-archive` after merge.
- **Keep:** Report branch and worktree location.
- **Discard:** Require typed 'discard' confirmation. Checkout base, delete branch.

## Phase 6: Cleanup

- **Update Spec Status:** Mark the spec complete by editing the frontmatter of `.agents/bundles/specs/{flow_id}/spec.md` to `state: completed` and updating `updated_at`.
- **Archive:** Recommend `/flow-archive` to synthesize learnings and clean up the active spec bundle directory.
- Clean up worktree if applicable.

## Critical Rules

1. **VERIFY FIRST** - No claims without fresh evidence
2. **TASK FILES ARE SOURCE OF TRUTH** - Check all task files are closed or skipped
3. **USER DECIDES** - Present options, don't assume
