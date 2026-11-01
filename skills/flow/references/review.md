# Flow Review (`/flow:review`)

Run zero-context reviews across a flow's exact Git range (`base_commit..head_commit`) along three axes—**Spec Conformance**, **Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells**, and **Mandatory Quality & Debloat (`quality-review-v1`)**—then adjudicate every finding (`ADOPT`, `CONTEST`, or `ESCALATE`) and verify remediations.

<!-- quality-review-contract: start -->
```yaml
contract: quality-review-v1
mandatory_dispatch: true
completion_order: [verification, code_review, quality_review, finish]
blocking_severities: [Critical, Important]
adjudication: [ADOPT, CONTEST, ESCALATE]
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

## Phase 2: Zero-Context Review Dispatch (Zero-Context Isolation Rules)

When dispatching reviewers, strictly enforce the **Zero-Context Isolation Rules**:

1. **Disk-Only Inputs**: Pass only on-disk artifact paths (`spec.md`, `tasks/*.md`, `.agents/skills/`, `knowledge/` chapters) and the exact `base_commit..head_commit` range.
2. **No Rationale Priming**: Never pass conversational history, design rationales, or explanations of *why* the code was written a certain way—if the code and docstrings are not self-explanatory to a cold reader, that is a valid finding.
3. **No Leading Focus Hints**: Never instruct the reviewer to ignore areas or pre-excuse trade-offs.
4. **No Pre-Digesting**: Never summarize the diff for the reviewer; let the reviewer inspect `git diff {base_commit}..{head_commit}` and repository files directly.

### Harness Dispatch Modes

- **When `run_workflow` Is Available (Google Antigravity)**:
  - Execute an async Python workflow script that enters `phase("Zero-Context Code & Quality Review")` and fans out `parallel()` across:
    - `agent(type_name="code-reviewer", role="Correctness, Spec & Standards Reviewer", schema=CODE_REVIEW_SCHEMA, model="inherit")`
    - `agent(type_name="quality-reviewer", role="Debloat & Test Strength Reviewer", schema=QUALITY_REPORT_SCHEMA, model="inherit")`
    - Any matching project-local `.agents/agents/<domain>-reviewer` subagents.
  - Hold persistent reviewer handles (`code_reviewer = agent(...)`, `quality_reviewer = agent(...)`) so if `ADOPT` remediations are applied, Round 2 verification is sent to the same isolated reviewer handle (`await code_reviewer(round2_prompt, schema=...)`).
- **In All Other Harnesses**:
  - Dispatch `@code-reviewer` (plus any matching `.agents/agents/<domain>-reviewer`) and `@quality-reviewer` (`model: inherit`) with the same disk-only brief and `base_commit..head_commit` range.

## Phase 3: Review Axes

### Spec Conformance (`@code-reviewer`)

- **Requirement Coverage**: Every Functional Requirement (`R1..RN`), Non-Functional Constraint, and Acceptance Scenario in `spec.md` is implemented and verified.
- **Scope Discipline**: Flag unrequested feature creep, silent contract deviations, or drift between `tasks/<id>-<slug>.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers.
- **Security & Operational Safety**: Flag command injection, unsafe shell interpolation, leaked secrets, or unsafe Git/hook mutations.

### Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells (`@code-reviewer` + `<domain>-reviewer`)

Documented repository standards (`AGENTS.md`, `product/tech-stack.md`, `knowledge/patterns/`, `.agents/skills/<domain>/`, and `.agents/skills/review-<domain>/references/checklist.md`) always take precedence; when an area is not covered by a repo-specific rule, evaluate **Deep-Module Design** and **Baseline Structural Code Smells**:

1. **Deep-Module Seam & Dependency Category Audit**:
   - Flag shallow pass-through modules, 1:1 interface wrappers with only one implementation (*"one adapter = hypothetical seam"*), or mock-heavy tests that violate the dependency categories (`In-process`, `Local-substitutable`, `Remote-owned (Ports & Adapters)`, `External boundary`).
2. **Baseline Structural Code Smells**:
   - *Long Function*, *Large Class / Module*, *Long Parameter List*, *Divergent Change* (one module changed for multiple unrelated reasons), *Shotgun Surgery* (one logical change scattered across many modules), *Feature Envy* (a function more interested in another class's state than its own), *Data Clumps* (the same parameter group passed together everywhere instead of a value object/`msgspec.Struct`), *Primitive Obsession*, *Repeated Switches / Conditionals*, *Loops Instead of Pipelines*, *Speculative Generality* (unused hooks/params added "just in case"), and *Message Chains* (deep `a.b().c().d()` chains).
3. **False-Positive Suppressions**:
   - Suppress every project-verified safe pattern listed in `.agents/skills/review-*/references/false-positive-suppressions.md` (`FP-<PREFIX>-NN`).

### Mandatory Quality & Debloat Review (`@quality-reviewer` — `quality-review-v1`)

- **Semantic Surface & Code Organization**: Flag dead code, pass-through wrappers failing the deletion test, standalone private `_...` module helpers that belong on their domain class, unnecessary function-scoped imports, inline `#` restatement comments in Python, and leftover compatibility shims.
- **Test & Gate Strength**: Flag Implementation-Coupled tests, Tautological (mock-echo) tests, horizontal-slicing tests, and standalone `test_*remediation*.py` / `test_*audit*.py` files.
- **Prose & Documentation Discipline**: Flag numbered buzzwords, AI puffery, chronological sediment, and leaked internal ceremony in docs, specs, or comments.

## Phase 4: Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`) & Waiver Rules

Evaluate every finding against the actual repository code and `.agents/skills/review-*/references/false-positive-suppressions.md`:

- **`ADOPT`**:
  - Fix valid `Critical` or `Important` correctness, seam, SUT integrity, or debloat findings in the canonical production/test files (or run `/flow:revise` if a task worksheet needs updating), rerun verification gates, and re-verify with the reviewer on the updated `base_commit..head_commit` range.
- **`CONTEST`**:
  - Reject false positives, suggestions that violate `false-positive-suppressions.md`, or out-of-scope feature creep by citing exact `path/to/file::Symbol` evidence or the matching `FP-<PREFIX>-NN` rule in the Adjudication Ledger. If a new recurring false positive was discovered, offer to record it in `false-positive-suppressions.md`.
- **`ESCALATE`**:
  - When a reviewer finding exposes a genuine requirement trade-off or user-visible behavior choice, pause and present the options to the user via `structured-choice-v1` ([`interaction.md`](interaction.md)).
- **Finding-Specific Waiver Rule**:
  - Dispatch of `@code-reviewer` and `@quality-reviewer` is mandatory and cannot be waived. If the user chooses to waive a specific blocking finding, record `waived_by: user`, `finding_id`, and `reason` in the Adjudication Ledger and `learnings.md`.

## Phase 5: Present Adjudication Ledger & Handoff

1. Present the **Review & Adjudication Report** (`Range`, `Review Findings`, `QualityReport`, and `Adjudication Ledger: Finding ID | Axis | Severity | Verdict (ADOPT/CONTEST/ESCALATE) | Evidence / Commit`).
2. Append a concise review summary to `.agents/bundles/specs/<flow_id>/learnings.md` and hand off to `/flow:finish <flow_id>`.
