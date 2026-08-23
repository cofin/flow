---
name: devils-advocate
description: "Use when performing an adversarial stress-test on a proposed design, pull request, or rollout plan to identify overlooked failure modes."
---

# Devil's Advocate & Adversarial Stress Testing

Subject proposed designs, plans, and implementations to adversarial critique to uncover hidden failure modes, concurrency race conditions, and operational blind spots.

## Workflow

1. **Review Proposed Artifact**: Read the spec, PR diff, or migration plan.
2. **Execute Inversion & Failure Scenarios**: Test data boundary inversions, concurrency states, partial network failures, and configuration errors.
3. **Calibrate Severity**: Differentiate critical show-stoppers from minor edge cases.

## Guardrails

- Surface genuine failure modes; avoid obstructing practical work with absurdly improbable scenarios.
- Every failure mode must accompany a concrete, low-cost defensive measure.

## Output

Return the adversarial stress-test findings, failure scenarios, and concrete mitigations.

## Validation

Confirm failure scenarios against actual codebase execution paths and error handlers.

## Example

Inspect a new caching layer for cache stamping risks when a high-traffic key expires simultaneously across workers.
