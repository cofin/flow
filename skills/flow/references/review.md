
# Flow Review

Dispatch correctness review followed by mandatory read-only quality review for a flow's exact Git range.

## Quality review contract

<!-- quality-review-contract: start -->
```yaml
contract: quality-review-v1
mandatory_dispatch: true
dispatch_after: code_review
completion_order: [verification, code_review, quality_review, finish]
blocking_severities: [Critical, Important]
report:
  name: QualityReport
  exact_keys: [reviewer, base_commit, head_commit, debloat_source, findings]
  reviewer: quality-reviewer
  commit_format: 7_to_40_lowercase_hex
  finding:
    exact_keys: [finding_id, severity, file, symbol, evidence, preserved_invariant, remediation_target, reverification]
    severities: [Critical, Important, Minor]
    evidence_required: true
    remediation_target_required: true
    reverification_required: true
skill_resolution:
  order: [.agents/skills/debloat/SKILL.md, skills/debloat/SKILL.md, inline_fallback]
  report_values:
    .agents/skills/debloat/SKILL.md: consumer_skill
    skills/debloat/SKILL.md: packaged_skill
    inline_fallback: inline_fallback
  inline_fallback: preserve_behavior_and_public_contracts_review_source_tests_prose_and_native_gates_read_only
one_commit_range:
  head_commit: commit
  base_commit: parent_of_head
freshness:
  exact_range_required: true
  invalidated_by: [head_change, base_change, remediation, archive_fragment_change]
remediation:
  route: revise
  required_sequence: [create_or_adjust_task, execute_task, rerun_affected_verification, rerun_code_review, dispatch_fresh_quality_review]
waiver:
  dispatch_still_required: true
  one_finding_only: true
  required: [finding_id, rationale, approval_text, approved_at, compensating_evidence, base_commit, head_commit]
  other_findings_unchanged: true
archive_candidate:
  disposable_local_range_required: true
  exact_manifest_required: true
  manifest_comparison: byte_for_byte
  changed_fragment_action: render_and_review_fresh_candidate
runtime_dependency: agent_file_tools_only
evaluator_module: forbidden
```
<!-- quality-review-contract: end -->

Installed workflows apply this contract from Markdown with ordinary agent file
and repository-diff tools. They never import a gate/evaluator module.

## Usage

`flow-review {flow_id}` or `flow-review` (uses current flow)

## Phase 1: Load Context

1. **Read Flow Artifacts:**
   - `.agents/bundles/specs/{flow_id}/spec.md` (requirements and plan)
   - `.agents/bundles/specs/{flow_id}/tasks/*.md` (task states and commit SHAs)
2. **Read Project Context:** `.agents/bundles/knowledge/patterns.md`

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

Record and show the range before dispatch. User acknowledgment is not a waiver
and cannot bypass either review.

## Phase 3: Dispatch Correctness Review

Dispatch code review subagent with:

1. **What was implemented:** Summary from spec.md Specification section
2. **Requirements:** From spec.md Requirements section
3. **Git range:** `{base_sha}..{head_sha}`
4. **Conventions:** From `.agents/bundles/knowledge/patterns.md`
5. **Description:** Brief summary of the flow's purpose

## Phase 4: Dispatch Mandatory Quality Review

After correctness review returns, always dispatch `quality-reviewer` on the
same exact `base_commit..head_commit`. For a one-commit change, `head_commit` is
that commit and `base_commit` is its parent.

Resolve the debloat policy in order:

1. `.agents/skills/debloat/SKILL.md` as `consumer_skill`.
2. Packaged `skills/debloat/SKILL.md` as `packaged_skill`.
3. If neither can be loaded, use the inline fallback from the contract and
   record `debloat_source: inline_fallback`.

The reviewer is read-only. Provide the exact range, requested invariants,
project-shaped knowledge/pattern paths relevant to the change, correctness
review result, and verification evidence. Require the closed `QualityReport`
shape above. Do not accept a report for a different range.

## Phase 5: Present Results

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

Quality Review: {flow_id}

Exact range: {base_sha}..{head_sha}
Debloat source: {consumer_skill | packaged_skill | inline_fallback}

Critical / Important / Minor Findings:
  {evidence-backed findings or "None"}

Assessment: {Ready to proceed | Remediation required}
```

## Phase 6: Handle Feedback

### Receiving Review Results

Follow the **Critical Thinking Iron Law** for every review finding:

- **No performative agreement** ("You're absolutely right!", "Great point!")
- **Verify** suggestions against codebase before implementing. **Read the actual code.**
- **Push back** with technical reasoning if reviewer is wrong.
- **YAGNI check:** If reviewer suggests features not in spec, question the need.
- **Clarify** all unclear items before implementing any.

### Acting on Feedback

- **Critical/Important correctness finding** → route through the appropriate task/plan change and rerun correctness review
- **Critical/Important quality finding** → block finish, use `revise` to create or adjust a remediation task, execute it, rerun affected gates and correctness review, then always dispatch a fresh quality review on the new exact range
- **Minor** → note in learnings.md, fix if quick

Remediation changes the head and invalidates every prior pass. A stale report is
never evidence for the new range.

### Finding-specific waiver

A waiver is legal only after quality review ran. Fresh explicit user approval
may waive one named finding for one exact range. Record its `finding_id`,
`rationale`, exact approval text and UTC time, compensating evidence, and
`base_commit`/`head_commit`. It does not waive another finding, survive a range
change, or substitute for mandatory dispatch.

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

1. **VERIFY GIT RANGE** — Confirm and record the exact base/head before reviewing
2. **NO PERFORMATIVE AGREEMENT** — Technical evaluation, not social performance
3. **LOG FINDINGS** — Always append to learnings.md
4. **YAGNI** — Don't accept suggestions to add unrequested features
5. **FIX CRITICAL** — Must resolve Critical issues before proceeding
6. **QUALITY REVIEW ALWAYS RUNS** — A waiver cannot bypass dispatch
7. **READ-ONLY QUALITY AGENT** — Findings become remediation work; the reviewer never edits
8. **FRESH RANGE** — Remediation or candidate drift requires verification, correctness review, and quality review again
