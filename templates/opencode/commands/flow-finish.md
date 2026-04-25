---
description: Complete flow work - verify, review, merge/PR/keep/discard
---

# Flow Finish

Complete a Flow's development work: verify tests, dispatch code review, and integrate.

## Usage
`/flow-finish {flow_id}`

## Phase 1: Load Context

1. **Flow ID:** Use argument or auto-discover from `.agents/flows.md` (look for `[~]` in-progress flows).
2. **Read Artifacts:** `.agents/specs/<flow_id>/spec.md`, `metadata.json`
3. **Check Beads:** `bd show <epic_id>`, verify all tasks completed. If open tasks remain, warn user.

## Phase 2: Verification Gate

**IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

1. Run full test suite. Read output. Confirm 0 failures.
2. Run coverage check. Confirm target met with actual numbers.
3. Run `/flow-sync` to ensure spec.md is current.
4. If any check fails, report actual results and STOP.

## Phase 3: Code Review

1. Get git range from Beads task records (commit SHAs from `bd close` reasons).
2. Dispatch code review subagent with: spec.md requirements, patterns.md, git range.
3. Fix Critical issues before proceeding. Fix Important issues or confirm with user.
4. Log findings to `.agents/specs/<flow_id>/learnings.md`.

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

- Close Beads epic: `bd close <epic_id> --reason "Flow finished: <option>"`
- Clean up worktree if applicable.

## Critical Rules

1. **VERIFY FIRST** - No claims without fresh evidence
2. **BEADS IS SOURCE OF TRUTH** - Check all tasks are complete
3. **USER DECIDES** - Present options, don't assume
