---
name: devils-advocate
description: "Use when stress-testing a PR, design, plan, or assumption for overlooked failure modes before a decision or release."
---

# Devil's Advocate

Stress-test failure modes so concrete risks are visible before they become
problems. Use directly or as an adversarial review subagent.

<workflow>

## Workflow

1. Load the adversarial persona and failure-mode checklist below.
2. Inspect the actual change or proposal and exercise every relevant checklist
   question.
3. Report calibrated findings and acknowledge verified strengths.

</workflow>

<guardrails>

## Guardrails

Follow the persona boundaries. Do not oppose a sound approach merely to be
contrarian, and do not inflate speculative concerns.

</guardrails>

## Output

For each finding, state severity, the specific failure mode, its evidence and
impact, and the recommended mitigation. A substantiated clean bill of health is
valid output.

<validation>

## Validation

Confirm each finding cites concrete code or design evidence and that severity is
calibrated.

</validation>

<example>

## Example

Flag an unbounded upstream call as a cascading timeout risk and identify the
timeout/error-path test that would mitigate it.

</example>

## References

- [Persona](references/persona.md) — adversarial role, tone, focus, and boundaries.
- [Failure-mode checklist](references/checklist.md) — stress-test questions.
- [Critic stance](../perspectives/references/stances.md) — underlying critical view.
