# Flow PRD (`/flow:prd`)

Co-design a **Master PRD** (`.agents/bundles/specs/<prd_id>/spec.md`) for a multi-flow initiative and seed ordered `state: draft` child flow charters (`.agents/bundles/specs/<child_flow_id>/spec.md`).

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for Design-Tree Frontier decisions and [`state.md`](state.md) for Markdown schemas. **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during throwaway spikes); never modify application source code during `/flow:prd`.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, frontier_discovery, draft, gap_scan, zero_context_review, adjudication, approved, revise, refine, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, overlapping_child_flows, missing_alternatives]
    require: [problem_framing, locked_architectural_decisions, ordered_child_flow_roadmap, explicit_child_flow_boundaries]
```

## Altitude Boundary: Master PRD vs. Feature Specification vs. Task Worksheet

- **Master PRD (`/flow:prd <goal>`)**: Multi-flow initiative roadmap spanning `2–8` ordered child flows (chapters). Frames the problem and objectives in plain English, locks cross-cutting deep-module seams and alternatives, and seeds `state: draft` child flow charters (`specs/<child_id>/spec.md`). **Never creates code-level `tasks/*.md` worksheets inside the PRD bundle.**
- **Feature Specification (`/flow:plan <child_flow_id>`)**: Expands a single child flow charter into a detailed specification and `1–8` atomic `tasks/<id>-<slug>.md` worksheets.

## Workflow

### Phase 1: Bundle Intelligence, Domain Glossary, & Proportional Research (`Facts First`)

1. Read `.agents/bundles/index.md`, `product/**`, `knowledge/**` (especially `knowledge/domains/**` and `knowledge/architecture/**`), `research/**`, and `.agents/skills/index.md`.
2. Inspect affected codebase entry points and module boundaries directly using read-only file tools.
3. **Close All Research Gaps Upfront**:
   - Never create "research chapters" for investigation that must happen during PRD design.
   - If the initiative depends on external SDK/protocol primary sources or at least two independent subsystem unknowns, dispatch `@researcher` subagents (`model: inherit`, or via `run_workflow` `parallel()` when available) and promote validated findings into `.agents/bundles/specs/<prd_id>/research/<topic>_<YYYYMMDD>.md` ([`research.md`](research.md)).

### Phase 2: Design-Tree Frontier Discovery (`structured-choice-v1`)

1. Map unresolved cross-cutting architectural choices, deep-module seams, and milestone boundaries as a **design tree**.
2. Separate **facts** (resolved by reading code/docs in Phase 1) from **decisions** (product trade-offs, seam placement, migration strategy).
3. Ask one `structured-choice-v1` question at a time on the current prerequisite-settled frontier ([`interaction.md`](interaction.md)), grounding every option in concrete `path/to/file::Symbol` evidence and placing `<Label> (Recommended)` first.
4. Summarize the anchored architecture hypothesis and confirm alignment before drafting the roadmap.

### Phase 3: Author Master PRD (`specs/<prd_id>/spec.md`) & Seed Child Flow Charters

1. Write `.agents/bundles/specs/<prd_id>/spec.md` (`type: Spec`, `flow_id: <prd_id>`, `state: planned`, `parent_prd: null`) framing the initiative in plain, jargon-free English:
   - `## 1. North Star Goal & Problem Framing` (Objectives without jargon, Current State & Limits, What Is New & Why It Succeeds, Impact, Risks & Mitigations, Success Metrics)
   - `## 2. Locked Architectural Seams & Alternatives Considered` (Cross-cutting deep-module interfaces, ports/adapters, and rejected alternatives with concrete reasons for rejection)
   - `## 3. Master Roadmap (Ordered Child Flows)` (table: `Chapter | Flow ID | Title | Key Deliverables | Public Seams | Dependencies | State`)
   - `## 4. Global Constraints (Applicable to All Child Flows)`
   - `## 5. Backlog (Explicitly Out-of-Scope / Deferred Items)`
   - `## Implementation Plan` (checklist of child flow charters `- [ ] <child_flow_id> — <summary> (../<child_flow_id>/spec.md)`)
   - `## Continuity Snapshot`
2. For each chapter in the Master Roadmap, create `.agents/bundles/specs/<child_flow_id>/spec.md` (`type: Spec`, `flow_id: <child_flow_id>`, `state: draft`, `parent_prd: <prd_id>`) containing its scoped charter, upstream dependencies, key deliverables, public seams, and acceptance boundary.
3. Promote any adopted research from `.agents/bundles/research/` into the owning roadmap or child spec bundle (`specs/<id>/research/`).

### Phase 4: Zero-Context Review & Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)

1. **Dispatch Zero-Context Review**:
   - Pass **only disk paths** (`specs/<prd_id>/spec.md`, child `spec.md` paths, `.agents/skills/index.md`, and relevant `knowledge/` chapters)—never conversational history.
   - Use `run_workflow` `parallel()` with `schema=SPEC_REVIEW_SCHEMA` when available on Google Antigravity, or `@code-reviewer` (`model: inherit`).
   - Evaluate across four review lenses: **Cold-Reader Comprehension**, **Architectural & Problem Framing Review**, **Chapter Boundary & Dependency Readiness**, and **Prose Debloat**.
2. **Adjudicate Every Finding**:
   - **`ADOPT`**: Rewrite the Master PRD or child charters in place in present tense, increment `plan_revision` once, and re-verify (up to 3 rounds).
   - **`CONTEST`**: Reject false positives or YAGNI scope creep by citing exact `path/to/file::Symbol` code, locked user decisions, or `false-positive-suppressions.md` rules.
   - **`ESCALATE`**: Surface genuine product trade-offs to the user via `structured-choice-v1`.

### Phase 5: Approval Gate (`Approve | Revise | Refine`) & Chapter 1 Handoff

1. Present the Master PRD summary, Ordered Child Flows table, and Review Adjudication Ledger, followed by the `Approve | Revise | Refine` gate ([`interaction.md`](interaction.md)).
2. Upon approval, stamp `plan_commit = HEAD` on `specs/<prd_id>/spec.md`, update `.agents/bundles/index.md` and `log.md`, and ask via a binary `structured-choice-v1` prompt whether to immediately plan Chapter 1 via `/flow:plan <first_child_flow_id>` (Recommended) or stop after PRD creation.
