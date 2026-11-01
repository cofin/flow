# Flow Research & Throwaway Prototyping (`/flow:research`, alias `/flow:task`)

Conduct primary-source technical research across codebases, external SDK/protocol documentation, or time-boxed throwaway prototypes in `.agents/scratch/<slug>/`, and promote validated findings into `.agents/bundles/research/<topic>_<YYYYMMDD>.md` or `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`.

## 1. Proportional Research Dispatch Contract

<!-- research-fanout-contract: proportional-v1 -->
```yaml
researcher:
  when: at_least_two_independent_unknowns | current_external_evidence_required
  count: one_per_independent_unknown_or_source_domain
  model: inherit
exploratory_spike:
  scratch_dir: .agents/scratch/<slug>/
  tracked_writes: forbidden_in_scratch
  promotion: distill_findings_to_research_or_spec_and_delete_scratch
otherwise: direct_file_reads_zero_extra_subagents
```

1. **Direct Reads First (`0` Subagents)**: Answer single-subsystem repository questions directly with file read and search tools.
2. **Parallel Read-Only `@researcher` Fan-Out**:
   - When investigating `>= 2` independent unknowns or external SDK/API primary sources (official docs, changelogs, migration guides, release notes), dispatch `@researcher` subagents (`model: inherit`).
   - Follow every claim back to the primary source that owns it—never rely on secondary blog summaries or unverified memory.
   - When the `run_workflow` tool is available in the active harness (Google Antigravity), fan out `parallel(questions, run_researcher)` using `agent(type_name="researcher", schema=RESEARCH_RESULT_SCHEMA, model="inherit")` so each researcher returns schema-validated citations and findings.

## 2. Throwaway Prototyping & Ephemeral Spikes (`/flow:task` Alias)

A prototype is **throwaway code that answers a design question** before locking a specification. Never write prototype code into production files.

### Pick the Prototype Branch by Question

1. **"Does this state model, algorithm, or logic feel right?" (Logic / State Prototype)**:
   - Build a single self-contained script, benchmark, or interactive HTML file inside `.agents/scratch/<slug>/` (with free-play state transitions and guided scenario walkthroughs) that exercises edge cases hard to reason about on paper.
2. **"What should this UI or CLI interaction look like?" (UI / Ergonomics Prototype)**:
   - Generate 2–3 radically different variations switchable via a parameter or toggle inside `.agents/scratch/<slug>/` so the user can compare ergonomics directly.

### Prototype Discipline Rules

- **Untracked Scratch Location Only**: All spike files live in `.agents/scratch/<slug>/` (`notes.md`, `findings.md`, and prototype scripts). `.agents/scratch/` is untracked and never committed to `main`.
- **Trivial to Run & In-Memory State**: Start from a single command (or double-clicking an HTML file), keep state in memory, skip polish/abstractions, and print or render full state after every transition.
- **Explicit Resolution (`Promote`, `Keep Notes`, or `Discard`)**:
  - **Promote to Spec/PRD**: Fold the validated decision into `spec.md` (`/flow:plan` or `/flow:prd`), document the rejected alternatives, and delete `.agents/scratch/<slug>/`.
  - **Keep Research Notes**: Distill empirical findings into a well-formed OKF Research document (`.agents/bundles/research/<topic>_<YYYYMMDD>.md`), then delete `.agents/scratch/<slug>/` and reset any working tree edits (`git checkout -- .`). Never move raw `findings.md` into `bundles/` as-is.
  - **Discard**: Delete `.agents/scratch/<slug>/` and restore a clean working tree.

## 3. Result Validation & OKF v0.2 Research Schema

Every `@researcher` subagent returns the `structured-result-v1` payload defined in [`../../../agents/researcher.md`](../../../agents/researcher.md). Before writing the research document, verify that:

- Every finding ID cites at least one concrete `path/to/file::Symbol` or primary-source URL.
- Confidence (`high`, `medium`, `low`) and limitations are stated explicitly.
- Contradictions between sources are preserved and resolved with evidence or surfaced for a user decision.

Write the validated research note to `.agents/bundles/research/<topic>_<YYYYMMDD>.md` (or directly to `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` when scoped to an active/planned flow):

```yaml
---
type: Research
research_id: "topic-slug-20261101"
title: "Primary-Source Audit: <Topic>"
description: "Single-sentence summary of the verified findings and architectural conclusion."
scope: architecture | domain | integration
status: stable
state: open                     # open | promoted
promoted_to: null               # <flow_id> once adopted by a spec
tags: [research, <domain>]
generated:
  by: flow/0.26.0
  at: 2026-11-01T00:00:00Z
verified:
  - by: agent:researcher
    at: 2026-11-01T00:00:00Z
sources:
  - id: primary-1
    resource: src/module.py::SymbolName
    title: Primary source implementation
---
```

## 4. Promotion & Contraction Contract

- **Promotion into a Spec**: When `/flow:prd` or `/flow:plan` adopts a research note from `.agents/bundles/research/<topic>_<YYYYMMDD>.md`, move it into `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`, set `state: promoted` and `promoted_to: <flow_id>`, and add its path to `research: [...]` in `spec.md`. `.agents/bundles/research/` holds un-promoted research only.
- **Contraction into Knowledge**: When `/flow:learn` or `/flow:archive` contracts a completed flow, durable facts from `specs/<flow_id>/research/*.md` are synthesized into `.agents/bundles/knowledge/**` chapters with `sources:` citations before the completed spec directory is removed.
