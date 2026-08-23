---
name: deepthink
description: "Use when a problem resists quick answers, debugging stalls, analysis feels shallow, confidence is low, hypotheses are competing, reasoning loops repeat, or a hard problem needs evidence tracking."
---

# Deepthink

Use hypothesis tracking to turn a resistant problem into an evidence-backed,
actionable conclusion.

<workflow>

## Workflow

1. Load the reasoning strategy and confidence ledger below.
2. Frame one testable hypothesis, gather relevant evidence, and update the
   hypothesis and ledger after each investigation step.
3. Continue until the completion criteria are met or the evidence establishes
   exactly what remains unknowable.

</workflow>

<guardrails>

## Guardrails

Do not hoard evidence, loop over the same checks, or present a hypothesis as a
conclusion. Reassess after three steps without confidence progress.

</guardrails>

## Output

Return the final hypothesis, evidence for and against it, confidence and its
basis, remaining uncertainty, and the resulting action.

<validation>

## Validation

Confirm the hypothesis evolved with evidence and the conclusion meets the
reference completion criteria.

</validation>

<example>

## Example

For a CI-only failure, revise a flakiness hypothesis as deterministic environment
evidence appears, then report the verified configuration cause.

</example>

## References

- [Reasoning strategy](references/reasoning-strategy.md) — investigation loop and anti-patterns.
- [Confidence tracking](references/confidence-tracking.md) — confidence and evidence ledger.
- [Critical thinking](../perspectives/references/critical-thinking.md) — optional reframing when progress stalls.
