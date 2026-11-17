# Flow Review (`/flow:review`)

Run independent reviews across a chapter's or flow's Git range (`base_commit..head_commit`) along four axes: **Spec Conformance**, **Markdown & Doc-Sync Conformance**, **Repository Standards & Structural Code Smells**, and **Quality & Debloat**.
Decide on each finding (`ADOPT`, `CONTEST`, or `ESCALATE`), verify fixes, and stamp `last_reviewed_commit`.

<!-- quality-review-contract: start -->
```yaml
mandatory_dispatch: true
completion_order: [verification, present_tense_doc_sync, code_review, quality_review, review_stamp]
blocking_severities: [Critical, Important]
decisions: [ADOPT, CONTEST, ESCALATE]
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

## Phase 1: Determine Git Range & Project Lenses

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), and the target `chapters/<ch_id>/spec.md` + `tasks/*.md` (or all chapters for a full-flow review).
2. Determine `base_commit..head_commit` from the parent of the earliest completed task `commit` SHA in the target chapter or flow to `HEAD` (including the pre-review Markdown/OKF sync commit), and run `git diff --stat {base_commit}..{head_commit}`.
3. Match modified file paths against `.agents/skills/index.md` and `.agents/bundles/knowledge/index.md` to attach relevant `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/` (`references/checklist.md` + `references/false-positive-suppressions.md`), and `knowledge/**` chapters.

## Phase 2: Independent Review Isolation Rules

When dispatching reviewers, enforce these isolation rules:

1. **Disk-Only Inputs**: Pass only on-disk paths (root `spec.md`, `chapters/index.md`, target `chapters/<ch_id>/spec.md`, `tasks/*.md`, `.agents/skills/`, `knowledge/` chapters, `docs/`) and the `base_commit..head_commit` range.
2. **No Rationale Priming**: Never pass conversation history or explanations of *why* code or docs were written a certain way—if code, docstrings, and specs are unclear to a first-time reader, that is a valid finding.
3. **No Leading Focus Hints**: Never instruct the reviewer to ignore areas or pre-excuse trade-offs.
4. **No Pre-Digesting**: Never summarize the diff; let the reviewer inspect `git diff {base_commit}..{head_commit}` and repo files directly.

### Harness Dispatch Modes

- **When `run_workflow` Is Available (Google Antigravity)**:
  - Invoke [`workflows/flow-dual-review/workflow.py`](../../../workflows/flow-dual-review/workflow.py) (`run_workflow(ScriptPath="<plugin_root>/workflows/flow-dual-review/workflow.py", Args={"git_range": f"{base_commit}..{head_commit}", "spec_path": spec_path, "review_mode": review_mode})`), which plans review seats via `ReviewRoster` (`flow-cli.mjs review plan`) across routed models ([`orchestration.md`](orchestration.md)).
  - Verify `git status --porcelain` is unchanged right after reviewer completion.
- **In All Other Harnesses**:
  - Dispatch `@code-reviewer` (plus any matching `.agents/agents/<domain>-reviewer`) and `@quality-reviewer` (or different-vendor `adversarial` seats planned via `ReviewRoster`) with the same disk-only brief and `base_commit..head_commit` range ([`orchestration.md`](orchestration.md)).

## Phase 3: Review Axes

### Spec Conformance (`@code-reviewer`)

- **Requirement & Edge-Case Coverage**: Every Functional Requirement (`R1..RN`), type/signature contract, edge-case matrix row, and acceptance scenario in `spec.md` is implemented and verified.
- **Scope Discipline**: Flag unrequested feature creep, silent contract deviations, or drift between `tasks/<id>-<slug>.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers.
- **Security & Operational Safety**: Flag command injection, unsafe shell interpolation, leaked secrets, or unsafe Git/hook mutations.

### Markdown, Roadmap & Doc-Sync Conformance (`@code-reviewer`)

- **Spec & Roadmap Sync**: Verify `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` match implemented types, signatures, and behavior in present tense.
- **Downstream Chapter Impact Check**: Flag `Important` or `Critical` if a shared cross-chapter type or signature changed without updating root `specs/<flow_id>/spec.md` and syncing (or marking `empirical_dependent` for `/flow:revise`) impacted chapters `chK..chNN`.
- **Snapshot & Documentation Truth**: Verify `## 6. Current State & Remaining Plan Snapshot` matches current reality and remaining work, and every `knowledge/**` and `README.md` / `docs/**` file in `## 3. Documentation & OKF Knowledge Plan` (`[k/N files documented]`) is updated and OKF v0.2 compliant.

### Repository Standards & Structural Code Smells (`@code-reviewer`)

Documented repository standards (`AGENTS.md`, `product/tech-stack.md`, `knowledge/patterns/`, `.agents/skills/<domain>/`, and `.agents/skills/review-<domain>/references/checklist.md`) always take precedence.
Where no repo-specific rule applies, evaluate **Deep Module Design** and **Structural Code Smells**:

1. **Deep Module Interface & Dependency Audit**:
   - Flag shallow pass-through modules, 1:1 interface wrappers with one implementation (*"one adapter = hypothetical interface"*), or mock-heavy tests violating the dependency categories (`In-process`, local test double, `Remote-owned`, `External boundary`).
2. **Structural Code Smells**:
   - *Long Function*, *Large Class / Module*, *Long Parameter List*, *Divergent Change*, *Shotgun Surgery*, *Feature Envy*, *Data Clumps*, *Primitive Obsession*, *Repeated Switches / Conditionals*, *Loops Instead of Pipelines*, *Speculative Generality*, and *Message Chains* (deep `a.b().c().d()` chains).
3. **False-Positive Suppressions**:
   - Suppress every verified safe pattern listed in `.agents/skills/review-*/references/false-positive-suppressions.md` (`FP-<PREFIX>-NN`).

### Quality, Doc Hygiene & Debloat (`@quality-reviewer`)

- **Semantic Surface & Code Organization**: Flag dead code, pass-through wrappers failing the deletion test, and standalone `_...` helpers that belong on their domain class. Also flag unnecessary function-scoped imports, inline `#` restatement comments in Python, and leftover compatibility shims.
- **Test & Check Strength**: Flag private-detail tests, mock-only tests, layer-by-layer tests without end-to-end behavior checks, and standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Current-State Doc & OKF Hygiene**: Flag `Revision History` / `Changelog` / `Change History` headings, chronological narrative (`"in chapter 1 we..."`), struck-through checklist items (`- [ ] ~~...~~`), standalone `---` body rules, numbered buzzwords, filler prose, and leaked internal ceremony.

