---
name: tracer
description: "Use when tracing execution paths, mapping dependencies, understanding unfamiliar code, following data flow, investigating end-to-end behavior, debugging call chains, or deciding which files to read next."
---

# Tracer

Trace code from a known entry point, following evidence-linked edges until the
question is answered.

<workflow>

## Workflow

1. Load the tracing strategy and mode-selection reference below.
2. Select execution, dependency, or data mode from the question.
3. Follow and record relevant edges, then synthesize the resulting map at the
   documented stop condition.

</workflow>

<guardrails>

## Guardrails

Do not open unrelated files, trace every branch indiscriminately, or cross a
third-party boundary unless the question requires it.

</guardrails>

## Output

Return the selected mode, an ordered path or dependency/data map with file and
symbol locations, transformations and side effects, and a concise answer to the
original question.

<validation>

## Validation

Confirm every inspected node follows from a recorded edge and the trace stops
only after the question or critical path is resolved.

</validation>

<example>

## Example

Map an HTTP handler through its service and repository to the database call,
annotating the data transformation at each node.

</example>

## References

- [Tracing strategy](references/tracing-strategy.md) — traversal and evidence procedure.
- [Trace modes](references/trace-modes.md) — mode selection and combination.
