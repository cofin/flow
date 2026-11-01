# Flow Plan (`/flow:plan`)

Author a decision-complete **Feature Specification** (`.agents/bundles/specs/<flow_id>/spec.md`) and `1–8` disjoint, vertical-slice **Task Worksheets** (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`), verify them through **Dynamic, Zero-Context Focused Review**, and adjudicate findings (`ADOPT` vs. `CONTEST`) before locking `plan_commit = HEAD`.

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for human decisions and [`state.md`](state.md) for Markdown schemas. Planning writes exclusively under `.agents/bundles/`; never modify application source code during `/flow:plan`.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, draft, gap_scan, zero_context_review, adjudication, approved, revise, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task, fragile_line_numbers]
    require: [requirement_to_task_traceability, symbol_anchored_targets, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [rewrite_in_present_tense, increment_plan_revision_once, sync_revision_to_spec_and_tasks, reanchor_plan_commit]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    adjudication: [ADOPT, CONTEST]
```

## Phase 1: Codebase Analysis, Bundle Context & Proportional Research

1. **Scope Check**: If the requested goal spans multiple independent subsystems or requires `> 8` tasks, recommend decomposing it into a Master PRD (`/flow:prd`) or scoping a cohesive first slice via `structured-choice-v1`.
2. **Read Bundle & Skills**: Read `.agents/bundles/index.md`, `knowledge/workflow.md`, matching `knowledge/{architecture,patterns,domains,testing,gotchas}/**/*.md` chapters, `.agents/skills/index.md`, and any parent PRD (`parent_prd`).
3. **Read-Only Code Analysis**: Inspect affected modules, symbols (`path/to/file::Symbol`), public seams, and existing canonical unit test files.
4. **Proportional Research Closure**: Answer local repository questions directly via file reads (`0` subagents). Dispatch `@researcher` subagents (`model: inherit`) only for independent external SDK/protocol questions or multi-domain unknowns, and promote validated findings into `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` ([`research.md`](research.md)).

## Phase 2: Design Frontier Interview (`structured-choice-v1`)

1. Present the **Code Analysis Summary** (`Area | Files Examined | Architectural Integration` with `path/to/file::Symbol` anchors).
2. Resolve any genuine product or architectural trade-offs one decision at a time using `structured-choice-v1` ([`interaction.md`](interaction.md)), referencing exact symbols/files and placing the recommended option first (`<Label> (Recommended)`).

## Phase 3: Author Rich Feature Specification (`spec.md`) & Task Worksheets (`tasks/<id>-<slug>.md`)

### 3.1 Feature Specification (`.agents/bundles/specs/<flow_id>/spec.md`)

Write `spec.md` with the normative frontmatter from [`state.md`](state.md) and these 5 sections:

```markdown
# Flow: <Title>

## 1. Specification & Context

### 1.1 Upstream Execution Baseline
- Branch, parent PRD (if any), and prerequisite commits/dependencies.

### 1.2 Code Analysis Summary
| Area | Files Examined (`path/to/file::Symbol`) | Architectural Integration |
| --- | --- | --- |
| ... | `src/module.py::ClassName` | ... |

### 1.3 Relevant Patterns & Knowledge Chapters
- Links to applicable `.agents/bundles/knowledge/**` chapters and `.agents/skills/<domain>/SKILL.md`.

## 2. Requirements

### 2.1 Functional Requirements
- **R1**: ...
- **R2**: ...

### 2.2 Non-Functional & Safety Constraints
- Performance, security, typing, and backwards-compatibility constraints.

### 2.3 Acceptance Scenarios (Given / When / Then)
- Concrete behavioral scenarios covering happy paths and edge/error cases.

### 2.4 Alternatives Considered
- Rejected approaches and why the chosen design is superior.

## 3. Requirement-to-Task Traceability Matrix

| Requirement | Owning Task(s) | Verification Strategy | Canonical Test / Gate Surface |
| --- | --- | --- | --- |
| R1 | `t01` | `behavior_tdd` | `tests/unit/test_module.py::test_behavior` |

## 4. Implementation Plan

### Phase 1: <Phase Name>
- [ ] t01 — <Task Title> (tasks/t01-<slug>.md)
- [ ] t02 — <Task Title> (tasks/t02-<slug>.md)
- **Phase 1 Recovery Checkpoint**: `<exact lint + phase test command>`

## 5. Continuity Snapshot
- **Flow ID**: `<flow_id>` (`state: planned`, `plan_revision: 1`, `plan_commit: <sha>`)
- **Current Task**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**: ...
- **Recent Discoveries**: ...
```

### 3.2 Atomic Vertical-Slice Task Worksheets (`tasks/<id>-<slug>.md`)

Create one worksheet per task (`tasks/t01-<slug>.md` or `tasks/1.1-<slug>.md`) following [`state.md`](state.md):

- **One Vertical Slice = One Subagent Turn = One Commit**: Each task bundles production code changes and their corresponding unit tests in the existing canonical test module. Never split a single behavior into separate "write code" and "write tests" tasks, and never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Symbol-Anchored Targets (`path/to/file::Symbol`)**: Specify exact module, class, function, and method symbols in `## Context` and `## Steps` rather than fragile line numbers.
- **Change-Appropriate Verification Strategy**: Choose one strategy from [`discipline.md`](discipline.md) (`behavior_tdd`, `regression_tdd`, `characterization`, `static_validation`, `documentation_validation`, `integration_acceptance`) and state the exact initial and final CLI commands in `## Verification`.

## Phase 4: Dynamic, Zero-Context Focused Review & Finding Adjudication

Before presenting the plan for user approval, run the **Dynamic, Zero-Context Focused Review Loop** ([`templates/agent/spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)):

1. **Select Matching Domain Lenses**: Match the planned `files:` across all `tasks/*.md` against `.agents/skills/index.md` and `.agents/bundles/knowledge/index.md` to select the relevant project-local `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/` (`checklist.md` + `false-positive-suppressions.md`), and `knowledge/**` chapters.
2. **Zero-Context Review Dispatch (Disk Paths Only — Never Chat Transcripts)**:
   - **When `run_workflow` is available (Google Antigravity)**: Execute an async Python workflow script that enters `phase("Zero-Context Spec Review")`, fans out `parallel(lenses, ...)` using `agent(type_name="code-reviewer", role=lens["role"], schema=SPEC_REVIEW_SCHEMA, model="inherit")` with **only on-disk file paths** (`spec.md`, `tasks/*.md`, matching `.agents/skills/`, and `knowledge/` chapters), and retains persistent reviewer handles (`reviewer = agent(...)`) for round-2 verification.
   - **In all other harnesses**: Dispatch isolated `@code-reviewer` (and matching `.agents/agents/<domain>-reviewer`) subagents (`model: inherit`) with the same disk-only brief.
3. **Evidence-Backed Finding Adjudication (`ADOPT` vs. `CONTEST`)**:
   - Evaluate every returned finding against the codebase and `false-positive-suppressions.md`:
     - **`ADOPT`**: Rewrite the affected sections of `spec.md` and `tasks/<id>-<slug>.md` in place in present tense, increment `plan_revision` once across `spec.md` and all tasks, and re-verify with the reviewer (up to 3 rounds).
     - **`CONTEST`**: Reject false positives, over-engineering, or out-of-scope suggestions by recording the exact `path/to/file::Symbol` evidence or `FP-*` suppression rule in the Adjudication Ledger.

## Phase 5: Approval Gate & Plan Lock

1. Present the planning summary, Task Worksheet table, and Zero-Context Review Adjudication Ledger, followed by the `Approve | Revise` gate (`structured-choice-v1` in [`interaction.md`](interaction.md)).
2. When approved, stamp `plan_commit: <HEAD_SHA>` across `spec.md` and every `tasks/<id>-<slug>.md`, update `.agents/bundles/index.md` and `log.md`, and hand off to `/flow:implement <flow_id>`.
