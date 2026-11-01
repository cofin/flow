# Flow Plan (`/flow:plan`)

Co-design a decision-complete **Feature Specification** (`.agents/bundles/specs/<flow_id>/spec.md`) and `1–8` disjoint, vertical-slice **Task Worksheets** (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`), pressure-test them with a **Zero-Context Verification** pass, and adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`) before locking `plan_commit = HEAD`.

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for Design-Tree Frontier decisions and [`state.md`](state.md) for Markdown schemas. **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during throwaway prototypes); never modify application source code during `/flow:plan`.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, frontier_discovery, draft, gap_scan, zero_context_review, adjudication, approved, revise, refine, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task, fragile_line_numbers, shallow_passthrough_seam]
    require: [problem_framing, alternatives_evaluated, deep_module_seams, requirement_to_task_traceability, symbol_anchored_targets, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [rewrite_in_present_tense, increment_plan_revision_once, sync_revision_to_spec_and_tasks, reanchor_plan_commit]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    adjudication: [ADOPT, CONTEST, ESCALATE]
```

## Phase 1: Codebase Analysis, Domain Glossary, & Proportional Research (`Facts First`)

1. **Scope & Altitude Check**: If the requested goal spans multiple independent subsystems or requires `> 8` tasks, explain why and ask via `structured-choice-v1` whether to decompose it into a Master PRD (`/flow:prd`), narrow to a cohesive first slice, or continue.
2. **Read Bundle, Domain Glossary, & Skills**: Read `.agents/bundles/index.md`, `knowledge/workflow.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, `knowledge/testing/**`, `knowledge/gotchas/**`, `.agents/skills/index.md`, and any parent PRD (`parent_prd`).
3. **Read-Only Code & Seam Analysis**:
   - Inspect affected modules, symbols (`path/to/file::Symbol`), public **seams**, **interfaces**, **adapters**, and existing canonical unit test files.
   - Classify each dependency boundary using the Deep-Module Dependency Model:
     1. **In-process** (pure computation / in-memory state — merge into a deep module and test directly).
     2. **Local-substitutable** (local test stand-in like SQLite or in-memory FS — keep seam internal and test with stand-in).
     3. **Remote-owned (Ports & Adapters)** (define a port at the seam; use HTTP/RPC adapter in production and in-memory adapter in tests).
     4. **External boundary (Mock)** (third-party API/clock — inject port and mock only at the external boundary).
4. **Proportional Research & Throwaway Prototyping**:
   - Answer local repository questions directly via file reads (`0` subagents).
   - Dispatch `@researcher` subagents (`model: inherit`) only for independent external SDK/protocol questions or multi-domain unknowns, promoting validated findings into `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` ([`research.md`](research.md)).
   - When a state model or UI design question is uncertain on paper, build a throwaway prototype in untracked `.agents/scratch/<slug>/`, fold the validated decision into `spec.md`, and delete the scratch directory.

## Phase 2: Design-Tree Frontier Discovery & Interface Comparison (`structured-choice-v1`)

1. Present the **Code Analysis Summary** (`Area | Files Examined (path/to/file::Symbol) | Public Seam & Dependency Category`).
2. **Active Domain Modeling**: Challenge any fuzzy or overloaded nouns against `knowledge/domains/<domain>.md` and probe concrete edge-case scenarios (*"What happens when X and Y occur together?"*).
3. **Compare Interface Alternatives (For Non-Trivial Interfaces)**:
   - When introducing or reshaping a module interface, compare at least 2–3 distinct interface shapes (e.g., *minimal entry-point / maximum leverage*, *flexible / extensible*, *optimized for the default caller*) on **depth**, **locality**, and **seam placement**.
   - **Seam Rule**: One adapter means a hypothetical seam (unnecessary indirection); two adapters (e.g., production + test) justify a real port/seam.
4. **Walk the Design Frontier (`structured-choice-v1`)**:
   - Ask one product or architectural decision at a time on the current prerequisite-settled frontier ([`interaction.md`](interaction.md)), referencing exact `path/to/file::Symbol` targets and placing `<Label> (Recommended)` first.
   - Explicitly confirm the **public seams under test** before drafting task worksheets.

## Phase 3: Author Self-Contained Specification (`spec.md`) & Task Worksheets (`tasks/<id>-<slug>.md`)

### 3.1 Feature Specification (`.agents/bundles/specs/<flow_id>/spec.md`)

Write `spec.md` with the normative frontmatter from [`state.md`](state.md) and these 5 sections:

```markdown
# Flow: <Title>

## 1. Specification & Context

### 1.1 Problem Statement & Objectives
- Plain-English problem statement, current limits, why this approach succeeds, and explicit Non-Goals.

### 1.2 Upstream Execution Baseline
- Branch, parent PRD (if any), and prerequisite commits/dependencies.

### 1.3 Code Analysis & Seam Summary
| Area | Files Examined (`path/to/file::Symbol`) | Public Seam, Dependency Category & Integration |
| --- | --- | --- |
| ... | `src/module.py::ClassName` | ... |

### 1.4 Relevant Patterns, Domain Terms & Knowledge Chapters
- Links to applicable `.agents/bundles/knowledge/**` chapters and `.agents/skills/<domain>/SKILL.md`.

## 2. Requirements & Architecture

### 2.1 Functional Requirements
- **R1**: ...
- **R2**: ...

### 2.2 Public Interfaces, Deep Modules & Seam Contracts
- Exact public types, signatures, invariants, ordering rules, and error modes hidden behind the seam.

### 2.3 Non-Functional & Safety Constraints
- Performance, security, typing, and backwards-compatibility constraints.

### 2.4 Acceptance Scenarios (Given / When / Then)
- Concrete behavioral scenarios covering happy paths and boundary/error cases at the public seam.

### 2.5 Alternatives Considered
- Mandatory comparison of rejected interface/architectural designs (contrasted by depth, locality, and seam placement) and why the chosen design won.

## 3. Requirement-to-Task Traceability Matrix

| Requirement | Owning Task(s) | Verification Strategy | Confirmed Public Seam & Canonical Test Surface |
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

### 3.2 Atomic Vertical-Slice Task Worksheets (`tasks/<id>-<slug>.md`) — The Zero-Decision Rule

Create one worksheet per task (`tasks/t01-<slug>.md` or `tasks/1.1-<slug>.md`) following [`state.md`](state.md):

- **The Zero-Decision Rule (Implementation Readiness Standard)**: Leave **zero** architectural or design choices (schema, API path, signature, dependency, or edge-case behavior) to the executor. An isolated executor must be able to implement the worksheet on the first attempt without guessing.
- **One Vertical Slice = One Subagent Turn = One Commit**: Each task bundles one behavioral capability and its public-seam tests in the existing canonical test module. Never split a behavior into horizontal "write all tests" and "write all code" tasks, and never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Symbol-Anchored Targets (`path/to/file::Symbol`)**: Specify exact module, class, function, and method symbols in `## Context` and `## Steps` rather than fragile line numbers.
- **Change-Appropriate Verification Strategy**: Choose one strategy from [`discipline.md`](discipline.md) (`behavior_tdd`, `regression_tdd`, `characterization`, `static_validation`, `documentation_validation`, `integration_acceptance`) and state the exact initial and final CLI commands in `## Verification`.

## Phase 4: Zero-Context Spec Verification & Finding Adjudication

Before presenting the plan for user approval, run the **Zero-Context Spec Review Loop** ([`../../../templates/agent/spec-reviewer-prompt.md`](../../../templates/agent/spec-reviewer-prompt.md)):

1. **Enforce Zero-Context Isolation Rules**:
   - Confirm no uncommitted prototype edits sit in production source files.
   - Always dispatch a fresh isolated subagent (`model: inherit`)—never roleplay the reviewer in-place inside the planning session that authored the plan.
   - Pass **only on-disk repository paths** (`spec.md`, `tasks/*.md`, matching `.agents/skills/`, and `knowledge/` chapters)—never pass chat summaries or oral rationale. (If the user asks for a copyable prompt to run in a separate chat window, emit the verbatim reviewer prompt wrapped in five backticks `````` ````` ``````.)
2. **Review Dispatch Across Core Spec Lenses**:
   - **Cold-Reader Comprehension**: Can a fresh engineer/agent understand the problem, domain terms, and design without chat context?
   - **Architectural & Deep-Module Seam Review**: Does the design solve the root problem, reuse existing modules, avoid YAGNI/speculative generality, deepen modules rather than adding shallow pass-throughs, and justify its chosen interface over alternatives?
   - **Implementation Readiness (Zero-Decision Rule)**: Do `spec.md` and `tasks/*.md` cover every requirement with valid `depends_on` ordering, exact `path/to/file::Symbol` targets, confirmed public-seam tests, and zero unstated decisions?
   - **Prose & Style Debloat**: Are `spec.md` and `tasks/*.md` free of AI puffery, chronological sediment, and vague steps (`"wire it up"`, `"handle edge cases"`)?
   - When `run_workflow` is available (Google Antigravity), fan out `parallel(lenses, ...)` using `agent(type_name="code-reviewer", role=lens["role"], schema=SPEC_REVIEW_SCHEMA, model="inherit")` and retain persistent reviewer handles for round-2 verification.
3. **Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - **`ADOPT`**: Rewrite the affected sections of `spec.md` and `tasks/<id>-<slug>.md` in place in present tense ([`revise.md`](revise.md)), increment `plan_revision` once across `spec.md` and all tasks, and re-verify (up to 3 rounds).
   - **`CONTEST`**: Reject false positives, over-engineering, or out-of-scope suggestions by recording the exact `path/to/file::Symbol` evidence or `FP-*` suppression rule in the Adjudication Ledger.
   - **`ESCALATE`**: If a finding uncovers a genuine unresolved product decision, ask the user via `structured-choice-v1`.

## Phase 5: Approval Gate (`Approve | Revise | Refine`) & Plan Lock

1. Present the planning summary, Task Worksheet table, and Review Adjudication Ledger, followed by the `Approve | Revise | Refine` gate (`structured-choice-v1` in [`interaction.md`](interaction.md)).
2. When approved, stamp `plan_commit: <HEAD_SHA>` across `spec.md` and every `tasks/<id>-<slug>.md`, update `.agents/bundles/index.md` and `log.md`, and hand off to `/flow:implement <flow_id>`.
