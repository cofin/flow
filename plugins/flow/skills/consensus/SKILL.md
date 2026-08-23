---
name: consensus
description: "Use when comparing two or more distinct architectural/technical approaches, evaluating build-vs-buy options, or resolving high-impact design disagreements."
---

# Technical Consensus & Trade-Off Analysis

Evaluate competing architectural designs, technology choices, or library selections through structured multi-criteria trade-off matrices.

## Workflow

1. **Define Candidate Approaches**: Frame 2 to 3 viable alternatives with clear boundary descriptions.
2. **Establish Evaluation Criteria**: Select relevant axes (e.g. Ergonomics, Type Safety, Runtime Performance, Team Cognitive Load).
3. **Construct Comparison Matrix**: Compare options side by side with concrete trade-off assessments.
4. **Formulate Recommendation**: State the winning approach with justification and reversal triggers.

## Guardrails

- Avoid false balance when one approach is objectively superior for the stack.
- Weigh reversibility (one-way door vs two-way door decisions).

## Output

Return the decision context, comparison matrix, recommended path, and reversal triggers.

## Validation

Confirm criteria alignment with repository patterns and tech stack constraints.

## Example

Compare choosing an embedded SQLite database versus PostgreSQL for local test fixtures, evaluating spin-up time and feature parity.
