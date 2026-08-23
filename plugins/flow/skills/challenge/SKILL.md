---
name: challenge
description: "Use when verifying a technical claim, conducting a sanity check, testing an unproven assumption, or answering 'are you sure?' with concrete evidence."
---

# Technical Claim Challenge

Rigorously verify technical assumptions, claims, and sanity-check questions with empirical evidence and code citations.

## Workflow

1. **Identify the Core Claim**: Formulate the assertion as a testable proposition.
2. **Execute Empirical Investigation**: Inspect source files, types, and compiler behaviors, running verification commands to test edge cases.
3. **Render Verdict**: Determine whether the claim Holds, Partially Holds, or Fails.

## Guardrails

- Never validate a claim simply because it was proposed; evaluate facts independently.
- Every verdict must quote exact file lines, command outputs, or documentation references.

## Output

Return the claim under review, verdict, empirical evidence, and actionable corrections.

## Validation

Confirm the verdict by citing exact code lines, compiler outputs, or test results.

## Example

When asked if a framework supports async generators, run a test or check the type declarations to provide empirical proof.
