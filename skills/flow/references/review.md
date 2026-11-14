# Flow Review (`/flow:review`)

Run zero-context reviews across a chapter's or flow's exact Git range (`base_commit..head_commit`) along four axes—**Spec Conformance**, **Present-Tense Markdown, Full-Plan Roadmap, & Doc-Sync Conformance**, **Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells**, and **Mandatory Quality, Zero-History Doc Hygiene, & Debloat (`quality-review-v1`)**—then adjudicate every finding (`ADOPT`, `CONTEST`, or `ESCALATE`), verify remediations, and stamp `last_reviewed_commit`.

<!-- quality-review-contract: start -->
```yaml
contract: quality-review-v1
mandatory_dispatch: true
completion_order: [verification, present_tense_doc_sync, code_review, quality_review, review_stamp]
blocking_severities: [Critical, Important]
adjudication: [ADOPT, CONTEST, ESCALATE]
report:
  name: QualityReport
  exact_keys: [reviewer, base_commit, head_commit, debloat_source, findings]
  finding_keys: [finding_id, severity, file, symbol, evidence, preserved_invariant, remediation_target, reverification]
```
<!-- quality-review-contract: end -->

## Usage

```text
/flow:review <flow_id> [chapter_id]
```

## Phase 1: Determine Exact Git Range & Match Project Lenses

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), and the target `chapters/<ch_id>/spec.md` + `tasks/*.md` (or all chapters when reviewing the full flow).
2. Determine `base_commit..head_commit` from the parent of the earliest completed task `commit` SHA in the target chapter/flow to `HEAD` (including the pre-review present-tense Markdown/OKF sync commit), and inspect `git diff --stat {base_commit}..{head_commit}`.
3. Match modified file paths against `.agents/skills/index.md` and `.agents/bundles/knowledge/index.md` to attach relevant project-local `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/` (`references/checklist.md` + `references/false-positive-suppressions.md`), and `knowledge/**` chapters.

## Phase 2: Zero-Context Review Dispatch (Zero-Context Isolation Rules)

When dispatching reviewers, strictly enforce the **Zero-Context Isolation Rules**:

1. **Disk-Only Inputs**: Pass only on-disk artifact paths (root `spec.md`, `chapters/index.md`, target `chapters/<ch_id>/spec.md`, `tasks/*.md`, `.agents/skills/`, `knowledge/` chapters, `docs/`) and the exact `base_commit..head_commit` range.
2. **No Rationale Priming**: Never pass conversational history, design rationales, or explanations of *why* code or docs were written a certain way—if code, docstrings, and specs are not self-explanatory to a cold reader, that is a valid finding.
3. **No Leading Focus Hints**: Never instruct the reviewer to ignore areas or pre-excuse trade-offs.
4. **No Pre-Digesting**: Never summarize the diff for the reviewer; let the reviewer inspect `git diff {base_commit}..{head_commit}` and repository files directly.

### Harness Dispatch Modes

- **When `run_workflow` Is Available (Google Antigravity)**:
  - Invoke the packaged [`workflows/flow-dual-review/workflow.py`](../../../workflows/flow-dual-review/workflow.py) workflow (`run_workflow(ScriptPath="<plugin_root>/workflows/flow-dual-review/workflow.py", Args={"git_range": f"{base_commit}..{head_commit}", "spec_path": spec_path, "review_mode": review_mode, "code_reviewer_agent": code_rev_agent, "quality_reviewer_agent": qual_rev_agent})`), which enters `phase("Zero-Context Review")` with `with_budget(timeout=600)` routing to high/extra-thinking Flash by default (or frontier Pro when `--prefer-pro-review` and `>= 25%` Pro quota; automatically falling back without using `flash_lite`):
    - `review_mode="dual"` (default for `Medium`/`Large` flows or `> 2` tasks): runs `@code-reviewer` (`agents/code-reviewer.md`) and `@quality-reviewer` (`agents/quality-reviewer.md`) in `parallel()`, plus any matching `.agents/agents/<domain>-reviewer.md`.
    - `review_mode="single"` (`Small` single-chapter flows with `<= 2` tasks and `<= 150` changed lines): runs one unified zero-context pass returning both `findings` and `QualityReport` (`quality-review-v1`).
  - Verify `git status --porcelain` is unchanged immediately after reviewer completion.
- **In All Other Harnesses**:
  - Dispatch `@code-reviewer` (plus any matching `.agents/agents/<domain>-reviewer`) and `@quality-reviewer` on the primary frontier review model—**`opus`** on Claude Code (preferring next-generation Opus when available, falling back to `sonnet` only when Opus is unavailable or quota-limited; **never** `haiku`) and `model_reasoning_effort = "high"` on Codex—with the same disk-only brief and `base_commit..head_commit` range (or a single unified pass returning `QualityReport` on `Small` `<= 2`-task diffs).

## Phase 3: Review Axes

### Spec Conformance (`@code-reviewer`)

