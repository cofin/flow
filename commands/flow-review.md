---
description: Dispatch code review for a flow using the git range from its task-file commits
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Flow Review

> Lifecycle skill: use `flow-completion` through the `flow` router.

Reviewing flow: **$ARGUMENTS**

## 1.0 SYSTEM DIRECTIVE

You are dispatching a code review for a Flow's implementation. Your task is to determine the correct git range from the flow's task files, dispatch a review subagent, and present actionable results.

---

## 2.0 LOAD CONTEXT

1. **Flow ID:** Use `$ARGUMENTS` or auto-discover by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active`.
2. **Read Artifacts:** `.agents/bundles/specs/<flow_id>/spec.md` (requirements), `.agents/bundles/knowledge/patterns.md` (conventions).
3. **Read Task Files:** All of `.agents/bundles/specs/<flow_id>/tasks/*.md`, collecting `commit:` SHAs from tasks with `state: closed`.

---

## 3.0 DETERMINE GIT RANGE

1. **From Task Files:** Use the `commit:` SHAs collected from closed task files. Base = before earliest, Head = latest or HEAD.
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

Append review summary to `.agents/bundles/specs/<flow_id>/learnings.md`.
