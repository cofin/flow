# Flow Research & Throwaway Prototyping (`/flow:research`, alias `/flow:task`)

Conduct primary-source technical research across codebases, external SDK/protocol documentation, or time-boxed throwaway prototypes in `.agents/scratch/<slug>/`, and promote validated findings into `.agents/bundles/research/<topic>_<YYYYMMDD>.md` or `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`.

## 1. Sharded Read-Only Scouts & Primary-Source Research Contract

<!-- research-fanout-contract: proportional-v1 -->
```yaml
scout_digest:
  when: more_than_two_source_files | at_least_two_modules
  count: one_per_subsystem_or_module_family
  payload: SubsystemDigest
  model: inherit
researcher:
  when: at_least_two_independent_unknowns | current_external_evidence_required
  count: one_per_independent_unknown_or_source_domain
  model: inherit
exploratory_spike:
  scratch_dir: .agents/scratch/<slug>/
  tracked_writes: forbidden_in_scratch
  promotion: distill_findings_to_research_or_spec_and_delete_scratch
otherwise: direct_file_reads_for_one_or_two_files_in_single_module
```

1. **Bounded Direct Reads (`<= 2` Files in One Module)**: Only read source files directly in the coordinator when the question is confined to `1–2` files inside a single module.
2. **Sharded `SubsystemDigest` Scouts (`> 2` Files or `>= 2` Modules)**:
   - Keep the planning coordinator under `< 25k` exploration tokens by dispatching parallel read-only `@researcher` Scouts (`1` per subsystem) returning the `SubsystemDigest` schema defined in [`../../../agents/researcher.md`](../../../agents/researcher.md): `symbols` (`path/to/file::Symbol`), `exact_signatures`, `seams_and_dependency_categories`, `canonical_tests_and_fixtures`, `edge_cases_and_gotchas`, `affected_docs_and_okf_chapters`, and `open_design_forks`.
3. **Parallel Primary-Source `@researcher` Fan-Out**:
   - When investigating `>= 2` independent unknowns or external SDK/API primary sources (official docs, changelogs, migration guides, release notes), dispatch `@researcher` subagents (`model: inherit`).
   - Follow every claim back to the primary source that owns it—never rely on secondary blog summaries or unverified memory.
   - On Google Antigravity (`run_workflow` / `invoke_subagent`), always dispatch with `type_name="self"` and `model="inherit"` pointing to `agents/researcher.md` (`schema=RESEARCH_RESULT_SCHEMA` when using `run_workflow` `parallel()`), and check `git status --porcelain` after completion to confirm zero working-tree mutations.

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

Write the validated research note to `.agents/bundles/research/<topic>_<YYYYMMDD>.md` (or directly to `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md` when scoped to an active/planned flow), pairing every `sources:` entry with a matching `[^id]:` body footnote and zero standalone `---` horizontal rules in the Markdown body:

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

Include a concise `<= 40`-line `<!-- truth: start --> ... <!-- truth: end -->` block at the top of the body and cite every verified claim with `[^primary-1]` footnotes resolved at the bottom of the document.

## 4. Promotion & Contraction Contract

- **Promotion into a Spec**: When `/flow:prd` or `/flow:plan` adopts a research note from `.agents/bundles/research/<topic>_<YYYYMMDD>.md`, move it into `.agents/bundles/specs/<flow_id>/research/<topic>_<YYYYMMDD>.md`, set `state: promoted` and `promoted_to: <flow_id>`, update frontmatter-free `research/index.md` if present, and add its path to `research: [...]` in root/chapter `spec.md`. `.agents/bundles/research/` holds un-promoted research only.
- **Contraction into Knowledge**: When `/flow:implement` (chapter closeout), `/flow:learn`, or `/flow:archive` synthesizes durable knowledge, verified facts from `specs/<flow_id>/research/*.md` are folded into `.agents/bundles/knowledge/**` chapters in present tense with `sources:` + `[^id]:` provenance footnotes.
