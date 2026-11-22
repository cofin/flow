# Flow Spec (`/flow:spec`, `/flow:plan`)

Design a decision-complete **Feature Spec** (`.agents/bundles/specs/<flow_id>/spec.md`) scaled to change size (`Small`, `Medium`, `Large`) without dropping engineering or doc scope.
Validate OKF v0.2 compliance right after writing, run independent review (`1` combined reviewer for `<= 4` chapters), and decide on each finding (`ADOPT` / `CONTEST` / `ESCALATE`) before stamping `status: stable` and `plan_commit: <HEAD_SHA>`.

Use [`interaction.md`](interaction.md) for open decisions, [`state.md`](state.md) and [`../../../templates/agent/plan-schema-card.md`](../../../templates/agent/plan-schema-card.md) for schemas, and [`../../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md`](../../multi-harness-plugins/references/skills-subagents-and-mcp-limits.md) for model routing and `run_workflow` rules.
**No Production Code Rule**: Planning writes only under `.agents/bundles/` (or the primary checkout's `.agents/bundles/` inside `local-only` git worktrees); never edit application source code during `/flow:spec`.

## Planning Sizes (`Small` | `Medium` | `Large`)

Choose the layout from estimated production LOC and impacted modules:

| Size | Trigger | Research | Layout | Worksheet | Planners | Review |
| --- | --- | --- | --- | --- | --- | --- |
| **Small / Single-Chapter** | Cohesive single feature (no intermediate checkpoint needed) | Coordinator direct read (`<= 8` files) or `flow-scout` | Single-chapter `spec.md` (`has_chapters: false`) | Compact by default (`full` only for complex public interfaces) | Coordinator only | `1` combined reviewer (`1` round) |
| **Medium** | `2..4` genuine stages, parallel subsystems, or `empirical_dependent` checks | Direct read (`<= 8` files) or `flow-scout` | Chapters (`2..4`) + `chapters/index.md` | Compact or Full (`worksheet_format: compact \| full`) | `flow-spec-planning` (`per_chapter` parallel for `>= 2` chapters) | `1` combined reviewer (`2nd` round only on adopted blocking findings) |
| **Large** | `> 4` chapters or `/flow:prd` | `flow-scout` parallel summaries | Chapters (`ch01..chNN`, no cap) + `chapters/index.md` | Compact or Full (`worksheet_format: compact \| full`) | `flow-spec-planning` (`per_chapter` parallel) | Per-chapter + cross-chapter reviewers |

- **Plan the Whole Scope**: Size scales ceremony and subagent count, never engineering scope.
- Default cohesive features of any size to a single-chapter `spec.md`, and split into `chapters/` only at genuine checkpoints, parallel subsystems, or `empirical_dependent` triggers.
- Allow `compact` worksheets for straightforward tasks, with no artificial caps on task count per chapter, `read_set`, `files`, or `estimated_loc`.
- During execution, chapters with `> 4` tasks split into parallel separate-file steps or `<= 4`-task worker groups.

## Phase 1: Bundle Review & Right-Sized Research

1. **Read Bundle Catalogs & Domain Glossary**: Read `.agents/bundles/index.md`, `knowledge/workflow.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, `knowledge/testing/**`, `knowledge/gotchas/**`, `.agents/skills/index.md`, and any parent spec.
2. **Direct Read vs. Shipped `flow-scout` Workflow**:
   - When the request touches `<= 8` files across `<= 2` modules, read those files directly in the coordinator (`< 15k` tokens) with no subagent overhead.
   - When touching `> 8` files or `>= 3` subsystems:
     - **Google Antigravity**: Call `run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [{"name": "auth", "paths": ["src/auth/"]}], "query": "..."})`, which resolves `(model, effort)` routes and prefetches seed excerpts ([`orchestration.md`](orchestration.md)).
     - **Other Harnesses**: Invoke `@researcher` in parallel using resolved profiles ([`orchestration.md`](orchestration.md)).
3. **Classify Dependency Boundaries**: Classify collaborators into **In-process**, local test double, **Remote-owned (Ports & Adapters)**, and **External boundary (Mock)**. Promote external SDK or multi-domain research to `specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` ([`research.md`](research.md)).

## Phase 2: Open Decisions & Interface Comparison

1. Present the **Code Analysis & Interface Summary** (`Area | Files Examined (path/to/file::Symbol) | Public Interface & Dependency Category | Affected Docs / OKF Chapters`).
2. **Compare Interface Alternatives**: Compare 2–3 distinct interface shapes on **depth**, **locality**, and **adapter count** (*one adapter = hypothetical interface; two concrete callers/adapters = real interface*).
3. **Walk Unresolved Open Decisions Only**:
   - Skip questions already settled by the prompt and codebase.
   - Ask `1` question at unresolved dependent forks, and batch `2-3` independent leaf questions once ([`interaction.md`](interaction.md)), putting `<Label> (Recommended)` first across interface choice, contracts, public interface tests, `< 60s` lint/test checkpoints, `docs/**` + OKF targets, and chapters.

## Phase 3: Author Specs, Worksheets & Validation

### 3.1 Single-Chapter vs. `flow-spec-planning`

- **Single-Chapter Flow (`has_chapters: false`)**:
  - Coordinator writes `specs/<flow_id>/spec.md` (`has_chapters: false`) and `specs/<flow_id>/tasks/tNN-<slug>.md` (`worksheet_format: compact` by default, or `full` for complex public interfaces) per [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), then runs `/flow:validate` (`exit 0`).
- **Medium & Large Multi-Chapter Flows**:
  1. Coordinator writes root `specs/<flow_id>/spec.md` (`has_chapters: true`, `current_chapter: ch01-<slug>`, `chapters: [...]`) and frontmatter-free `specs/<flow_id>/chapters/index.md`.
  2. **Google Antigravity**: Call `run_workflow(ScriptPath="<plugin_root>/workflows/flow-spec-planning/workflow.py", Args={"flow_id": "<flow_id>", "chapters": [{"id": "ch01-core", "brief": "...", "read_files": ["src/core.py"]}], "seed_files": ["src/core.py"], "review": "single"})`, keeping tasks around `<= 250` LOC and `<= 3` files where boundaries permit ([`orchestration.md`](orchestration.md)).
     - `flow-spec-planning` prefetches seed files, passes [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md) (`type_name="self"`), writes `chapters/<id>/planner-notes.md`, recovers stalled planners after `45s` disk idle, runs OKF validation, flags `planning_quality: degraded` on fallback, and runs independent review when `root_spec_issues` is empty.
     - **Manual Fallback Rule**: If a background workflow has written every chapter's `spec.md`, `tasks/*.md`, and `planner-notes.md` and stalls, cancel it, fold every `planner-notes.md` `Root Spec Issues` entry into root `spec.md`, and continue to review.
  3. **Other Harnesses**: Dispatch parallel `@plan-generator` subagents (`>= 2` chapters) on the resolved `strong` model role, passing root `spec.md`, [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md), and scoped files; fold `planner-notes.md` issues into root `spec.md` and run `/flow:validate` (`exit 0`).

### 3.2 Spec Body (`spec.md`) & Task Worksheets

Follow [`state.md`](state.md) and [`plan-schema-card.md`](../../../templates/agent/plan-schema-card.md):

- **6 Required `spec.md` Sections** (preceded by a `<= 40`-line `<!-- truth: start -->` truth block, with `sources:` + `[^id]:` footnotes and zero standalone `---` body rules):
  1. `## 1. Specification, Context & Provenance` — `### 1.1 Problem Statement & Objectives`, `### 1.2 Upstream Execution Baseline`, `### 1.3 Code Analysis & Interface Summary`, and `### 1.4 Relevant OKF Knowledge Chapters & Skills`.
  2. `## 2. Requirements, Concrete Contracts & Architecture` — `R1..RN`, concrete public types/signatures, `Caller -> Interface -> Collaborator` map, Edge-Case & Failure-Mode Matrix, Acceptance Scenarios, and Alternatives Considered.
  3. `## 3. Documentation & OKF Knowledge Plan` (`[0/N files documented]`).
  4. `## 4. Requirement-to-Task Traceability Matrix`.
  5. `## 5. Implementation Plan` — Checklist plus fast (`< 60s`) **Chapter / Phase Recovery Checkpoint** (`make lint` + targeted unit test file, never a slow `> 60s` full test suite).
  6. `## 6. Current State & Remaining Plan Snapshot`.
- **Task Worksheets (`tasks/<id>-<slug>.md`)**: Reference shared types/signatures in `spec.md` instead of duplicating them; use `compact` headings by default and `full` headings when complex contracts need full detail.

## Phase 4: Independent Spec Verification

Run the **Independent Spec Review Loop** ([`../../../templates/agent/spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)) when not already run inside `flow-spec-planning`:

1. **Enforce Isolation Rules**: Confirm `git status --porcelain` shows zero production edits, dispatch fresh read-only reviewer(s) (`type_name="self"` on Antigravity; `strong` model role per [`orchestration.md`](orchestration.md)), and pass **only on-disk paths**.
2. **Single Combined Reviewer Default**:
   - For `Small` and `Medium` plans (`<= 4` chapters), run **one combined reviewer** checking root `spec.md`, `chapters/index.md`, all chapters, shared contracts, and OKF compliance in one pass.
   - Use per-chapter + cross-chapter parallel reviewers only for `Large` plans (`> 4` chapters or `/flow:prd`).
   - Run a **second review round only** when Round 1 returns `Critical` or `Important` findings that were `ADOPT`ed, scoped to the modified chapters.
3. **Decide on Each Finding (`ADOPT` / `CONTEST` / `ESCALATE`)**: Rewrite `ADOPT`ed changes in place in present tense across chapter and root specs, increment `plan_revision` once, and re-run `/flow:validate` (`exit 0`).

## Phase 5: Approval Check & Plan Lock

1. **Degraded-Model Banner**: If `planning_quality == "degraded"`, display a callout stating `planning_degraded_reason` and `planned_with_model` before the approval prompt.
2. Present the planning summary, Chapter & Task table, `[0/N files documented]` checklist, and Review Summary, followed by `Approve | Revise | Refine` ([`interaction.md`](interaction.md)).
3. When approved, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across root `spec.md`, `chapters/<ch_id>/spec.md`, and `tasks/*.md`.
4. Update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off to `/flow:implement <flow_id>`.
