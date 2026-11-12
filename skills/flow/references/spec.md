# Flow Spec (`/flow:spec`, alias `/flow:plan`)

Co-design a decision-complete **Feature Specification** (`.agents/bundles/specs/<flow_id>/spec.md`), scale layout and orchestration to change size (`Small`, `Medium`, `Large`) without truncating engineering or documentation scope, validate OKF v0.2 schema compliance deterministically on write, verify blueprints with **Zero-Context Verification** (`1` combined reviewer by default for `<= 4` chapters), and adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`) before stamping `status: stable` and `plan_commit: <HEAD_SHA>`.

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for Design-Tree Frontier decisions, [`state.md`](state.md) and [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md) for OKF v0.2 schemas, and [`../../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md`](../../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md) for model routing and `run_workflow` rules. **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or primary-checkout `.agents/bundles/` inside `local-only` git worktrees); never modify application source code during `/flow:spec`.

## Proportional Planning Tiers (`Small` | `Medium` | `Large`)

Choose the tier from estimated production LOC and impacted modules:

| Tier | Trigger | Scouting | Layout | Worksheet | Planners | Review |
| --- | --- | --- | --- | --- | --- | --- |
| **Small** | `<= 400` LOC, `1` module | Coordinator direct read (`<= 8` files) | Single-chapter `spec.md` (`1..4` tasks) | Compact (`worksheet_format: compact`) | Coordinator only | `1` combined reviewer (`1` round) |
| **Medium** | `<= 1,500` LOC or `<= 3` modules | Direct read (`<= 8` files) or `flow-scout` | Chapters (`<= 4`) + `chapters/index.md` | Full (`worksheet_format: full`) | `flow-spec-planning` (`single_batch` for `<= 3` ch; parallel for `4`) | `1` combined reviewer (`2nd` round only on adopted blocking findings) |
| **Large** | `> 1,500` LOC, `> 3` modules, `> 4` chapters, or `/flow:prd` | `flow-scout` parallel digests | Chapters (`2..N`, zero cap) + `chapters/index.md` | Full (`worksheet_format: full`) | `flow-spec-planning` (`per_chapter` parallel) | Per-chapter + cross-chapter reviewers |

- **Anti-Truncation Rule**: Tiers scale document ceremony and subagent count, never engineering scope. Every requirement, concrete contract, edge case, and documentation/OKF target maps to a task and verification surface; whenever work exceeds `4` tasks or crosses module boundaries, expand into nested `chapters/ch01-<slug>/..chNN-<slug>/` with zero upper cap on chapter count.

## Phase 1: Bundle Grounding & Right-Sized Scouting (`Facts First`)

1. **Read Bundle Catalogs & Domain Glossary**: Read `.agents/bundles/index.md`, `knowledge/workflow.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, `knowledge/testing/**`, `knowledge/gotchas/**`, `.agents/skills/index.md`, and any parent spec.
2. **Direct Read vs. Shipped `flow-scout` Workflow**:
   - When the request touches `<= 8` files across `<= 2` modules, inspect those files directly in the coordinator (`< 15k` tokens) with zero scout subagent overhead.
   - When touching `> 8` files or `>= 3` subsystems:
     - **Google Antigravity**: Call the shipped scout workflow (`type_name="self"`, `model="flash"`—restricting `flash_lite` strictly to `narrow_fetch: true` items with `<= 3` paths):
       `run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [{"name": "auth", "paths": ["src/auth/"]}]})`
     - **Other Harnesses**: Invoke `@researcher` in parallel (`model: "sonnet"` on Claude Code; restrict `"haiku"` strictly to narrow `<= 3`-file fetches).
3. **Classify Dependency Boundaries**: Classify collaborators into **In-process**, **Local-substitutable**, **Remote-owned (Ports & Adapters)**, and **External boundary (Mock)**. Promote external SDK/multi-domain research to OKF v0.2 `specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` ([`research.md`](research.md)).

## Phase 2: Design-Tree Frontier Discovery & Interface Comparison (`structured-choice-v1`)

1. Present the **Code Analysis & Seam Summary** (`Area | Files Examined (path/to/file::Symbol) | Public Seam & Dependency Category | Affected Docs / OKF Chapters`).
2. **Compare Interface Alternatives**: Compare at least 2–3 distinct interface shapes on **depth**, **locality**, and **seam placement** (*one adapter = hypothetical seam; two concrete callers/adapters = real seam*).
3. **Walk the Frontier & Satisfy the Pre-Draft Question Coverage Gate (`structured-choice-v1`)**:
   - Ask `1` question at dependent forks and batch `2–3` orthogonal leaf questions once on a settled frontier ([`interaction.md`](interaction.md)), placing `<Label> (Recommended)` first across seam selection, concrete data/error contracts, public-seam test strategy, fast (`< 60s`) lint + targeted unit file checkpoints, `docs/**` + OKF targets, and tier/chapter decomposition.

## Phase 3: Author OKF v0.2 Specifications, Schema-Card Blueprints, & Write-Time Validation

### 3.1 Single-Chapter (`Small`) vs. Shipped `flow-spec-planning` (`Medium` / `Large`)

- **`Small` Single-Chapter Flow (`<= 400` LOC, `1` module, `1..4` tasks)**:
  - Coordinator writes `specs/<flow_id>/spec.md` (`has_chapters: false`) and `specs/<flow_id>/tasks/t01-<slug>.md..t04-<slug>.md` (`worksheet_format: compact`) directly following [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), then runs `/flow:validate` (`exit 0`).
