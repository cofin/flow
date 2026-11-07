# Flow Spec (`/flow:spec`, alias `/flow:plan`)

Co-design a decision-complete **Feature Specification** (`.agents/bundles/specs/<flow_id>/spec.md`), decompose work exceeding `4` tasks or crossing `>= 2` module boundaries into nested context-bounded **Chapter Specifications** (`specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/spec.md`, `1–4` tasks per chapter, zero upper cap on chapter count), author **all 8-section Task Blueprints upfront in parallel** (`tasks/<id>-<slug>.md`), pressure-test every chapter with **Zero-Context Verification**, and adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`) before stamping `status: stable` and `plan_commit: <HEAD_SHA>`.

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for Design-Tree Frontier decisions and [`state.md`](state.md) for OKF v0.2 Markdown schemas. **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during throwaway prototypes); never modify application source code during `/flow:spec`.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, frontier_discovery, draft, gap_scan, zero_context_review, adjudication, approved, revise, refine, blocked]
  gap_scan:
    reject:
      - deferred_research
      - unresolved_decisions
      - stub_body
      - truncated_or_compressed_scope
      - oversized_chapter
      - oversized_task
      - missing_concrete_signatures
      - missing_call_site_map
      - missing_edge_case_matrix
      - missing_worked_test_matrix
      - missing_documentation_and_okf_plan
      - missing_okf_provenance
      - missing_bounded_read_manifest
      - vague_verification
      - missing_verification_strategy
      - overlapping_ownership
      - fragile_line_numbers
      - shallow_passthrough_seam
      - stale_or_historical_plan_prose
    require:
      - problem_framing
      - alternatives_considered
      - deep_module_seams
      - concrete_type_and_signature_contracts
      - caller_seam_collaborator_map
      - edge_case_and_failure_matrix
      - documentation_and_okf_plan
      - requirement_to_task_traceability
      - symbol_anchored_targets
      - bounded_read_set
      - worked_public_seam_tests
      - one_invocation_per_task
      - one_commit_per_task
  revision_update:
    on_plan_change:
      - rewrite_chapter_and_root_roadmap_in_present_tense
      - sync_chapters_index
      - increment_plan_revision_once
      - sync_revision_to_spec_and_tasks
      - reanchor_plan_commit
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    adjudication: [ADOPT, CONTEST, ESCALATE]
```

## Phase 1: Bundle Grounding & Sharded Read-Only Scouts (`Facts First`, `< 25k` Coordinator Tokens)

