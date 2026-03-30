---
name: docgen
description: "Auto-activate when generating documentation, writing API docs, documenting modules or components, creating README content, building reference guides, or systematically documenting a codebase. Use when: documenting multiple files or components, ensuring complete coverage of a module, generating structured docs from code, or when /flow-docs needs systematic file-by-file analysis."
---

# Docgen

## Overview

Systematic documentation generation with progress tracking and completeness guarantees. Analyzes code file-by-file, ensures nothing is skipped, and produces structured output per component.

Docgen complements `flow-docs` — it provides the systematic analysis engine for flow-docs' five-phase workflow. It can also be used standalone for ad-hoc documentation tasks when you need structured, complete documentation without a full flow-docs run.

The core guarantee: every file in scope gets documented. Progress is tracked explicitly (`[3/12 files documented]`) so you always know what's been covered and what remains.

## Usage Patterns

- "Document the authentication module"
- "Generate API reference docs for this package"
- "I need complete docs for everything in src/services/"
- "What does this module do and how do I use it?" (single-component mode)

## References

- [`references/docgen-strategy.md`](references/docgen-strategy.md) — Five-step documentation workflow: scope target, build file manifest, analyze each file, cross-reference, synthesize. Includes progress tracking guidance and anti-patterns.
- [`references/component-template.md`](references/component-template.md) — Per-component documentation structure with scaling guidance for utilities, services, and config files.