- **`Medium` & `Large` Multi-Chapter Flows**:
  1. Coordinator writes root `specs/<flow_id>/spec.md` (`has_chapters: true`, `current_chapter: ch01-<slug>`, `chapters: [...]`) and frontmatter-free `specs/<flow_id>/chapters/index.md`.
  2. **Google Antigravity**: Call the shipped planning workflow (never hand-write orchestration scripts):
     `run_workflow(ScriptPath="<plugin_root>/workflows/flow-spec-planning/workflow.py", Args={"flow_id": "<flow_id>", "chapters": [{"id": "ch01-core", "brief": "...", "read_files": ["src/core.py"]}], "review": "single"})`
     - `flow-spec-planning` passes [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md) (`type_name="self"`), writes `chapters/<id>/planner-notes.md` on disk before returning, recovers stalled planners automatically once all chapter files sit idle on disk, runs deterministic OKF validation, flags `planning_quality: degraded` whenever quota fallback prevented planning on the primary frontier thinking model, and runs Zero-Context Review when `root_spec_issues` is empty.
     - **Manual Fallback Rule**: If a background workflow has written every chapter's `spec.md`, `tasks/*.md`, and `planner-notes.md` on disk and makes no progress for `10` minutes, cancel the workflow and continue from the files on disk, folding every `planner-notes.md` `Root Spec Issues` entry into root `spec.md` before review.
  3. **Other Harnesses**: Dispatch `1` batch `@plan-generator` (`Medium` `<= 3` chapters) or parallel `@plan-generator` subagents (`Large`) on the primary frontier thinking model (`inherit` / Opus family / `high`), passing only root `spec.md`, [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and scoped chapter files, then fold `planner-notes.md` issues into root `spec.md` and run `/flow:validate` (`exit 0`).

### 3.2 Specification Body (`spec.md`) & Task Worksheet Contracts

Follow [`state.md`](state.md) and [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md):

- **6 Required `spec.md` Sections** (preceded by a `<= 40`-line `<!-- truth: start -->` block, with `sources:` + `[^id]:` footnotes and zero standalone `---` body rules):
  1. `## 1. Specification, Context & Provenance` — Including `### 1.1 Problem Statement & Objectives`, `### 1.2 Upstream Execution Baseline`, `### 1.3 Code Analysis & Seam Summary`, and `### 1.4 Relevant OKF Knowledge Chapters & Skills`.
  2. `## 2. Requirements, Concrete Contracts & Architecture` — `R1..RN`, concrete public types/signatures, `Caller -> Seam -> Collaborator` map, Edge-Case & Failure-Mode Matrix, Acceptance Scenarios, and Alternatives Considered.
  3. `## 3. Documentation & OKF Knowledge Plan` (`[0/N files documented]`).
  4. `## 4. Requirement-to-Task Traceability Matrix`.
  5. `## 5. Implementation Plan` — Checklist + fast (`< 60s`) **Chapter / Phase Recovery Checkpoint** (`make lint` + targeted unit test file, never a slow `> 60s` full test suite).
  6. `## 6. Current State & Remaining Plan Snapshot`.
- **Task Worksheets (`tasks/<id>-<slug>.md`)**: Reference shared structs/signatures defined in `spec.md` instead of copy-pasting duplicate blocks; use the 6 `compact` headings on `Small` specs and the 8 `full` headings on `Medium`/`Large` specs.

## Phase 4: Zero-Context Spec Verification & Adjudication (`1` Combined Reviewer Default)

Run the **Zero-Context Spec Review Loop** ([`../../../templates/agent/spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)) when not already executed inside `flow-spec-planning`:

1. **Enforce Zero-Context Isolation Rules**: Confirm `git status --porcelain` shows zero production edits, dispatch fresh isolated read-only reviewer(s) (`type_name="self"` on Antigravity; never roleplay in-place, and never use `flash_lite` or `haiku` for spec review), and pass **only on-disk paths**.
2. **Single Combined Reviewer Default**:
   - For `Small` and `Medium` plans (`<= 4` chapters), run **one combined reviewer** checking root `spec.md`, `chapters/index.md`, all chapters, cross-chapter contracts, and OKF compliance in a single pass.
   - Use per-chapter + cross-chapter parallel reviewers only in the `Large` tier (`> 4` chapters or `/flow:prd`).
   - Run a **second review round only** when Round 1 returns `Critical` or `Important` findings that were `ADOPT`ed, scoping Round 2 strictly to the modified chapters.
3. **Adjudicate Findings (`ADOPT` / `CONTEST` / `ESCALATE`)**: Rewrite `ADOPT`ed changes in place in present tense across chapter and root specs, increment `plan_revision` once, and re-run `/flow:validate` (`exit 0`).

## Phase 5: Degraded-Model Disclosure, Approval Gate, & Plan Lock

1. **Mandatory Degraded-Model Banner**: If `planning_quality == "degraded"` (because quota exhaustion forced fallback from the primary frontier thinking model or a stalled planner was recovered from disk), present an explicit callout stating `planning_degraded_reason` and `planned_with_model` before the approval gate so the user knows the plan was not authored on the optimal thinking model.
2. Present the planning summary, Chapter & Task Blueprint table, `[0/N files documented]` manifest, and Review Adjudication Ledger, followed by `Approve | Revise | Refine` ([`interaction.md`](interaction.md)).
3. When approved, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across root `spec.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`, update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off to `/flow:implement <flow_id>`.
