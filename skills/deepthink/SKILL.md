---
name: deepthink
description: "Auto-activate when a problem resists quick answers, when initial analysis feels shallow, when debugging hits a wall, when architectural reasoning needs depth, when confidence in a conclusion is low, when analysis feels like it is going in circles, or when the first answer feels too easy for a hard problem. Produces a confidence-tracked investigation with explicit hypothesis evolution, evidence log, and a specific actionable conclusion. Use when: complex reasoning needed, hypothesis testing required, going in circles on a problem, need to track what has been explored vs what remains, analysis feels shallow, confidence is low, or when debugging hits a wall. Not for clear questions with obvious answers, simple lookups, or problems that yield to direct investigation."
---

# Deepthink

Structured extended reasoning with hypothesis tracking and confidence progression. Prevents circular thinking by explicitly tracking what's been explored, what evidence exists, and what confidence level has been reached.

References `perspectives` for multi-angle evaluation when confidence is stuck and a fresh frame is needed.

<workflow>

## Workflow

### 1. Frame the Problem

State what you're trying to understand or decide, specifically. Vague framing produces vague investigation.

### 2. Form Initial Hypothesis

Your best guess based on available information. One sentence. Confidence: `exploring`.

Don't skip this step — even a weak hypothesis focuses investigation better than no hypothesis.

### 3. Gather Evidence

Read code, check docs, run tests, trace execution. Record what you find at each step. Every piece of evidence should be evaluated against the current hypothesis.

> **Note:** Sequential-thinking or similar extended reasoning tools can complement complex sub-steps within this workflow — particularly during evidence gathering (step 3) or when evaluating a hypothesis with many interdependencies. Use them to decompose a stuck sub-step without abandoning the overall hypothesis tracking structure.

### 4. Evaluate Against Hypothesis

Does the evidence support, contradict, or require revision?

- **Supports:** confirms a specific aspect of the hypothesis
- **Contradicts:** rules out a specific aspect, requiring revision
- **Requires revision:** the hypothesis was wrong in some way — update it now

### 5. Update Confidence

Based on evidence quality and coverage, update the confidence level:

| Level | Meaning | Action |
| ----- | ------- | ------ |
| `exploring` | Just started, no hypothesis yet | Gather initial evidence, form hypothesis |
| `low` | Have a hypothesis but weak evidence | Seek confirming/disconfirming evidence |
| `medium` | Evidence supports hypothesis but gaps remain | Fill specific gaps, check edge cases |
| `high` | Strong evidence, minor uncertainties | Verify the uncertainties aren't critical |
| `certain` | Conclusive evidence, ready to act | Synthesize findings and present |

**Escalation rule:** If confidence has not increased after 3 investigation steps, stop and reassess. Either the hypothesis is too broad, you're looking in the wrong place, or you need a different tool (`flow:tracer`, `flow:perspectives`).

### 6. Decide: Continue or Conclude

- **Continue:** identify exactly what's missing and loop back to step 3 with a specific target
- **Conclude:** if confidence is `high` or `certain`, synthesize findings and present

Investigation is complete when: confidence is `high`/`certain`, all evidence-against items are explained, the hypothesis is a specific actionable conclusion, and unexplored areas are evaluated or ruled out as non-critical.

</workflow>

<guardrails>

### Guardrails

- **Evidence hoarding** — Reading files without updating hypothesis. Every read should confirm, contradict, or refine your current hypothesis. If it doesn't, you're reading the wrong thing.
- **Premature conclusion** — Presenting hypothesis as conclusion before gathering evidence. A hypothesis is not a conclusion. Don't present it as one.
- **Permanent exploring** — Staying at `exploring` after 5+ checks without narrowing. Formulate a hypothesis and commit to testing it.
- **Circular investigation** — Revisiting same evidence without new framing. If you're back where you started, the hypothesis needs to change, not the evidence gathering.

</guardrails>

<validation>

### Validation Checkpoint

Before presenting the conclusion, verify:

- [ ] Hypothesis was updated at least once during investigation
- [ ] Evidence for AND against was recorded
- [ ] Confidence level progression is justified by evidence
- [ ] Investigation concluded with a specific, actionable finding

</validation>

<example>

## Example

**Debugging:** "Tests pass locally but fail in CI."

- **Hypothesis 1:** "Flaky test — timing issue" (confidence: `exploring`)
- **Evidence:** CI logs show deterministic failure on same test. Rules out flakiness. → Revise.
- **Hypothesis 2:** "Environment difference — missing env var" (confidence: `low`)
- **Evidence:** Compared CI env vs local. Found `DATABASE_URL` uses different host. Test creates real DB connection. → confidence: `medium`.
- **Hypothesis 3:** "CI database not seeded" (confidence: `medium`)
- **Evidence:** CI setup script skips seed step for test DB. Local has leftover seed data. → confidence: `high`.
- **Conclusion:** CI test DB is empty. Fix: add seed step to CI pipeline before tests.

</example>

## Complements

- **systematic-debugging** — deepthink provides structured hypothesis evolution when debugging stalls after 3+ iterations
- **brainstorming** — deepthink enables deeper analysis during the design phase when approaches need thorough evaluation
- **flow-plan** — deepthink supports thorough requirement analysis for complex decomposition decisions

## References Index

- **[Reasoning Strategy](references/reasoning-strategy.md)** — When to use deepthink, the 6-step workflow, and anti-patterns to avoid
- **[Confidence Tracking](references/confidence-tracking.md)** — Confidence levels table, what to track at each step, escalation rule, and completion criteria