- **Requirement & Edge-Case Coverage**: Every Functional Requirement (`R1..RN`), Concrete Type/Signature Contract, Edge-Case & Failure-Mode Matrix row, and Acceptance Scenario in `spec.md` is implemented and verified.
- **Scope Discipline**: Flag unrequested feature creep, silent contract deviations, or drift between `tasks/<id>-<slug>.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers.
- **Security & Operational Safety**: Flag command injection, unsafe shell interpolation, leaked secrets, or unsafe Git/hook mutations.

### Present-Tense Markdown, Full-Plan Roadmap, & Doc-Sync Conformance (`@code-reviewer`)

- **Spec & Full-Plan Synchronization**: Verify `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` match implemented types, signatures, and behavior in present tense.
- **Downstream Chapter Impact Check**: Flag `Important` / `Critical` if a shared cross-chapter type or signature changed during the chapter without updating root `specs/<flow_id>/spec.md` AND reconciling (or marking `empirical_dependent` for `/flow:revise`) impacted remaining chapters `chK..chNN`.
- **Snapshot & Documentation Manifest Truth**: Verify `## 6. Current State & Remaining Plan Snapshot` accurately states verified baseline + remaining chapters/tasks across the full plan, and verify every `knowledge/**` and `README.md` / `docs/**` file owned by the chapter in `## 3. Documentation & OKF Knowledge Plan` (`[k/N files documented]`) is updated, accurate, and OKF v0.2 compliant (`sources:` + `[^id]:`, `<= 40`-line truth block, frontmatter-free `index.md`).

### Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells (`@code-reviewer` + `<domain>-reviewer`)

Documented repository standards (`AGENTS.md`, `product/tech-stack.md`, `knowledge/patterns/`, `.agents/skills/<domain>/`, and `.agents/skills/review-<domain>/references/checklist.md`) always take precedence; when an area is not covered by a repo-specific rule, evaluate **Deep-Module Design** and **Baseline Structural Code Smells**:

1. **Deep-Module Seam & Dependency Category Audit**:
   - Flag shallow pass-through modules, 1:1 interface wrappers with only one implementation (*"one adapter = hypothetical seam"*), or mock-heavy tests that violate the dependency categories (`In-process`, `Local-substitutable`, `Remote-owned (Ports & Adapters)`, `External boundary`).
2. **Baseline Structural Code Smells**:
   - *Long Function*, *Large Class / Module*, *Long Parameter List*, *Divergent Change* (one module changed for multiple unrelated reasons), *Shotgun Surgery* (one logical change scattered across many modules), *Feature Envy* (a function more interested in another class's state than its own), *Data Clumps* (the same parameter group passed together everywhere instead of a value object/`msgspec.Struct`), *Primitive Obsession*, *Repeated Switches / Conditionals*, *Loops Instead of Pipelines*, *Speculative Generality* (unused hooks/params added "just in case"), and *Message Chains* (deep `a.b().c().d()` chains).
3. **False-Positive Suppressions**:
   - Suppress every project-verified safe pattern listed in `.agents/skills/review-*/references/false-positive-suppressions.md` (`FP-<PREFIX>-NN`).

### Mandatory Quality, Zero-History Doc Hygiene, & Debloat Review (`@quality-reviewer` — `quality-review-v1`)

- **Semantic Surface & Code Organization**: Flag dead code, pass-through wrappers failing the deletion test, standalone private `_...` module helpers that belong on their domain class, unnecessary function-scoped imports, inline `#` restatement comments in Python, and leftover compatibility shims.
- **Test & Gate Strength**: Flag Implementation-Coupled tests, Tautological (mock-echo) tests, horizontal-slicing tests, and standalone `test_*remediation*.py` / `test_*audit*.py` files.
- **Zero-History Living-Doc & OKF Hygiene**: Flag `Revision History` / `Changelog` / `Change History` headings, chronological narrative (`"in chapter 1 we..."`, `"previously..."`), struck-through obsolete checklist items (`- [ ] ~~...~~`), standalone `---` horizontal rules in Markdown bodies, numbered buzzwords, AI puffery, and leaked internal ceremony across `specs/**`, `knowledge/**`, `README.md`, and `docs/**`.

## Phase 4: Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`) & Waiver Rules

Evaluate every finding against the actual repository code, living docs, and `.agents/skills/review-*/references/false-positive-suppressions.md`:

- **`ADOPT`**:
  - Fix valid `Critical` or `Important` correctness, seam, SUT integrity, Markdown/OKF sync, or debloat findings in canonical production/test/doc/spec files (rewriting specs and docs in place in present tense), rerun verification gates (`exit 0`), and re-verify with the reviewer on the updated `base_commit..head_commit` range.
- **`CONTEST`**:
  - Reject false positives, suggestions that violate `false-positive-suppressions.md`, or out-of-scope feature creep by citing exact `path/to/file::Symbol` evidence or the matching `FP-<PREFIX>-NN` rule in the Adjudication Ledger.
- **`ESCALATE`**:
  - When a reviewer finding exposes a genuine requirement trade-off or user-visible behavior choice, pause and present the options to the user via `structured-choice-v1` ([`interaction.md`](interaction.md)).
- **Finding-Specific Waiver Rule**:
  - Dispatch of `@code-reviewer` and `@quality-reviewer` is mandatory and cannot be waived. If the user chooses to waive a specific blocking finding, record `waived_by: user`, `finding_id`, and `reason` in the Adjudication Ledger and `.agents/bundles/log.md`.

## Phase 5: Stamp `last_reviewed_commit`, Present Ledger, & Handoff

1. Let `<REVIEWED_HEAD_SHA>` be the verified `HEAD` commit SHA that passed review. Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` and `verified:` in the reviewed `chapters/<ch_id>/spec.md` and/or root `specs/<flow_id>/spec.md` (advancing `last_reviewed_chapter` and `current_chapter` when closing a chapter) and create a signed metadata commit if updated.
2. Present the **Review & Adjudication Report** (`Range`, `Review Findings`, `QualityReport`, `last_reviewed_commit`, and `Adjudication Ledger: Finding ID | Axis | Severity | Verdict (ADOPT/CONTEST/ESCALATE) | Evidence / Commit`), prepend a `review` entry to `.agents/bundles/log.md`, and hand off to the next chapter (`/flow:implement <flow_id>`) or `/flow:finish <flow_id>`.
