---
description: Complete flow work - verify, review, merge/PR/keep/discard
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Flow Finish

Completing flow: **$ARGUMENTS**

## 1.0 SYSTEM DIRECTIVE
You are completing a Flow's development work. Your task is to verify all tests pass, dispatch a code review, and help the user integrate their work.

CRITICAL: You must have FRESH VERIFICATION EVIDENCE before claiming anything passes.

---

## 2.0 LOAD CONTEXT
1.  **Flow ID:** Use `$ARGUMENTS` or auto-discover from `.agents/flows.md` (look for `[~]` in-progress flows).
2.  **Read Artifacts:** `.agents/specs/<flow_id>/spec.md`, `metadata.json`
3.  **Check Beads:** `br show <epic_id>`, verify all tasks completed. If open tasks remain, warn user.

---

## 3.0 VERIFICATION GATE
**IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

1.  **Run full test suite.** Read output. Confirm 0 failures.
2.  **Run coverage check.** Confirm target met with actual numbers.
3.  **Run `/flow-sync`** to ensure spec.md is current.
4.  If any check fails, report actual results and STOP.

---

## 4.0 CODE REVIEW
1.  Get git range from Beads task records (commit SHAs from `br close` reasons).
2.  Dispatch code review subagent with: spec.md requirements, patterns.md, git range.
3.  Fix Critical issues before proceeding. Fix Important issues or confirm with user.
4.  Log findings to `.agents/specs/<flow_id>/learnings.md`.

### Specialized Reviewers

For targeted analysis, consider dispatching specialized reviewer subagents alongside the general code review:
- `flow:security-auditor` — when changes touch authentication, authorization, user input handling, secrets, or external API calls
- `flow:architecture-critic` — when changes introduce new components, modify boundaries, or affect system structure
- `flow:performance-analyst` — when changes affect hot paths, database queries, or latency-sensitive operations
- `flow:devils-advocate` — when changes are large or make structural assumptions that haven't been challenged

Apply `flow:challenge` when evaluating review findings before implementing fixes. Structured critical reassessment prevents both reflexive agreement and reflexive dismissal of feedback.

---

## 5.0 PRESENT OPTIONS
Present exactly 4 options:
1. Merge back to base branch locally
2. Push and create a Pull Request
3. Keep the branch as-is
4. Discard this work

---

## 6.0 EXECUTE CHOICE
-   **Option 1 (Merge):** Checkout base, pull, merge, run tests on result, delete feature branch. Suggest `/flow-archive`.
-   **Option 2 (PR):** Push with -u, create PR via `gh pr create`. Suggest `/flow-archive` after merge.
-   **Option 3 (Keep):** Report branch and worktree location.
-   **Option 4 (Discard):** Require typed 'discard' confirmation. Checkout base, delete branch.

---

## 7.0 CLEANUP
-   Close Beads epic: `br close <epic_id> --reason "Flow finished: <option>"`
-   Clean up worktree if applicable (Options 1, 4).
