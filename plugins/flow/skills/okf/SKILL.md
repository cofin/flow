---
name: okf
description: "Use when creating, editing, validating, or structuring Open Knowledge Format (OKF v0.2) bundle files (.agents/bundles/), YAML frontmatter, or knowledge catalogs."
---

# Open Knowledge Format (OKF)

Author, validate, tag, and structure Open Knowledge Format (OKF v0.2) knowledge bundles and hierarchical concept documents.

## Hierarchical Layout Standard

OKF bundles under `.agents/bundles/` organize knowledge into scope-derived subdirectories:

```text
.agents/bundles/
  index.md                      # Bundle root index with okf_version: "0.2"
  log.md                        # Date-grouped change history (ISO dates)
  product/                      # Identity documents: product.md, tech-stack.md
  knowledge/                    # Categorized knowledge base:
    workflow.md                 # Canonical commands and development workflow
    patterns.md                 # Elevated conventions and gotchas
    architecture/               # System design, module boundaries, data flow
    data-model/                 # Domain entities, database schemas, migrations
    domains/<name>/             # Domain-specific models and ubiquitous glossaries
    decisions/                  # Single-paragraph Architecture Decision Records (ADRs)
    rejections/                 # Durable out-of-scope catalog (Rejection Memory)
  research/                     # Pre-PRD technical research notes
  specs/<flow_id>/              # Active Flow specifications and task worksheets
  archive/<year>/<flow_id>/     # Compact archived flows
```

## Frontmatter Schema Standard

Every concept document carries a YAML frontmatter block:

```yaml
---
type: Spec | Task | Guide | Pattern | Decision | Rejection | Research | Skill
id: "scope:identifier"          # Optional unique identifier
title: Display Name
description: Single sentence summary
scope: architecture | data-model | domain | lifecycle
domain: core | auth | billing
parent: "parent-doc-id"         # Optional parent hierarchy pointer
supersedes: "old-doc-id"        # Optional replacement pointer for revised knowledge
tags: [tag1, tag2]              # Lowercase hyphenated tags for search
status: draft | stable | deprecated # OKF document maturity
state: open | in_progress | closed | blocked | skipped # Task workflow state only
---
```

## Workflow

1. **Resolve Bundle Layout**: Confirm root `index.md` carries `okf_version: "0.2"`.
2. **Structure Concept Documents**: Place files in their scope-derived directory under `knowledge/`.
3. **Declare Frontmatter**: Set non-empty `type:`, `title:`, `description:`, and relevant `tags: []`.
4. **Enforce State vs Status**:
   - Task workflow state lives strictly in `state:`.
   - Document lifecycle lives in `status:`. Never mix workflow state into `status:`.
5. **Progressive Disclosure**: Update local `index.md` tables and log updates in `log.md`.

## Guardrails

- Every non-reserved `.md` file must have valid YAML frontmatter with a non-empty `type:`.
- Reserved files (`index.md`, `log.md`) require no frontmatter.
- Tags must be a YAML array of lowercase strings (`tags: [auth, jwt]`).
- Do not create unmanaged flat files at the root of `bundles/` or `knowledge/`.

## Output

Return created or validated concept documents, frontmatter schemas, applied tags, and validation status.

## Validation

Verify that root `index.md` carries `okf_version: "0.2"`, markdown files carry valid frontmatter, and all tags are arrays of strings.

## Example

For a new system architecture chapter, author `knowledge/architecture/overview.md` with `type: Guide` frontmatter and add it to `knowledge/index.md`.

## References

- [OKF Specification Reference](references/spec.md)
- [Frontmatter and Tagging Guide](references/frontmatter-and-tagging.md)
- [Flow State Contract](../flow/references/state.md)
