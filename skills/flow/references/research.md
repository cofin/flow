# Flow Research (`/flow:research`, alias `/flow:task`)

Conduct primary-source technical research across codebases, external SDK/protocol documentation, or time-boxed exploratory spikes, and promote validated findings into `.agents/bundles/research/<topic>_<YYYYMMDD>.md` or `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`.

## Proportional Dispatch Contract

<!-- research-fanout-contract: proportional-v1 -->
```yaml
researcher:
  when: at_least_two_independent_unknowns | current_external_evidence_required
  count: one_per_independent_unknown_or_source_domain
  model: inherit
exploratory_spike:
  scratch_dir: .agents/scratch/<slug>/
  tracked_writes: forbidden_in_scratch
  promotion: distill_findings_to_research_md_and_delete_scratch
otherwise: direct_file_reads_zero_extra_subagents
```

1. **Direct Reads First (`0` Subagents)**: Answer single-subsystem repository questions directly with file read and search tools.
2. **Parallel Read-Only `@researcher` Fan-Out**:
   - When investigating `>= 2` independent unknowns or external SDK/API primary sources, dispatch `@researcher` subagents (`model: inherit`).
   - When the `run_workflow` tool is available in the active harness (Google Antigravity), fan out `parallel(questions, run_researcher)` using `agent(type_name="researcher", schema=RESEARCH_RESULT_SCHEMA, model="inherit")` so each researcher returns schema-validated citations and findings.
3. **Time-Boxed Exploratory Spikes (`/flow:task` alias)**:
   - When a design question requires a throwaway prototype or benchmark to verify runtime behavior, place all temporary spike files inside untracked `.agents/scratch/<slug>/`.
   - Never modify production source files during a research spike. Once the spike answers the question, record the empirical evidence in the research document and delete `.agents/scratch/<slug>/`.

## Result Validation & Adoption

Every `@researcher` subagent returns the `structured-result-v1` payload defined in [`agents/researcher.md`](../../../agents/researcher.md). Before writing the research document, the parent agent verifies that:

- Every finding ID is supported by at least one concrete `path/to/file::Symbol` or primary-source URL citation.
- Confidence (`high`, `medium`, `low`) and limitations are stated explicitly.
- Contradictions between sources are preserved and either resolved with evidence or surfaced for a user decision.

## Research Document Schema (`OKF v0.2`)

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

## Promotion & Contraction Contract

- **Promotion into a Spec**: When `/flow:prd` or `/flow:plan` adopts a research note from `.agents/bundles/research/<topic>_<YYYYMMDD>.md`, move it into `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`, set `state: promoted` and `promoted_to: <flow_id>`, and add its path to `research: [...]` in `spec.md`.
- **Contraction into Knowledge**: When `/flow:learn` or `/flow:archive` contracts a completed flow, durable facts from `specs/<flow_id>/research/*.md` are synthesized into `.agents/bundles/knowledge/**` chapters with `sources:` citations.
