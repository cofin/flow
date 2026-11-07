---
name: flow-planning
description: "Use when co-designing Master PRDs (/flow:prd), authoring high-detail feature and chapter specifications and vertical-slice task blueprints (/flow:spec, alias /flow:plan), revising or refining plans in present tense (/flow:revise, /flow:refine), or running primary-source research and throwaway prototypes (/flow:research, /flow:task)."
disable-model-invocation: true
---

# Flow Planning (Chaptered High-Detail Co-Design & Zero-Context Verification)

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,spec,plan,revise,refine,research,task -->

## Trigger

Use for `prd` ([`../flow/references/prd.md`](../flow/references/prd.md)), `spec` / `plan` ([`../flow/references/spec.md`](../flow/references/spec.md)), `revise` / `refine` ([`../flow/references/revise.md`](../flow/references/revise.md)), and `research` / `task` ([`../flow/references/research.md`](../flow/references/research.md)).

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

## Thin Coordinator, Chapter Subagents, & Zero-Context Verification

- **Thin Coordinator (`< 25k` exploration tokens)**: Reads `.agents/bundles/index.md` and `knowledge/`, shards codebase scouting (`SubsystemDigest`) across isolated read-only subagents when touching `> 2` files or `>= 2` modules, walks the `structured-choice-v1` decision frontier with the user, writes root `specs/<flow_id>/spec.md` + `chapters/index.md`, and fans out parallel Chapter Planner subagents (`@plan-generator`) so every chapter and worksheet is authored in full detail upfront without compacting the coordinator window.
- **Anti-Truncation & Horizontal Scaling**: Each chapter is bounded to `1–4` vertical-slice tasks (`1–3` production files, `read_set <= 6` files, `estimated_loc <= 250` per task) strictly to fit subagent context windows—**never to shorten planning, merge distinct behaviors into vague tasks, omit edge cases, or drop documentation/OKF work**. Expand into as many granular chapters (`ch01..chNN`, zero upper cap) as the initiative requires.
- **Zero-Context Verifier (`@code-reviewer`, `<domain>-reviewer`)**: Runs in fresh, isolated subagents (`model: inherit`; `type_name="self"` on Google Antigravity) with **only on-disk repository paths**—never chat history—auditing **Cold-Reader Comprehension**, **Architectural & Deep-Module Seams**, **Anti-Truncation & 8-Section Blueprint Readiness**, **OKF v0.2 & Documentation Plan Coverage**, and **Present-Tense Debloat**.

## Unified Planning Hierarchy (`Root Roadmap Spec` &rarr; `Chapter Spec` &rarr; `Task Blueprint`)

| Level | Artifact | Command & Owner | Scope & Altitude |
| --- | --- | --- | --- |
| **Multi-Chapter Flow / Master PRD** | `specs/<flow_id>/spec.md` + `specs/<flow_id>/chapters/index.md` | `/flow:prd <goal>` or `/flow:spec <goal>` (`> 4` tasks or `>= 2` modules) | Full-plan present-tense roadmap (`2..N` chapters, zero upper cap): plain-English problem statement, shared public types/signatures, Flow-Wide Documentation & OKF Knowledge Plan (`[k/N files documented]`), full chapter checklist, and `Current State & Remaining Plan Snapshot`. |
| **Chapter / Single-Chapter Spec** | `specs/<flow_id>/chapters/chNN-<slug>/spec.md` (or root `specs/<flow_id>/spec.md` for `1–4` tasks) | Parallel Chapter Planner subagents (`@plan-generator`) | Cohesive chapter blueprint (`1–4` tasks): OKF v0.2 provenance (`sources:` + `[^id]:`, `<= 40`-line truth block), concrete public types & signatures, `Caller -> Seam -> Collaborator` map, Edge-Case & Failure-Mode Matrix, Alternatives Comparison, Documentation & OKF Plan, and `Chapter Recovery Checkpoint`. |
| **Task Blueprint (`Task`)** | `chapters/chNN-<slug>/tasks/t01-<slug>.md` (or `specs/<flow_id>/tasks/t01-<slug>.md`) | Authored upfront in `/flow:spec` / `/flow:prd`, revised in `/flow:revise`, executed in `/flow:implement` (`@executor`) | One isolated executor turn and one atomic commit (`read_set <= 6`, `files <= 3`, `estimated_loc <= 250`) containing all 8 blueprint sections and non-tautological Worked Test Matrix literals in canonical module test files. |

## Workflow

