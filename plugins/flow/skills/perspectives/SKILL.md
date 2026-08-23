---
name: perspectives
description: "Use when a multi-view analysis (advocate, critic, and neutral stances) is needed to balance tradeoffs and synthesize an unbiased technical recommendation."
---

# Multi-Perspective Analysis

Analyze complex engineering decisions across three distinct stances (Advocate, Critic, and Neutral Architect) to eliminate bias and produce balanced recommendations.

## Workflow

1. **Frame the Question**: State the architectural or technical dilemma under review.
2. **Collect Multi-View Evidence**: Gather Advocate viewpoint (benefits), Critic viewpoint (risks), and Neutral viewpoint (ecosystem context).
3. **Synthesize Balanced Recommendation**: Extract highest-signal insights from each perspective to form an actionable path forward.

## Guardrails

- Ensure distinct, non-overlapping stances with substantive arguments.
- Synthesize actionable conclusions rather than leaving open ambiguities.

## Output

Return the question framing, advocate case, critic case, and synthesized consensus recommendation.

## Validation

Confirm that all three viewpoints are grounded in codebase context and practical operational trade-offs.

## Example

Analyze introducing a new state machine library by comparing the Advocate's velocity case, the Critic's dependency risk case, and the Neutral architect's custom enum approach.
