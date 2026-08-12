---
description: Dispatch code review for a flow using the git range from its task-file commits
---

# Flow Review

Dispatch a code review for a Flow's implementation using the git range derived from its task-file commits.

## Usage
`/flow-review {flow_id}`

## Phase 1: Load Context

1. **Flow ID:** Use argument or auto-discover by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active`.
2. **Read Artifacts:** `.agents/bundles/specs/<flow_id>/spec.md` (requirements), `.agents/bundles/knowledge/patterns/patterns.md` (conventions).
3. **Read Task Files:** All of `.agents/bundles/specs/<flow_id>/tasks/*.md`, collecting `commit:` SHAs from tasks with `state: closed`.

## Phase 2: Determine Git Range

1. **From Task Files:** Use the `commit:` SHAs collected from closed task files. Base = before earliest, Head = latest or HEAD.
2. **Fallback:** `git merge-base HEAD main`
3. **Confirm:** Show `git log --oneline <base>..<head>` and ask user to confirm range.

## Phase 3: Dispatch Review

Dispatch code review subagent with:
- What was implemented (from spec.md)
- Requirements (from spec.md)
- Git range
- Project conventions (from knowledge/patterns/patterns.md)

For targeted analysis, consider dispatching specialized reviewers alongside the general review:

- `flow:security-auditor` — auth, user input, secrets, external API calls
- `flow:architecture-critic` — new components, boundary changes, system structure
- `flow:performance-analyst` — hot paths, database queries, latency-sensitive operations
- `flow:devils-advocate` — large changes or unchallenged structural assumptions

## Phase 4: Present Results

Format by severity: Critical, Important, Minor, Strengths.
Overall assessment: Ready to proceed or Issues need attention.

## Phase 5: Handle Feedback

- No performative agreement. Technical evaluation only.
- Verify suggestions against codebase before implementing.
- Push back with reasoning if wrong. YAGNI check for unrequested features.
- Fix Critical immediately. Fix Important before next phase. Note Minor in learnings.md.

## Phase 6: Log

Append review summary to `.agents/bundles/specs/<flow_id>/learnings.md`.

## Critical Rules

1. **TASK-FILE-AWARE** - Use task-file `commit:` records for the git range
2. **ACTIONABLE** - Severity-based, not nit-picking
3. **LOG EVERYTHING** - Review findings go to learnings.md
