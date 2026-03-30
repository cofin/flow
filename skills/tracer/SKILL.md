---
name: tracer
description: "Auto-activate when tracing execution paths, mapping dependencies, understanding unfamiliar code, following data flow through a system, investigating how a feature works end-to-end, or when debugging requires understanding call chains. Use when: need to understand how code flows from entry point to result, mapping what depends on what, exploring unfamiliar codebases systematically, or when reading random files isn't building understanding."
---

# Tracer

## Overview

Systematic code exploration that builds understanding incrementally by tracing execution paths and mapping dependencies, rather than randomly reading files. Start at a known entry point and follow connections outward, building a map as you go.

## Complements

- **systematic-debugging** — provides the "understand the system" phase before hypothesis formation
- **brainstorming** — understanding existing code before designing changes
- **flow-research** — structured codebase investigation

## Usage Patterns

- "How does a request flow from the API endpoint to the database?"
- "What depends on the UserService class?"
- "Trace the authentication flow end to end"
- "I need to understand this module before I can change it"
- "What happens when someone calls /api/payments?"

## References

- [Tracing Strategy](references/tracing-strategy.md) — core principle, seven-step workflow, what to record at each node, when to stop
- [Trace Modes](references/trace-modes.md) — execution trace, dependency trace, data trace, and combining modes
