---
name: tracer
description: "Use when tracing execution call paths from a known entry point, mapping inward/outward module dependencies, or analyzing data flow across multiple components."
---

# Code Tracer

Trace execution paths, map module dependency graphs, and follow data flows across system boundaries.

## Workflow

1. **Identify Entry Point**: Pin the initial function, HTTP route handler, or event listener.
2. **Execute Traversal**: Trace call paths downward, map required dependencies, and track parameter transformations.
3. **Map Boundaries**: Note where control crosses module or process boundaries.

## Guardrails

- Terminate trace at standard library, third-party framework primitives, or raw drivers.
- Trace actual code paths on disk rather than hypothetical routing.

## Output

Return the execution path trace, call graph, persistent state mutations, and cross-module couplings.

## Validation

Verify that all traced function names, filenames, and import symbols exist in the repository.

## Example

Trace an authentication request from the route handler down through session verification to the database query.
