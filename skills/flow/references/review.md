
# Flow Review

Dispatch a code review for a flow's implementation with Beads-aware git range detection.

## Usage

`flow-review {flow_id}` or `flow-review` (uses current flow)

## Phase 1: Load Context

1. **Read Flow Artifacts:**
   - `.agents/specs/{flow_id}/spec.md` (requirements and plan)
   - `.agents/specs/{flow_id}/metadata.json`
2. **Read Project Context:** `.agents/patterns.md`
3. **Load Beads context:**

   ```bash
   br show {epic_id}
   ```

## Phase 2: Determine Git Range

### From Beads (Primary)

Extract commit SHAs from Beads task close reasons:

```bash
br list --parent {epic_id} --status closed
```

Each closed task has a reason like `"commit: abc1234"`. Use:

- **Base:** commit before earliest task SHA
- **Head:** latest task SHA or current HEAD

### From Git (Fallback)

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
4. **Conventions:** From `.agents/patterns.md`
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

Follow code review reception discipline:

- **No performative agreement** ("You're absolutely right!", "Great point!")
- **Verify** suggestions against codebase before implementing
- **Push back** with technical reasoning if reviewer is wrong
- **YAGNI check:** If reviewer suggests features not in spec, question the need
- **Clarify** all unclear items before implementing any

### Acting on Feedback

- **Critical** → fix immediately, re-run review
- **Important** → fix before proceeding to next phase/finish
- **Minor** → note in learnings.md, fix if quick

### Log Findings

Append review summary to `.agents/specs/{flow_id}/learnings.md`:

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
