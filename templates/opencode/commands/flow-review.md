---
description: Dispatch code review with Beads-aware git range
---

# Flow Review

Dispatch a code review for a Flow's implementation using Beads-aware git range detection.

## Usage
`/flow-review {flow_id}`

## Phase 1: Load Context

1. **Flow ID:** Use argument or auto-discover from `.agents/flows.md`.
2. **Read Artifacts:** `.agents/specs/<flow_id>/spec.md` (requirements), `.agents/patterns.md` (conventions).
3. **Load Beads:** `br show <epic_id>`, `br list --parent <epic_id> --status closed`

## Phase 2: Determine Git Range

1. **From Beads:** Extract commit SHAs from task close reasons (`"commit: abc1234"`). Base = before earliest, Head = latest or HEAD.
2. **Fallback:** `git merge-base HEAD main`
3. **Confirm:** Show `git log --oneline <base>..<head>` and ask user to confirm range.

## Phase 3: Dispatch Review

Dispatch code review subagent with:
- What was implemented (from spec.md)
- Requirements (from spec.md)
- Git range
- Project conventions (from patterns.md)

## Phase 4: Present Results

Format by severity: Critical, Important, Minor, Strengths.
Overall assessment: Ready to proceed or Issues need attention.

## Phase 5: Handle Feedback

- No performative agreement. Technical evaluation only.
- Verify suggestions against codebase before implementing.
- Push back with reasoning if wrong. YAGNI check for unrequested features.
- Fix Critical immediately. Fix Important before next phase. Note Minor in learnings.md.

## Phase 6: Log

Append review summary to `.agents/specs/<flow_id>/learnings.md`.

## Critical Rules

1. **BEADS-AWARE** - Use Beads task records for git range
2. **ACTIONABLE** - Severity-based, not nit-picking
3. **LOG EVERYTHING** - Review findings go to learnings.md