1. **Read Bundle Catalogs, Domain Glossary, & Skills**: Read `.agents/bundles/index.md`, `knowledge/workflow.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, `knowledge/testing/**`, `knowledge/gotchas/**`, `.agents/skills/index.md`, and any parent spec (`parent_prd` or `parent_flow`).
2. **Sharded Read-Only Scouts (`SubsystemDigest`)**:
   - Keep the coordinator thin (`< 25k` exploration tokens). Only read source files directly when the entire request touches `<= 2` files inside a single module.
   - Whenever the request touches `> 2` source files or crosses `>= 2` modules/packages, dispatch **parallel read-only Scout subagents** (`1` per subsystem; on Google Antigravity use `run_workflow` `parallel()` with `agent(..., type_name="self", model="inherit")` and `agents/researcher.md`, then verify `git status --porcelain` is unchanged; on Claude Code / Codex / Cursor / OpenCode / VS Code invoke `@researcher` in parallel).
   - Each Scout returns a structured **`SubsystemDigest`**: `symbols` (`path/to/file::Symbol`), `exact_signatures`, `seams_and_dependency_categories`, `canonical_tests_and_fixtures`, `edge_cases_and_gotchas`, `affected_docs_and_okf_chapters`, and `open_design_forks`.
3. **Classify Dependency Boundaries (Deep-Module Dependency Model)**:
   - **In-process** (pure computation / in-memory state — merge into a deep module and test directly).
   - **Local-substitutable** (local test stand-in like SQLite or in-memory FS — keep seam internal and test with stand-in).
   - **Remote-owned (Ports & Adapters)** (define a port at the seam; use HTTP/RPC adapter in production and in-memory adapter in tests).
   - **External boundary (Mock)** (third-party API/clock — inject port and mock only at the external boundary).
4. **Primary-Source Research & Throwaway Prototyping**:
   - For external SDK/protocol questions or multi-domain unknowns, promote validated Scout/`@researcher` findings into OKF v0.2 `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` documents with `sources:` and `[^id]:` body footnotes ([`research.md`](research.md)).
   - When a state model or UI interaction is uncertain on paper, run a throwaway prototype in untracked `.agents/scratch/<slug>/`, fold the validated decision into `spec.md`, and delete `.agents/scratch/<slug>/`.

## Phase 2: Design-Tree Frontier Discovery, Interface Comparison, & Chapter Decomposition (`structured-choice-v1`)

1. Present the concise **Code Analysis & Seam Summary** (`Area | Files Examined (path/to/file::Symbol) | Public Seam & Dependency Category | Affected Docs / OKF Chapters`).
2. **Active Domain Modeling & Edge-Case Probing**: Challenge fuzzy or overloaded nouns against `knowledge/domains/<domain>.md` and probe concrete boundary interactions (*"What happens when X fails mid-batch while Y is already committed?"*).
3. **Compare Interface Alternatives (For Non-Trivial Interfaces)**:
   - Compare at least 2–3 distinct interface shapes (such as *minimal entry-point hiding full workflow*, *configurable policy struct*, or *caller-optimized adapter*) on **depth**, **locality**, and **seam placement**.
   - **Seam Rule**: One adapter means hypothetical indirection; two concrete callers/adapters (such as production + in-memory test double) justify a port/seam.
4. **Walk the Frontier & Satisfy the Pre-Draft Question Coverage Gate (`structured-choice-v1`)**:
   - Ask `1` question at dependent design forks and batch `2–3` orthogonal leaf questions per call once on a settled frontier ([`interaction.md`](interaction.md)), placing `<Label> (Recommended)` first.
   - Before drafting, resolve all five Pre-Draft Question Coverage Gate areas: (1) Deep-Module Seam & Interface Alternative Selection, (2) Concrete Data/Type Contracts & Edge-Case/Failure Semantics, (3) Public Seams & Canonical Test Strategy, (4) Documentation (`README.md` / `docs/**`) & OKF Knowledge Scope, and (5) Full Chapter Decomposition (`1–4` tasks in a single-chapter spec, or `ch01-<slug>..chNN-<slug>` with `1–4` tasks per chapter and zero scope truncation).
   - **Anti-Truncation Rule**: Never compress multiple capabilities into a vague task, drop edge cases, or omit documentation/OKF updates to stay under `4` tasks. Whenever work requires `> 4` tasks or spans `>= 2` module boundaries, expand into nested `chapters/ch01-<slug>/..chNN-<slug>/` (including dedicated documentation/OKF synthesis tasks or chapters) with **zero upper ceiling on chapter count**.

## Phase 3: Author OKF v0.2 Specifications & Upfront Parallel Chapter Blueprints

### 3.1 Single-Chapter vs. Multi-Chapter Layout (`specs/<flow_id>/`)

- **Single-Chapter Flow (`1–4` vertical-slice tasks within one subsystem)**:
  - Write `specs/<flow_id>/spec.md` (`has_chapters: false`) and `specs/<flow_id>/tasks/t01-<slug>.md..t04-<slug>.md`.
- **Multi-Chapter Flow (`> 4` tasks or `>= 2` module boundaries — `ch01..chNN`, zero upper cap)**:
  1. Coordinator writes root `specs/<flow_id>/spec.md` (`has_chapters: true`, `current_chapter: ch01-<slug>`, `chapters: [ch01-<slug>, ...]`) locking cross-chapter public types/signatures, shared invariants, Flow-Wide Documentation & OKF Knowledge Plan (`[0/N files documented]`), and the full chapter checklist, plus frontmatter-free `specs/<flow_id>/chapters/index.md`.
  2. Coordinator fans out **1 isolated Chapter Planner subagent per chapter in parallel** (`run_workflow` `parallel()` with `agent(..., type_name="self", model="inherit")` and `agents/plan-generator.md` on Google Antigravity; parallel `@plan-generator` subagents on other harnesses).
  3. Each Chapter Planner subagent reads root `specs/<flow_id>/spec.md`, its scoped `SubsystemDigest` / `research/*.md`, and its `<= 6` target files, and writes `specs/<flow_id>/chapters/<ch_id>/spec.md` plus `specs/<flow_id>/chapters/<ch_id>/tasks/t01-<slug>.md..t04-<slug>.md` **upfront in full detail**.
  4. Only when a later chapter's exact thresholds or schema genuinely depend on runtime output from executing an upstream chapter, set `planning_status: empirical_dependent`, `depends_on_chapters: [ch01-<slug>]`, and `replan_trigger: "<exact runtime artifact/measurement needed>"` while still authoring full requirements, edge cases, documentation targets, and provisional worksheets upfront.

### 3.2 Specification Body Contract (`spec.md` — OKF v0.2, Zero Body `---`)

Write root and chapter `spec.md` files with the normative OKF v0.2 frontmatter from [`state.md`](state.md) (`status: draft` until approved, `state: planned`, `sources:` with matching `[^id]:` footnotes, `tags:`, `generated:`), a `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` summary block, and all 6 present-tense sections (never using standalone `---` horizontal rules in the Markdown body):

```markdown
# Flow: <Title>

<!-- truth: start -->
- **Canonical Seam**: `src/module.py::ServiceClass` [^seam-1]
- **Invariants**: ...
<!-- truth: end -->

## 1. Specification, Context & Provenance

### 1.1 Problem Statement & Objectives
- Plain-English problem statement, current limits, why this design succeeds, and explicit Non-Goals.

### 1.2 Upstream Execution Baseline
- Branch, `parent_flow` / `depends_on_chapters` (if chaptered), and prerequisite commits.

### 1.3 Code Analysis & Seam Summary
| Area | Files Examined (`path/to/file::Symbol`) | Public Seam, Dependency Category & Integration |
| --- | --- | --- |
| ... | `src/module.py::ClassName` [^seam-1] | ... |

### 1.4 Relevant OKF Knowledge Chapters & Skills
- Links to applicable `.agents/bundles/knowledge/**` chapters and `.agents/skills/<domain>/SKILL.md`.

## 2. Requirements, Concrete Contracts & Architecture

### 2.1 Functional Requirements
- **R1**: ...

### 2.2 Full Public Type, Struct, Schema & Signature Contracts
- Exact public class/struct definitions, fields, method/function signatures, parameter types, return types, and invariants.

### 2.3 Caller -> Seam -> Collaborator Integration Map
- Exact call-site wiring showing how callers invoke the public seam and how collaborators/ports connect.

### 2.4 Non-Functional Constraints & Edge-Case / Failure-Mode Matrix
| Scenario / Boundary | Trigger / Input | Expected Behavior / Error Contract | Invariant Preserved |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

### 2.5 Acceptance Scenarios (Given / When / Then)
- Concrete happy-path and failure-mode scenarios at the confirmed public seam.

### 2.6 Alternatives Considered
- Mandatory comparison of rejected interface/architectural designs (contrasted by depth, locality, and seam placement) and why the chosen design won.

## 3. Documentation & OKF Knowledge Plan

- **Progress**: `[0/N files documented]`
- `[ ]` `docs/guide/<topic>.md` — User-facing guide and code examples for `<Symbol>`.
- `[ ]` `.agents/bundles/knowledge/architecture/<topic>.md` — Present-tense OKF v0.2 architecture chapter with `sources:` citations.

## 4. Requirement-to-Task Traceability Matrix

| Requirement / Doc Target | Owning Chapter / Task | Verification Strategy | Canonical Test / Doc Gate |
| --- | --- | --- | --- |
| R1 | `ch01 / t01` | `behavior_tdd` | `tests/unit/test_module.py::test_behavior` |

## 5. Implementation Plan

- [ ] ch01-core-seam — <Chapter Summary> (chapters/ch01-core-seam/spec.md)
- [ ] ch02-docs-and-okf — <Chapter Summary> (chapters/ch02-docs-and-okf/spec.md)
- **Chapter / Phase Recovery Checkpoint**: `<exact lint + chapter test command>`

## 6. Current State & Remaining Plan Snapshot

- **Verified Baseline (`HEAD`)**: `<sha>` — Initial plan authored; `0/2` chapters completed.
- **Active Chapter**: `ch01-core-seam` (`0/3` tasks completed).
- **Remaining Plan**: `ch01-core-seam`, `ch02-docs-and-okf`.
- **Documentation & OKF Sync**: `[0/2 files documented]`.
- **Active Invariants & Triggers**: ...

[^seam-1]: `src/module.py::ClassName` — Existing service boundary inspected during planning.
```

### 3.3 8-Section Task Blueprints (`tasks/<id>-<slug>.md`) — The Zero-Decision Rule

Every task worksheet (`1–3` production files, `read_set <= 6` files, `estimated_loc <= 250`) follows [`state.md`](state.md) with all 8 required headings:

1. `## Objective & Scope Boundary` — Exact vertical-slice outcome (production code + canonical public-seam tests, or manifest-driven docs/OKF synthesis) and explicit out-of-scope boundaries.
2. `## Bounded Read Manifest` — The `<= 6` exact `path/to/file::Symbol` and OKF files the isolated executor needs to read (zero broad repository exploration).
3. `## Symbol & Signature Contracts` — Exact struct/class fields, function/method signatures, types, and `Caller -> Seam -> Collaborator` call-site wiring.
4. `## Edge Cases & Error Semantics` — Concrete boundary inputs (empty, null, malformed, concurrency, timeout, permission) and exact exception or error return contracts.
5. `## Public-Seam Test Blueprint` — Canonical module test file path, dependency category, and a non-tautological **Worked Test Matrix** (`Case | Concrete Input | Expected Output / Error`) with literal values (never standalone `test_*remediation*.py` or `test_*audit*.py` files; for `documentation_validation`, specify link, frontmatter, and example-execution checks).
6. `## Verification` — Exact initial (Red/baseline) and final (Green + lint/typecheck) CLI commands.
7. `## Acceptance Criteria` — Checkboxes (`- [ ]`) mapped to parent requirements and documentation targets.
8. `## Notes & Discoveries` — Concise implementation findings (`- [YYYY-MM-DD HH:MM] ...`).

## Phase 4: Per-Chapter Zero-Context Spec Verification & Subagent Adjudication

Before presenting the plan for user approval, run the **Zero-Context Spec Review Loop** ([`../../../templates/agent/spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)):

1. **Enforce Zero-Context Isolation Rules**:
   - Confirm `git status --porcelain` shows zero uncommitted edits to production source files.
   - Always dispatch fresh isolated subagents (`model: inherit`)—never roleplay the reviewer in-place inside the coordinator session.
   - Pass **only on-disk repository paths** (root `spec.md`, `chapters/index.md`, target `chapters/<ch_id>/spec.md`, `tasks/*.md`, matching `.agents/skills/`, and `knowledge/` chapters)—never chat summaries or oral rationale. (If the user asks for a copyable prompt for a separate window, emit the verbatim prompt wrapped in five backticks `````` ````` ``````.)
2. **Parallel Per-Chapter & Cross-Chapter Review Dispatch**:
   - For multi-chapter plans, fan out **1 isolated Zero-Context Spec Reviewer per chapter** plus **1 Cross-Chapter Seam, Anti-Truncation & OKF Reviewer** in parallel (on Google Antigravity use `run_workflow` `parallel()` with `agent(..., type_name="self", schema=SPEC_REVIEW_SCHEMA, model="inherit")` and `agents/code-reviewer.md`, then verify `git status --porcelain` reveals no unexpected writes; on other harnesses invoke `@code-reviewer` / `<domain>-reviewer` in parallel).
   - Reviewers audit five lenses: **Cold-Reader Comprehension**, **Architectural & Deep-Module Seam Review**, **Anti-Truncation & 8-Section Blueprint Readiness**, **Documentation & OKF v0.2 Conformance**, and **Present-Tense Prose Debloat**.
3. **Subagent Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - **`ADOPT`**: Dispatch isolated per-chapter revision subagents (`@plan-generator`; `type_name="self"` on Antigravity) to rewrite affected `chapters/<ch_id>/{spec.md,tasks/*.md}` AND synchronize root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense ([`revise.md`](revise.md)), increment `plan_revision` once across all specs and tasks, and re-verify changed chapters (up to 3 rounds).
   - **`CONTEST`**: Reject false positives, over-engineering, or out-of-scope suggestions by recording exact `path/to/file::Symbol` evidence or `FP-*` suppression rules in the Adjudication Ledger.
   - **`ESCALATE`**: Surface genuine unresolved product trade-offs to the user via `structured-choice-v1`.

## Phase 5: Approval Gate (`Approve | Revise | Refine`) & Plan Lock

1. Present the planning summary, full Chapter & Task Blueprint table (`Chapter | Task ID | Strategy | Read Set / Owned Files & Canonical Tests`), `[0/N files documented]` manifest, and Review Adjudication Ledger, followed by the `Approve | Revise | Refine` gate (`structured-choice-v1` in [`interaction.md`](interaction.md)).
2. When approved, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across root `spec.md`, every `chapters/<ch_id>/spec.md`, and every `tasks/<id>-<slug>.md`, update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off to `/flow:implement <flow_id>` (which executes one chapter per run).
