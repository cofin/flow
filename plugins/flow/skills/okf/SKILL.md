---
name: okf
description: "Use when creating, validating, tagging, structuring, or maintaining Open Knowledge Format (OKF v0.2) bundles, concept documents, frontmatter, and knowledge catalogs."
---

# Open Knowledge Format (OKF)

Author, validate, tag, and structure Open Knowledge Format (OKF v0.2) knowledge bundles and concept documents.

<workflow>

## Workflow

1. **Resolve Bundle Layout**: Locate the bundle root (default `.agents/bundles/` or configured `bundles_dir`) and confirm `index.md` carries `okf_version: "0.2"`.
2. **Structure Concept Documents**: Author every concept document as a UTF-8 markdown file with a valid YAML frontmatter block starting with `---` and closing with `---`.
3. **Declare Required and Recommended Frontmatter**:
   - `type`: REQUIRED non-empty string identifying the concept kind (`Guide`, `Pattern`, `Spec`, `Task`, `BigQuery Table`, `API Endpoint`, `Playbook`, `Metric`, etc.).
   - `title`: Display name.
   - `description`: Single sentence summary.
   - `resource`: Canonical URI when describing a concrete asset.
   - `tags`: List of concise, lowercase hyphenated strings (`[tag1, tag2]`) for cross-cutting discovery.
4. **Enforce State vs Status Invariants**:
   - Flow workflow state lives in `state:` (`planned|active|completed` for Spec; `open|in_progress|closed|blocked|skipped` for Task).
   - OKF document lifecycle lives in `status:` (`draft|stable|deprecated`). Never mix workflow state into `status:`.
5. **Maintain Bundle Integrity**: Update directory `index.md` progressive disclosure tables and append update summaries to `log.md`.

</workflow>

<guardrails>

## Guardrails

- Every non-reserved `.md` file MUST have a parseable YAML frontmatter block with a non-empty `type:`.
- Reserved filenames (`index.md`, `log.md`) must follow their structural standards.
- Never store workflow state in `status:`.
- Tags must be a YAML list of strings, never a plain string or comma-separated scalar.
- Consumers tolerate unknown `type` values and extra producer-defined fields; do not reject valid custom metadata.

</guardrails>

## Output

Return the created or validated concept documents, frontmatter schemas, applied tags, resolved bundle hierarchy, and validation diagnostic summary.

<validation>

## Validation

Verify that:

1. Bundle root `index.md` carries `okf_version: "0.2"`.
2. All non-reserved markdown files have valid YAML frontmatter with non-empty `type:`.
3. Tags are valid list-of-strings arrays.
4. All markdown links resolve within the bundle or repository.
5. No workflow states appear in `status:`.

</validation>

<example>

## Example

For a new data asset concept, author `bundles/tables/orders.md` with:

```yaml
---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
---

# Schema

| Column | Type | Description |
|---|---|---|
| `order_id` | STRING | Primary key |
```

And add an entry to `bundles/tables/index.md` and `bundles/log.md`.

</example>

## References

- [OKF Specification Reference](references/spec.md) — complete OKF v0.2 specification.
- [Frontmatter and Tagging Guide](references/frontmatter-and-tagging.md) — templates, tagging taxonomies, and field rules.
- [Flow State Contract](../flow/references/state.md) — Flow lifecycle state operations.
