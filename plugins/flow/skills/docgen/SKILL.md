---
name: docgen
description: "Use when generating structured API references, component documentation, or README guides across a batch of files using an explicit coverage manifest."
---

# Documentation Generator

Generate accurate, structured component documentation, API reference guides, and system overviews directly from codebase source truth.

## Workflow

1. **Build Coverage Manifest**: List target source files to document.
2. **Extract Symbol Metadata**: Inspect classes, methods, docstrings, type annotations, and module exports.
3. **Generate Documentation**: Write Component Overview, Public API Reference, and configuration tables.
4. **Verify Links & Syntax**: Confirm all code fences, markdown links, and symbol names are valid.

## Guardrails

- Document actual signatures and return types directly from source files.
- Track documented files via an explicit manifest to ensure complete coverage.

## Output

Return structured Markdown documentation with accurate type signatures and runnable examples.

## Validation

Verify that all documented symbols and relative file links exist and resolve accurately.

## Example

Generate a markdown reference for a service module, extracting public functions, argument types, and docstrings.
