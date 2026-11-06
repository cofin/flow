# Flow PRD (`/flow:prd`)

Co-design a **Master PRD & Multi-Chapter Flow Roadmap** (`.agents/bundles/specs/<flow_id>/spec.md`), progressive-disclosure chapter catalog (`specs/<flow_id>/chapters/index.md`), and **upfront detailed chapter specifications and 8-section task blueprints** (`specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/{spec.md,tasks/*.md}`) across `2..N` chapters (with zero upper cap on chapter count).

Use [`interaction.md`](interaction.md) (`structured-choice-v1`) for Design-Tree Frontier decisions and [`state.md`](state.md) for OKF v0.2 Markdown schemas. **No Production Code Rule**: Planning writes exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during throwaway spikes); never modify application source code during `/flow:prd`.

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
      - missing_concrete_signatures
      - missing_edge_case_matrix
      - missing_documentation_and_okf_plan
      - missing_okf_provenance
      - overlapping_chapters
      - missing_alternatives
      - stale_or_historical_plan_prose
    require:
      - problem_framing
      - locked_architectural_decisions
      - concrete_cross_chapter_contracts
      - documentation_and_okf_plan
      - ordered_chapter_roadmap
      - upfront_chapter_and_task_blueprints
```

## Unified Multi-Chapter Architecture (`/flow:prd` & Multi-Chapter `/flow:plan`)

- **Unified Nested Layout**: `/flow:prd <goal>` produces the exact same OKF v0.2 nested bundle layout as multi-chapter `/flow:plan`:
  - `specs/<flow_id>/spec.md` (`has_chapters: true`, `current_chapter: ch01-<slug>`, `chapters: [ch01-<slug>, ...]`) — Full-plan roadmap, plain-English North Star framing, cross-chapter public seams and shared struct/signature contracts, Flow-Wide Documentation & OKF Knowledge Plan (`[0/N files documented]`), full chapter checklist, and `## 6. Current State & Remaining Plan Snapshot`.
  - `specs/<flow_id>/chapters/index.md` — Frontmatter-free OKF v0.2 directory catalog listing all chapters in execution order.
  - `specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/{spec.md,tasks/t01..t04.md}` — `2..N` chapters (zero upper cap, `1–4` vertical-slice tasks per chapter) authored **upfront in parallel** by isolated Chapter Planner subagents so user design context and edge-case decisions are captured completely while fresh.
- **Anti-Truncation & Empirical True-Up**: Never cap chapter counts or compress a large initiative into thin stubs. When a downstream chapter genuinely depends on runtime measurements or discovered schema output from executing an earlier chapter, author its full requirements, edge cases, documentation targets, and provisional worksheets upfront with `planning_status: empirical_dependent`, `depends_on_chapters: [...]`, and `replan_trigger: "<exact runtime output required>"`.

## Workflow

### Phase 1: Bundle Intelligence, Domain Glossary, & Sharded Read-Only Scouts (`Facts First`)

1. Read `.agents/bundles/index.md`, `product/**`, `knowledge/**` (`domains/`, `architecture/`, `patterns/`, `testing/`, `gotchas/`, `decisions/`), `research/**`, and `.agents/skills/index.md`.
2. **Sharded Read-Only Scouts (`SubsystemDigest`)**:
   - Keep the coordinator under `< 25k` exploration tokens by dispatching parallel read-only Scout subagents (`1` per affected subsystem; on Google Antigravity use `run_workflow` `parallel()` with `agent(..., type_name="self", model="inherit")` and `agents/researcher.md`, verifying `git status --porcelain` afterward; on other harnesses invoke `@researcher` in parallel).
   - Collect exact `path/to/file::Symbol` entry points, existing public signatures, dependency categories, canonical test suites, gotchas, and impacted `docs/**` + `knowledge/**` files.
3. **Close All Research Gaps Upfront**:
   - Never create "research-only chapters" for discovery that belongs in PRD planning.
   - Promote external SDK/protocol audits and multi-subsystem findings into OKF v0.2 `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` notes with `sources:` + `[^id]:` footnotes ([`research.md`](research.md)).

### Phase 2: Design-Tree Frontier Discovery & Pre-Draft Coverage Gate (`structured-choice-v1`)

1. Map cross-cutting architectural choices, deep-module seams, error contracts, documentation scope, and chapter boundaries as a **design tree**.
2. Ask `1` `structured-choice-v1` question at dependent design forks and batch `2–3` orthogonal leaf questions once on a settled frontier ([`interaction.md`](interaction.md)), grounding every option in `path/to/file::Symbol` evidence and placing `<Label> (Recommended)` first.
3. Satisfy all five Pre-Draft Question Coverage Gate areas (seam selection + rejected alternatives, concrete shared types & edge-case/failure semantics, public-seam test strategy, `README.md` / `docs/**` & OKF knowledge deliverables, and full `ch01..chNN` decomposition with any `empirical_dependent` triggers) before drafting.

### Phase 3: Lock Root Roadmap (`specs/<flow_id>/spec.md`) & Fan Out Parallel Chapter Planners

