---
description: Dispatch code review with Beads-aware git range
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Flow Review

Reviewing flow: **$ARGUMENTS**

## 1.0 SYSTEM DIRECTIVE

You are dispatching a code review for a Flow's implementation. Your task is to determine the correct git range from Beads, dispatch a review subagent, and present actionable results.

---

## 2.0 LOAD CONTEXT

1. **Flow ID:** Use `$ARGUMENTS` or auto-discover from `.agents/flows.md`.
2. **Read Artifacts:** `.agents/specs/<flow_id>/spec.md` (requirements), `.agents/patterns.md` (conventions).
3. **Load Beads:** `br show <epic_id>`, `br list --parent <epic_id> --status closed`

---

## 3.0 DETERMINE GIT RANGE

1. **From Beads:** Extract commit SHAs from task close reasons (`"commit: abc1234"`). Base = before earliest, Head = latest or HEAD.
2. **Fallback:** `git merge-base HEAD main`
3. **Confirm:** Show `git log --oneline <base>..<head>` and ask user to confirm range.

---

## 4.0 DISPATCH REVIEW

Dispatch code review subagent with:

- What was implemented (from spec.md)
- Requirements (from spec.md)
- Git range
- Project conventions (from patterns.md)

### Specialized Reviewers

For targeted analysis, consider dispatching specialized reviewer subagents alongside the general code review:

- `flow:security-auditor` — when changes touch authentication, authorization, user input handling, secrets, or external API calls
- `flow:architecture-critic` — when changes introduce new components, modify boundaries, or affect system structure
- `flow:performance-analyst` — when changes affect hot paths, database queries, or latency-sensitive operations
- `flow:devils-advocate` — when changes are large or make structural assumptions that haven't been challenged

---

## 5.0 PRESENT RESULTS

Format by severity: Critical, Important, Minor, Strengths.
Overall assessment: Ready to proceed or Issues need attention.

---

## 6.0 HANDLE FEEDBACK

- No performative agreement. Technical evaluation only.
- Verify suggestions against codebase before implementing.
- Push back with reasoning if wrong. YAGNI check for unrequested features.
- Fix Critical immediately. Fix Important before next phase. Note Minor in learnings.md.

### Feedback Evaluation

Apply `flow:challenge` when evaluating review findings. Do not reflexively accept or dismiss feedback — use structured critical reassessment to determine whether each finding is valid, actionable, and correctly scoped before implementing changes.

---

## 7.0 LOG

Append review summary to `.agents/specs/<flow_id>/learnings.md`.