1. **Ground in Bundle, Domain Glossary, & Sharded Scouts (`Facts First`)**:
   - Read `.agents/bundles/index.md`, `knowledge/domains/**`, `knowledge/architecture/**`, `knowledge/patterns/**`, and `.agents/skills/index.md`.
   - When touching `> 2` source files or `>= 2` modules, dispatch parallel read-only Scout subagents (`@researcher` returning `SubsystemDigest`; `type_name="self"` on Google Antigravity) to collect exact signatures, seams, canonical test fixtures, edge cases, and impacted `knowledge/**` + `docs/**` files. Promote external SDK/multi-domain research to OKF v0.2 `specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` ([`../flow/references/research.md`](../flow/references/research.md)).
2. **Walk the Design-Tree Frontier & Pass the Coverage Gate (`structured-choice-v1`)**:
   - Ask `1` question at dependent design forks and batch `2–3` orthogonal leaf questions once on a settled frontier ([`../flow/references/interaction.md`](../flow/references/interaction.md)), citing `path/to/file::Symbol` and placing `<Label> (Recommended)` first.
   - Compare at least two distinct interface shapes on **depth** (complexity hidden behind a small interface), **locality**, and **seam/adapter count**, and satisfy all five areas of the Pre-Draft Question Coverage Gate (seam choice, concrete data/error contracts, public-seam test strategy, `docs/**` + OKF scope, and full `ch01..chNN` decomposition).
3. **Author Root Roadmap & Upfront Parallel Chapter Blueprints (Zero-Decision Rule)**:
   - For `1–4` tasks within one module, write `specs/<flow_id>/spec.md` and `specs/<flow_id>/tasks/t01..t04.md`.
   - For `> 4` tasks, `>= 2` modules, or `/flow:prd`, write root `specs/<flow_id>/spec.md` (`has_chapters: true`, `chapters: [...]`) and frontmatter-free `specs/<flow_id>/chapters/index.md`, then fan out **1 isolated Chapter Planner subagent per chapter in parallel** (`type_name="self"` on Antigravity) to write every `chapters/chNN-<slug>/spec.md` and 8-section `tasks/t01..t04.md` upfront (`planning_status: empirical_dependent` + `replan_trigger` + `depends_on_chapters` only when upstream runtime evidence is genuinely required).
4. **Per-Chapter Zero-Context Verification & Subagent Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)**:
   - Fan out isolated Zero-Context Spec Reviewers **one per chapter** plus one **Cross-Chapter Seam, Anti-Truncation & OKF Reviewer** passing **only disk paths** (`type_name="self"` on Antigravity; verify `git status --porcelain` is unchanged after review).
   - Delegate `ADOPT` updates to isolated per-chapter revision subagents that rewrite both the chapter artifacts and root `specs/<flow_id>/spec.md` + `chapters/index.md` **in place in present tense**, **`CONTEST`** false positives with `path/to/file::Symbol` or `FP-*` evidence, or **`ESCALATE`** genuine product trade-offs to the user.
5. **Approval Gate (`Approve | Revise | Refine`)**:
   - Present the chapter/task blueprint summary table, Review Adjudication Ledger, and `Approve | Revise | Refine`. Upon approval, stamp `status: stable` and `plan_commit: <HEAD_SHA>` across root `spec.md`, all chapter `spec.md` files, and all `tasks/*.md`, update `.agents/bundles/index.md` and `log.md`, and hand off to `/flow:implement <flow_id>` (which executes one chapter per run).

## Guardrails

- **No Production Code During Planning**: Modify files exclusively under `.agents/bundles/` (or untracked `.agents/scratch/<slug>/` during a throwaway prototype spike).
- **Zero Scope Truncation & Zero Historical Sediment**: Never compress distinct capabilities or omit `docs/**` / OKF knowledge chapters to fit `1–4` tasks—add chapters instead—and never place `Revision History` sections, struck-through bullets, or standalone `---` horizontal rules inside bundle Markdown bodies.
- **Symbol-Anchored Targets & Canonical Tests**: Anchor all targets to `path/to/file::Symbol` (never fragile line numbers) and place all planned tests at confirmed public seams inside existing canonical module test files.

## Output

Return the root `spec.md` path, full chapter and task blueprint summary table (`Chapter | Task ID | Strategy | Read Set / Owned Files & Canonical Tests`), `[0/N files documented]` manifest summary, Review Adjudication Ledger (`ADOPT` / `CONTEST` / `ESCALATE`), and the `Approve | Revise | Refine` gate.

## Validation

Confirm root `spec.md`, frontmatter-free `chapters/index.md` (when multi-chapter), every `chapters/<ch_id>/spec.md`, and every 8-section `tasks/<id>-<slug>.md` carry valid OKF v0.2 frontmatter and `sources:`/`[^id]:` provenance, `plan_revision` matches across all specs and tasks, `<= 4` tasks exist per chapter (`read_set <= 6`, `estimated_loc <= 250`), every code and doc/OKF requirement maps to a task and verification surface, and zero body `---` separators or historical prose exist.
