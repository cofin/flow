---
name: deepthink
description: "Use when a complex bug resists initial investigation, debugging progress has stalled, or multiple competing hypotheses require structured evidence tracking."
---

# Deepthink & Root Cause Isolation

Investigate hard-to-diagnose bugs, race conditions, and architectural dilemmas through systematic hypothesis tracking and falsifiable predictions.

## Workflow

1. **State the Anomaly**: Define the observed failure, error trace, and reproduction conditions.
2. **Formulate Competing Hypotheses**: Generate 2 to 4 distinct root causes.
3. **Design Discriminating Predictions**: State verifiable predictions for each hypothesis.
4. **Execute Tests & Record Evidence**: Run commands and update hypothesis statuses.
5. **Isolate Root Cause**: Confirm the supported root cause with empirical data.

## Guardrails

- Do not modify production code until a discriminating test isolates the failure.
- If three tests produce ambiguous results, step back and re-examine foundational assumptions.

## Output

Return the anomaly summary, hypothesis ledger, confirmed root cause, and minimal fix strategy.

## Validation

Confirm the root cause by reproducing the failure and demonstrating a passing test with the fix.

## Example

For an intermittent async race condition, log timestamps and task ids to isolate order-of-execution violations.
