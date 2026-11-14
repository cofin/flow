---
name: okf
description: "Use when creating, editing, validating, or structuring Open Knowledge Format (OKF v0.2) bundle files (.agents/bundles/), YAML frontmatter, Attested Computations, provenance footnotes, or Google Cloud Knowledge Catalog okf-bundle trees."
---

# Open Knowledge Format (OKF v0.2)

Author, validate, tag, and structure Open Knowledge Format (`OKF v0.2`) knowledge bundles (`.agents/bundles/`) compatible with both local agent workflows and the Google Cloud Knowledge Catalog (`okf-bundle` aspect).

## Materialization Contract

<!-- okf-materialization-contract: start -->
```yaml
okf_version: "0.2"
default_scaffold:
  - bundles/index.md
  - bundles/log.md
  - bundles/product/index.md
  - bundles/product/product.md
  - bundles/product/product-guidelines.md
  - bundles/product/tech-stack.md
  - bundles/knowledge/index.md
  - bundles/knowledge/workflow.md
provenance_contract:
  required_for: [architecture, data-model, domain, pattern, standard, testing, gotcha, research]
  sources_schema:
    - id: string
      resource: string
      title: string
  inline_citations: markdown_footnotes_matching_source_id
trust_and_generation:
  generated: { by: "<producer>/<version>", at: "YYYY-MM-DDTHH:MM:SSZ" }
  verified:
    - by: "<actor>"
      at: "YYYY-MM-DDTHH:MM:SSZ"
      commit: "<git_sha_optional>"
truth_block:
  markers: ["<!-- truth: start -->", "<!-- truth: end -->"]
  max_lines: 40
archive:
  resident_spec_directories: forbidden
  effect: knowledge_synthesis_log_append_and_completed_spec_removal
```
<!-- okf-materialization-contract: end -->

## Hierarchical Bundle Layout (`.agents/bundles/`)

```text
.agents/bundles/
├── index.md                        # Root bundle manifest (okf_version: "0.2" in frontmatter or header)
├── log.md                          # Append-only lifecycle changelog (newest ISO date first; no frontmatter required)
├── product/                        # Product vision, engineering tenets, and tech stack
│   ├── index.md
│   ├── product.md
│   ├── product-guidelines.md
│   └── tech-stack.md
├── knowledge/                      # Hierarchical OKF v0.2 knowledge base
│   ├── index.md
│   ├── workflow.md                 # Canonical build, lint, typecheck, test, and release gates
│   ├── architecture/<area>.md      # Subsystem boundaries, dataflow, concurrency, IPC/RPC contracts
│   ├── patterns/<topic>.md         # Language/framework idioms, class layout, serialization conventions
│   ├── domains/<domain>.md         # Domain vocabulary, invariants, adapters, and business rules
│   ├── testing/<topic>.md          # Test matrix, fixture patterns, SUT integrity rules
│   ├── gotchas/<area>.md           # Non-obvious footguns, runtime traps, platform quirks
│   └── decisions/adr-NNN-<slug>.md # Architectural Decision Records (context, decision, rejected alternatives)
├── research/                       # Project-wide promoted primary-source research notes
│   ├── index.md
│   └── <topic>_<YYYYMMDD>.md
└── specs/                          # Active Flow Specifications & Chaptered Roadmaps
    ├── index.md                    # Frontmatter-free directory catalog
    └── <flow_id>/
        ├── spec.md                 # Root Full-Plan Roadmap OR Single-Chapter Spec (type: Spec)
        ├── learnings.md            # Implementation discoveries awaiting promotion to knowledge/
        ├── research/<topic>.md     # Spec-scoped primary-source research (type: Research)
        ├── tasks/<id>-<slug>.md    # Single-chapter task worksheets (1-4 tasks; type: Task)
        └── chapters/               # Multi-chapter decomposition (2..N chapters, zero upper cap)
            ├── index.md            # Frontmatter-free chapter catalog
            └── ch01-<slug>/
                ├── spec.md         # Chapter specification (type: Spec)
                └── tasks/<id>-<slug>.md # Chapter task worksheets (1-4 tasks; type: Task)
```

## Concept Frontmatter & Provenance Schema (`OKF v0.2` + Knowledge Catalog)

Every non-reserved `.md` file (`index.md` and `log.md` are reserved) begins with YAML frontmatter:

```yaml
---
type: Pattern                       # REQUIRED: non-empty concept type (Pattern, Architecture, Domain, Guide, Decision, Research, Spec, Task, Attested Computation, BigQuery Table, etc.)
title: Centralized JSON Serialization
description: Route all JSON encoding and decoding through msgspec serializer helpers.
status: stable                      # Document lifecycle ONLY: draft | stable | deprecated (never workflow state)
tags: [serialization, msgspec, json]
generated:
  by: flow/0.26.0
  at: 2026-11-01T00:00:00Z
verified:
  - by: agent:flow-learn
    at: 2026-11-01T00:00:00Z
    commit: 164b07f
sources:
  - id: serializer-mod
    resource: src/core/serialization.py::encode_json
    title: Canonical msgspec JSON serializer module
---
```

