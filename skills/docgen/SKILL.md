---
name: docgen
description: "Use when generating documentation, writing API docs, documenting modules or components, creating README content, building reference guides, or documenting many files with explicit coverage tracking."
---

# Docgen

Generate complete documentation from inspected source with explicit coverage
tracking. Use standalone or as the analysis engine for Flow documentation work.

<workflow>

## Workflow

1. Load the documentation strategy and component template below.
2. Execute the manifest-driven coverage workflow against the exact source scope.
3. Cross-reference the documented components and synthesize the requested
   consumer-facing document.

</workflow>

<guardrails>

## Guardrails

Read every in-scope file. Do not infer behavior from names, skip small files,
or claim completeness while manifest entries remain unresolved.

</guardrails>

## Output

Return the completed/total manifest count, module overview, scaled
per-component documentation, verified cross-references, usage examples, and a
dependency map when the scope contains multiple components.

<validation>

## Validation

Confirm every manifest item is covered and every documentation claim comes
from freshly inspected source.

</validation>

<example>

## Example

For a four-file module, report `[4/4 files documented]`, describe each public
interface, and show the verified dependency direction between components.

</example>

## References

- [Docgen strategy](references/docgen-strategy.md) — coverage workflow and progress rules.
- [Component template](references/component-template.md) — generated document structure.
