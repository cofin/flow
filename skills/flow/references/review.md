
# Flow Review

Dispatch a code review for a flow's implementation, deriving the git range from the flow's task-file commits.

## Usage

`flow-review {flow_id}` or `flow-review` (uses current flow)

## Phase 1: Load Context

1. **Read Flow Artifacts:**
   - `.agents/bundles/specs/{flow_id}/spec.md` (requirements and plan)
   - `.agents/bundles/specs/{flow_id}/tasks/*.md` (task states and commit SHAs)
2. **Read Project Context:** `.agents/bundles/knowledge/patterns/patterns.md`

## Phase 2: Determine Git Range

### From Task Files (Primary)

Collect the `commit:` frontmatter SHAs from task files with `state: closed`. Use:

- **Base:** commit before earliest task SHA
- **Head:** latest task SHA or current HEAD

### From Git (Fallback)

When no task file carries a commit SHA:

```bash
git merge-base HEAD main  # or master
```

### Show Range

```bash
git log --oneline {base_sha}..{head_sha}
```

Confirm range with user: "Reviewing {N} commits from {base_sha} to {head_sha}. Correct?"

## Phase 3: Dispatch Review

Dispatch code review subagent with:

1. **What was implemented:** Summary from spec.md Specification section
2. **Requirements:** From spec.md Requirements section
3. **Git range:** `{base_sha}..{head_sha}`
4. **Conventions:** From `.agents/bundles/knowledge/patterns/patterns.md`
5. **Description:** Brief summary of the flow's purpose

## Phase 4: Present Results

Format review results:

```text
Code Review: {flow_id}

Commits reviewed: {count} ({base_sha}..{head_sha})

Critical Issues:
  {list or "None"}

Important Issues:
  {list or "None"}

Minor Issues:
  {list or "None"}

Strengths:
  {brief list}

Assessment: {Ready to proceed | Issues need attention}
```

## Phase 5: Handle Feedback

### Receiving Review Results

Follow the **Critical Thinking Iron Law** for every review finding:

- **No performative agreement** ("You're absolutely right!", "Great point!")
- **Verify** suggestions against codebase before implementing. **Read the actual code.**
- **Push back** with technical reasoning if reviewer is wrong.
- **YAGNI check:** If reviewer suggests features not in spec, question the need.
- **Clarify** all unclear items before implementing any.

### Acting on Feedback

- **Critical** → fix immediately, re-run review
- **Important** → fix before proceeding to next phase/finish
- **Minor** → note in learnings.md, fix if quick

### Log Findings

Append review summary to `.agents/bundles/specs/{flow_id}/learnings.md`:

```markdown
## [YYYY-MM-DD] Code Review

**Range:** {base_sha}..{head_sha}
**Issues Found:** {count by severity}
**Key Findings:**
- {finding 1}
- {finding 2}
```

## Critical Rules

1. **VERIFY GIT RANGE** — Confirm range with user before reviewing
2. **NO PERFORMATIVE AGREEMENT** — Technical evaluation, not social performance
3. **LOG FINDINGS** — Always append to learnings.md
4. **YAGNI** — Don't accept suggestions to add unrequested features
5. **FIX CRITICAL** — Must resolve Critical issues before proceeding