### Bounded `<!-- truth: start -->` Block & Footnote Citations

Place a bounded (`<= 40` lines) machine-checkable invariant block at the top of each knowledge chapter or project skill, and anchor body claims to `sources[].id` via standard Markdown footnotes (`[^serializer-mod]`):

```markdown
<!-- truth: start -->
- Route all JSON encoding/decoding through `encode_json` and `decode_json` in `src/core/serialization.py`[^serializer-mod].
- Never call `json.dumps` or `json.loads` directly in adapter or controller modules.
<!-- truth: end -->

[^serializer-mod]: `src/core/serialization.py::encode_json` — Canonical msgspec JSON serializer module.
```

## Workflow

1. **Scaffold or Inspect the Bundle Root (`.agents/bundles/` or `catalog.yaml` + `bundle/`)**:
   - Ensure root `index.md` declares `okf_version: "0.2"` (and `bundle: <repo-slug>` for Flow bundles; `kcmd --format okf` `catalog.yaml` + `bundle/{agents,assets,documents,_links.yaml}` trees may use `catalog.yaml` scope without `bundle:`), and `log.md` records ISO-dated lifecycle events (`setup`, `synthesize`, `verify`, `archive`).
2. **Author Evidence-Backed Concept Chapters**:
   - Place each concept in its domain directory (`product/`, `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/`, `research/`, or `specs/<flow_id>/`) with YAML frontmatter (`type`, `title`, `description`, `status`, `tags`, `generated`, `verified`, `sources`).
   - Add a bounded `<= 40`-line `<!-- truth: start -->` block at the top of the body and cite every `sources[].id` entry via a matching `[^id]` footnote.
3. **Validate Bundle Integrity**:
   - Verify all relative links in `index.md` files resolve on disk, reserved files (`index.md`, `log.md`) omit concept-only keys (`type`, `status`, `sources`), and completed specs are contracted into `knowledge/**` upon `/flow:archive`.

## Guardrails

- **State vs. Status Invariant**: Workflow state (`draft`, `planned`, `active`, `completed` on `Spec`; `pending`, `in_progress`, `completed`, `blocked`, `deferred` on `Task`) lives strictly in `state:`. Document maturity (`draft`, `stable`, `deprecated`) lives strictly in `status:`. Never mix them.
- **Reserved Files & Body Delimiters**: Root `bundles/index.md` carries `okf_version: "0.2"` and `bundle: <repo-slug>` (unless `catalog.yaml` supplies scope), whereas every subdirectory `index.md` (`product/index.md`, `knowledge/index.md`, `specs/index.md`, `specs/<flow_id>/chapters/index.md`) and `log.md` carry **zero YAML frontmatter**. Never place standalone `---` horizontal rules inside `.agents/bundles/**/*.md` bodies so strict OKF YAML frontmatter splitters parse cleanly.
- **Knowledge Catalog Exclusions & Size Budget**: Set `catalog_publish: false` in frontmatter, add globs to `catalog.yaml` (`catalog_exclude:` / `exclude:`), or place a `.kc-no-export` marker file to omit private files/subtrees from catalog ingestion; keep non-excluded overviews at or below `120,832` HTML-safe JSON-escaped bytes (`<`, `>`, `&` expanded) when `knowledge_catalog.enabled` is true.
- **Zero Chronological Sediment**: Keep concept chapters, root `specs/<flow_id>/spec.md`, `chapters/index.md`, and `chapters/<ch_id>/spec.md` synchronized in place in present tense (current verified state, remaining chapters, and full plan) as chapters finish or revise; record chronological history exclusively in `log.md` and Git commits.
- **Single-Sentence Chapter Scope**: Whenever a knowledge chapter requires more than one crisp sentence in `description:` or exceeds `~200` lines, split it into focused nested chapters and link them from the parent `index.md`.

## Validation

Confirm `/flow:validate` passes on `.agents/bundles/`, every non-reserved `.md` file has `type`, `title`, and `description`, and every `sources[].id` resolves to a `[^id]:` footnote in the document body.

## Output

Produce valid OKF v0.2 Markdown documents, `index.md` catalogs, and `log.md` audit entries.

## References

- [OKF v0.2 Specification Reference](references/spec.md)
- [Frontmatter and Tagging Guide](references/frontmatter-and-tagging.md)
- [Flow State Contract](../flow/references/state.md)
