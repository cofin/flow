# Flow PRD (`/flow:prd`)

Create a **Master PRD** (`.agents/bundles/specs/<prd_id>/spec.md`) for a multi-flow initiative and seed ordered `state: draft` child flow charters (`.agents/bundles/specs/<child_flow_id>/spec.md`).

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for human decisions and [`state.md`](state.md) for Markdown schemas. Planning writes exclusively under `.agents/bundles/`; never modify application source code during `/flow:prd`.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, draft, gap_scan, zero_context_review, adjudication, approved, revise, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, overlapping_child_flows]
    require: [locked_architectural_decisions, ordered_child_flow_roadmap, explicit_child_flow_boundaries]
```

## Altitude Boundary: Master PRD vs. Feature Specification vs. Task Worksheet

- **Master PRD (`/flow:prd <goal>`)**: Multi-flow initiative roadmap spanning `2–8` ordered child flows (chapters). Locks cross-cutting architectural invariants and seeds `state: draft` child flow charters (`specs/<child_id>/spec.md`). **Never creates code-level `tasks/*.md` worksheets inside the PRD bundle.**
- **Feature Specification (`/flow:plan <child_flow_id>`)**: Expands a single child flow charter into a detailed specification and `1–8` atomic `tasks/<id>-<slug>.md` worksheets.

## Workflow

### Phase 1: Bundle Intelligence & Proportional Research

1. Read `.agents/bundles/index.md`, `product/**`, `knowledge/**`, `research/**`, and `.agents/skills/index.md`.
2. Inspect affected codebase entry points and module boundaries directly using read-only file tools.
3. If the initiative depends on external SDK/protocol primary sources or at least two independent subsystem unknowns, dispatch `@researcher` subagents (`model: inherit`, or via `run_workflow` `parallel()` when available) and promote validated findings into `.agents/bundles/specs/<prd_id>/research/<topic>_<YYYYMMDD>.md`.

### Phase 2: Design Frontier Interview (`structured-choice-v1`)

1. Identify cross-cutting architectural decisions, subsystem boundaries, and milestone sequencing.
2. Ask one `structured-choice-v1` question at a time ([`interaction.md`](interaction.md)), grounding every choice in concrete `path/to/file::Symbol` evidence and placing the recommended option first (`<Label> (Recommended)`).

### Phase 3: Author Master PRD (`specs/<prd_id>/spec.md`) & Seed Child Flow Charters

1. Write `.agents/bundles/specs/<prd_id>/spec.md` (`type: Spec`, `flow_id: <prd_id>`, `state: planned`, `parent_prd: null`) with:
   - `## 1. North Star Goal & Context` (problem statement, structural blind spots, target outcomes)
   - `## 2. Locked Architectural Decisions` (cross-cutting invariants binding all child flows)
   - `## 3. Master Roadmap (Ordered Child Flows)` (table: `Chapter | Flow ID | Title | Key Deliverables | Dependencies | State`)
   - `## 4. Global Constraints (Applicable to All Child Flows)`
   - `## 5. Backlog (Deferred Items)`
   - `## Implementation Plan` (checklist of child flow charters `- [ ] <child_flow_id> — <summary> (../<child_flow_id>/spec.md)`)
   - `## Continuity Snapshot`
2. For each child flow in the Master Roadmap, create `.agents/bundles/specs/<child_flow_id>/spec.md` (`type: Spec`, `flow_id: <child_flow_id>`, `state: draft`, `parent_prd: <prd_id>`) containing its scoped charter, upstream dependencies, key deliverables, and acceptance boundary.

### Phase 4: Dynamic, Zero-Context Focused Review & Finding Adjudication

1. Dispatch zero-context architectural review on `.agents/bundles/specs/<prd_id>/spec.md` and its child flow charters (using `run_workflow` `parallel()` with `schema=FINDINGS_SCHEMA` when available, or `@code-reviewer` with `model: inherit`), passing **only disk paths** (`specs/<prd_id>/spec.md`, child `spec.md` paths, `.agents/skills/index.md`, and relevant `knowledge/` chapters)—never conversation transcripts.
2. Adjudicate every reviewer finding with explicit evidence:
   - **`ADOPT`**: Update the Master PRD or child charters in place in present tense, increment `plan_revision` once, and re-verify.
   - **`CONTEST`**: Reject false positives or scope-creeping suggestions by citing exact `path/to/file::Symbol` code, locked user decisions, or `false-positive-suppressions.md` rules.

### Phase 5: Approval Gate & Chapter 1 Handoff

1. Present the Master PRD summary, Ordered Child Flows table, and Zero-Context Review Adjudication Ledger, followed by the `Approve | Revise` gate ([`interaction.md`](interaction.md)).
2. Upon approval, stamp `plan_commit = HEAD` on `specs/<prd_id>/spec.md`, update `.agents/bundles/index.md` and `log.md`, and ask via a binary `structured-choice-v1` prompt whether to immediately expand Chapter 1 via `/flow:plan <first_child_flow_id>` (Recommended) or stop after PRD creation.
