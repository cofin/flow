# Flow Review (`/flow:review`)

Run zero-context correctness, domain-checklist, and mandatory debloat quality reviews across a flow's exact Git range (`base_commit..head_commit`), adjudicate every finding with evidence (`ADOPT` vs. `CONTEST`), and verify remediations.

<!-- quality-review-contract: start -->
```yaml
contract: quality-review-v1
mandatory_dispatch: true
completion_order: [verification, code_review, quality_review, finish]
blocking_severities: [Critical, Important]
adjudication: [ADOPT, CONTEST]
report:
  name: QualityReport
  exact_keys: [reviewer, base_commit, head_commit, debloat_source, findings]
  finding_keys: [finding_id, severity, file, symbol, evidence, preserved_invariant, remediation_target, reverification]
```
<!-- quality-review-contract: end -->

## Phase 1: Determine Exact Git Range & Match Project Lenses

1. Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/*.md`.
2. Determine `base_commit..head_commit` from the parent of the earliest completed task `commit` SHA to `HEAD` (or `$(git merge-base main HEAD)..HEAD`), and inspect `git diff --stat {base_commit}..{head_commit}`.
3. Match the modified file paths against `.agents/skills/index.md` and `.agents/bundles/knowledge/index.md` to attach the relevant project-local `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/` (`references/checklist.md` + `references/false-positive-suppressions.md`), and `knowledge/**` chapters.

## Phase 2: Dynamic, Zero-Context Review Dispatch

Pass **only on-disk artifact paths and the exact `base_commit..head_commit` range** to reviewers—never pass conversational history:

1. **When `run_workflow` Is Available (Google Antigravity)**:
   - Execute an async Python workflow script that enters `phase("Zero-Context Code & Quality Review")` and fans out `parallel()` across:
     - `agent(type_name="code-reviewer", role="Correctness & Spec Reviewer", schema=CODE_REVIEW_SCHEMA, model="inherit")`
     - `agent(type_name="quality-reviewer", role="Debloat & Test Strength Reviewer", schema=QUALITY_REPORT_SCHEMA, model="inherit")`
     - Any matching project-local `.agents/agents/<domain>-reviewer` subagents.
   - Hold persistent reviewer handles (`code_reviewer = agent(...)`, `quality_reviewer = agent(...)`) so if `ADOPT` remediations are applied, Round 2 verification is sent to the same isolated reviewer handle (`await code_reviewer(round2_prompt, schema=...)`).
2. **In All Other Harnesses**:
   - Dispatch `@code-reviewer` (plus any matching `.agents/agents/<domain>-reviewer`) and `@quality-reviewer` (`model: inherit`) with the same disk-only brief and `base_commit..head_commit` range.

## Phase 3: Evidence-Backed Finding Adjudication (`ADOPT` vs. `CONTEST`)

Evaluate every finding against the actual repository code and `.agents/skills/review-*/references/false-positive-suppressions.md`:

- **`ADOPT`**:
  - For valid `Critical` or `Important` correctness, SUT integrity, or debloat findings within the spec's scope, fix the issue in the canonical production/test files (or run `/flow:revise` if a task worksheet needs updating), rerun verification gates, and re-verify on the updated `base_commit..head_commit` range.
- **`CONTEST`**:
  - Reject false positives, suggestions that violate `false-positive-suppressions.md`, or out-of-scope feature creep by citing exact `path/to/file::Symbol` evidence or the matching `FP-<PREFIX>-NN` rule in the Adjudication Ledger.

## Phase 4: Present Adjudication Ledger & Log Summary

1. Present the **Review & Adjudication Report** (`Range`, `Code Review Findings`, `QualityReport`, and `Adjudication Ledger: Finding ID | Severity | Verdict (ADOPT/CONTEST) | Evidence / Commit`).
2. Append a concise review summary to `.agents/bundles/specs/<flow_id>/learnings.md` and hand off to `/flow:finish <flow_id>`.
