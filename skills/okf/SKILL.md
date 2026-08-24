---
name: okf
description: "Use when creating, editing, validating, or structuring Open Knowledge Format (OKF v0.2) bundle files (.agents/bundles/), YAML frontmatter, or knowledge catalogs."
---

# Open Knowledge Format (OKF)

Author, validate, tag, and structure Open Knowledge Format (OKF v0.2) knowledge bundles and hierarchical concept documents.

## Materialization Contract

<!-- okf-materialization-contract: start -->
```yaml
default_scaffold:
  - bundles/index.md
  - bundles/log.md
  - bundles/product/product.md
  - bundles/product/tech-stack.md
  - bundles/knowledge/index.md
  - bundles/knowledge/workflow.md
repository_evidence:
  applies_to: [architecture, data-model, domain, pattern, standard]
  required: [repository_relative_paths, symbols_or_observed_behavior]
decision_evidence:
  applies_to: [decision, rejected-alternative]
  required: [explicit_user_decision, recorded_at, actor]
path_policy:
  shape: repository_derived_hierarchy
  nested_paths: preserve
  unknown_types: tolerate
  rerun: idempotent_without_duplicate_or_overwrite
  links: resolve_before_commit
tags:
  optional_by_okf: true
  required_by_profile: non_empty_lowercase_hyphenated_strings
  empty_list_satisfies_required: false
archive:
  resident_spec_directories: forbidden
  effect: knowledge_synthesis_log_append_and_completed_spec_removal
```
<!-- okf-materialization-contract: end -->

Setup creates only the default scaffold. Do not pre-create optional namespace
directories. Materialize architecture, data-model, domain, pattern, or standard
chapters only after inspecting named repository-relative paths and recording
the symbols or observed behavior that support each fact. Materialize a decision
only from a recorded explicit user decision with its actor and timestamp;
record rejected alternatives inside that decision rather than in a separate
rejections tree. A placeholder, inferred layering convention, sample schema,
invented glossary term, or sample ADR is not evidence.

Materialize reusable conventions at `knowledge/patterns/<topic>.md` only from
the same repository evidence. Continue to tolerate an existing legacy
`knowledge/patterns.md`, but do not create or advertise that catch-all path.

Derive chapter paths from the project rather than a fixed taxonomy, preserve
nested paths on reruns, and never replace customized content. Validate links
before committing an index update. Unknown concept `type:` values remain valid
OKF and must be tolerated by consumers.

## Hierarchical Layout Standard

OKF bundles under `.agents/bundles/` organize knowledge into scope-derived subdirectories:

```text
.agents/bundles/
  index.md                      # Bundle root index with okf_version: "0.2"
  log.md                        # Date-grouped change history (ISO dates)
  product/                      # Identity documents: product.md, tech-stack.md
  knowledge/                    # Evidence-backed, project-shaped knowledge:
    workflow.md                 # Canonical commands and development workflow
    patterns/<topic>.md         # Reusable convention
    architecture/<area>.md      # System boundary or data flow
    domains/<domain>.md         # Domain model and vocabulary
    data-model/<area>.md        # Schema and migration facts
    decisions/<decision>.md     # Decision and rejected alternatives
    standards/<topic>.md        # Repository standard
  research/                     # Pre-PRD technical research notes
  specs/<flow_id>/              # Active Flow specifications and task worksheets
```

Every optional namespace above is lazy: create its directory only when the
first evidence-backed chapter is materialized.

Archive contracts knowledge and removes completed spec directories. It does
not create a resident `archive/<year>/<flow_id>/` tree.

## Frontmatter Schema Standard

Every concept document carries a YAML frontmatter block:

```yaml
---
type: <non-empty producer-defined concept type>
id: "scope:identifier"          # Optional unique identifier
title: Display Name
description: Single sentence summary
scope: architecture | data-model | domain | lifecycle
domain: core | auth | billing
parent: "parent-doc-id"         # Optional parent hierarchy pointer
supersedes: "old-doc-id"        # Optional replacement pointer for revised knowledge
tags: [tag1, tag2]              # Optional in OKF; non-empty when a profile requires relevance
status: draft | stable | deprecated # OKF document maturity
state: planned | active | completed # Spec workflow state only
# Task state: open | in_progress | closed | blocked | skipped
---
```

## Workflow

1. **Resolve Bundle Layout**: Confirm root `index.md` carries `okf_version: "0.2"`.
2. **Structure Concept Documents**: Place files in their scope-derived directory under `knowledge/`.
3. **Declare Frontmatter**: Set non-empty `type:` and supported metadata. When
   the active profile requires relevance tags, provide at least one lowercase,
   hyphenated tag; `tags: []` does not satisfy that requirement.
4. **Enforce State vs Status**:
   - Task workflow state lives strictly in `state:`.
   - Document lifecycle lives in `status:`. Never mix workflow state into `status:`.
5. **Progressive Disclosure**: Update local `index.md` tables and log updates in `log.md`.

## Guardrails

- Every non-reserved `.md` file must have valid YAML frontmatter with a non-empty `type:`.
- Reserved files (`index.md`, `log.md`) require no frontmatter.
- Tags, when present, must be a YAML array of lowercase, hyphenated strings
  (`tags: [auth, jwt]`). A policy requiring relevant tags requires a non-empty
  array.
- Do not create unmanaged flat files at the root of `bundles/` or `knowledge/`.
- Do not create architecture, data, domain, decision, rejection, or archive
  content from templates alone.

## Output

Return created or validated concept documents, frontmatter schemas, applied tags, and validation status.

## Validation

Verify that root `index.md` carries `okf_version: "0.2"`, markdown files carry valid frontmatter, and all tags are arrays of strings.

## Example

After observing `src/scheduler.py` and its tests, author a project-shaped
`knowledge/components/scheduler.md` concept that records those evidence paths,
then add a resolving link to `knowledge/index.md`.

## References

- [OKF Specification Reference](references/spec.md)
- [Frontmatter and Tagging Guide](references/frontmatter-and-tagging.md)
- [Flow State Contract](../flow/references/state.md)