1. Write `.agents/bundles/specs/<flow_id>/spec.md` (`type: Spec`, `flow_id: <flow_id>`, `status: draft`, `state: planned`, `has_chapters: true`, `chapters: [ch01-<slug>, ...]`, `current_chapter: ch01-<slug>`, `sources:` + `[^id]:` footnotes, zero standalone `---` body rules) covering all 6 normative sections from [`state.md`](state.md):
   - `## 1. Specification, Context & Provenance` — Including **North Star Goal & Problem Framing** in plain, jargon-free English (objectives, current limits, why this architecture succeeds, explicit Non-Goals / Backlog, and `Code Analysis & Seam Summary` with `[^id]` citations).
   - `## 2. Requirements, Concrete Contracts & Architecture` — Initiative requirements `R1..RN`, cross-chapter **Full Public Type, Struct, Schema & Signature Contracts**, **Caller -> Seam -> Collaborator Integration Map**, **Edge-Case, Failure-Mode & Invariant Matrix**, Acceptance Scenarios, and **Mandatory Alternatives Comparison**.
   - `## 3. Documentation & OKF Knowledge Plan` — `[0/N files documented]` manifest across user `README.md` / `docs/**` and `.agents/bundles/knowledge/**` + `.agents/skills/**` chapters.
   - `## 4. Requirement-to-Task Traceability Matrix` — Mapping every requirement and documentation deliverable to its owning `chNN / tMM` and verification gate.
   - `## 5. Implementation Plan` — Ordered chapter roadmap table + checklist (`- [ ] ch01-<slug> — <summary> (chapters/ch01-<slug>/spec.md)`, annotating `[empirical_dependent: <replan_trigger>]` where applicable) + **Chapter Recovery Checkpoint** policy.
   - `## 6. Current State & Remaining Plan Snapshot` — Present-tense baseline, active `ch01-<slug>`, full remaining chapter list, and `[0/N files documented]` status.
2. Write frontmatter-free `.agents/bundles/specs/<flow_id>/chapters/index.md` cataloging `ch01-<slug>..chNN-<slug>`.
3. **Parallel Upfront Chapter Blueprint Generation**:
   - Fan out **1 isolated Chapter Planner subagent per chapter in parallel** (`run_workflow` `parallel()` with `type_name="self"` and `agents/plan-generator.md` on Google Antigravity; parallel `@plan-generator` subagents elsewhere).
   - Each Chapter Planner writes `specs/<flow_id>/chapters/<ch_id>/spec.md` and `1–4` 8-section `tasks/t01-<slug>.md..t04-<slug>.md` worksheets (`read_set <= 6`, `files <= 3`, `estimated_loc <= 250`) following [`plan.md`](plan.md) and [`state.md`](state.md), including dedicated documentation and OKF knowledge synthesis tasks/chapters so nothing is deferred or truncated.

### Phase 4: Per-Chapter Zero-Context Review & Subagent Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)

1. **Dispatch Per-Chapter & Cross-Chapter Zero-Context Reviewers**:
   - Pass **only disk paths** (`specs/<flow_id>/spec.md`, `chapters/index.md`, `chapters/<ch_id>/{spec.md,tasks/*.md}`, `.agents/skills/index.md`, and relevant `knowledge/` chapters)—never conversational history.
   - Fan out **1 Zero-Context Reviewer per chapter** plus **1 Cross-Chapter Seam, Anti-Truncation & OKF Reviewer** in parallel (`type_name="self"` with `agents/code-reviewer.md` on Google Antigravity, checking `git status --porcelain` afterward; `@code-reviewer` elsewhere).
   - Audit **Cold-Reader Comprehension**, **Architectural & Problem Framing Review**, **Anti-Truncation & 8-Section Blueprint Readiness**, **OKF v0.2 & Documentation Plan Coverage**, and **Present-Tense Debloat**.
2. **Adjudicate Every Finding via Isolated Subagents**:
   - **`ADOPT`**: Dispatch isolated per-chapter revision subagents to rewrite affected `chapters/<ch_id>/{spec.md,tasks/*.md}` AND synchronize root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense, increment `plan_revision` once across all specs and tasks, and re-verify (up to 3 rounds).
   - **`CONTEST`**: Reject false positives or YAGNI scope creep by citing exact `path/to/file::Symbol` code, locked user decisions, or `false-positive-suppressions.md` rules.
   - **`ESCALATE`**: Surface genuine product trade-offs to the user via `structured-choice-v1`.

### Phase 5: Approval Gate (`Approve | Revise | Refine`) & Chapter 1 Handoff

1. Present the Master PRD & Multi-Chapter summary, full Chapter & Task Blueprint table (`ch01..chNN`), `[0/N files documented]` manifest, and Review Adjudication Ledger, followed by the `Approve | Revise | Refine` gate ([`interaction.md`](interaction.md)).
2. Upon approval, stamp `status: stable`, `verified:`, and `plan_commit: <HEAD_SHA>` across `specs/<flow_id>/spec.md`, all `chapters/<ch_id>/spec.md`, and all `tasks/*.md`, update `.agents/bundles/index.md`, `specs/index.md`, and `log.md`, and hand off to `/flow:implement <flow_id>` (which executes `ch01-<slug>` first and stops cleanly at each chapter boundary).