## Phase 4: Decide on Findings & Waivers

Evaluate every finding against the repository code, docs, and `.agents/skills/review-*/references/false-positive-suppressions.md`:

- **`ADOPT`**:
  - Fix valid `Critical` or `Important` correctness, interface, real-code test, Markdown/OKF sync, or debloat findings in canonical files (rewriting specs and docs in place in present tense). Rerun checks (`exit 0`) and re-verify on the updated `base_commit..head_commit` range.
- **`CONTEST`**:
  - Reject false positives, suggestions violating `false-positive-suppressions.md`, or out-of-scope creep by citing `path/to/file::Symbol` evidence or the matching `FP-<PREFIX>-NN` rule in the review summary.
- **`ESCALATE`**:
  - When a finding exposes a genuine requirement trade-off or user-visible behavior choice, pause and present options via [`interaction.md`](interaction.md).
- **Finding-Specific Waiver Rule**:
  - Dispatching `@code-reviewer` and `@quality-reviewer` is mandatory and cannot be waived. If the user waives a specific blocking finding, record `waived_by: user`, `finding_id`, and `reason` in the review summary and `.agents/bundles/log.md`.

## Phase 5: Stamp `last_reviewed_commit` & Handoff

1. Let `<REVIEWED_HEAD_SHA>` be the verified `HEAD` commit SHA that passed review.
2. Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` and `verified:` in the reviewed `chapters/<ch_id>/spec.md` and/or root `specs/<flow_id>/spec.md` (advancing `last_reviewed_chapter` and `current_chapter` when closing a chapter) and create a signed metadata commit if updated.
3. Present the **Review Summary** (`Range`, `Review Findings`, `QualityReport`, `last_reviewed_commit`, and table `Finding ID | Axis | Severity | Verdict (ADOPT/CONTEST/ESCALATE) | Evidence / Commit`).
4. Prepend a `review` entry to `.agents/bundles/log.md` and hand off to the next chapter (`/flow:implement <flow_id>`) or `/flow:finish <flow_id>`.
