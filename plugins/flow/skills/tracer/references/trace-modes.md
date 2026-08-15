# Trace Modes

Three tracing modes — pick based on your goal:

## Execution Trace

**Question:** "What happens when X is called?"

- Start at the trigger (endpoint, event handler, CLI command)
- Follow the primary execution path step by step
- Focus on: call order, data transformations, side effects
- Output: sequential flow (A calls B with X, B transforms to Y, B calls C with Y, ...)
- Best for: understanding features, debugging unexpected behavior

## Dependency Trace

**Question:** "What does X depend on, and what depends on X?"

- Start at the target component
- Map outward: what does it import/use? (outgoing dependencies)
- Map inward: what imports/uses it? (use grep for references)
- Focus on: coupling, blast radius of changes, circular dependencies
- Output: dependency map with direction arrows
- Best for: planning refactors, understanding change impact, finding circular deps

## Data Trace

**Question:** "How does data Y flow through the system?"

- Start where the data enters (user input, API response, database read)
- Follow the data through transformations, validations, storage
- Focus on: where data is validated, transformed, copied, persisted
- Output: data flow with transformation annotations
- Best for: understanding data models, finding where validation happens, security audit of data handling

## Combining Modes

For complex investigations, start with an execution trace to understand the happy path, then use dependency trace on the components that matter most, then data trace on the critical data structures.
