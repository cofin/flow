# Reasoning Strategy

Extended reasoning workflow for problems that resist quick answers.

## When to Use Deepthink vs Regular Analysis

- **Regular analysis:** clear question, bounded scope, confident in first answer
- **Deepthink:** ambiguous problem, multiple valid interpretations, first answer feels incomplete, debugging with no obvious root cause

## Extended Reasoning Workflow

### 1. Frame the Problem

State what you're trying to understand or decide. Be specific. Vague framing produces vague investigation.

### 2. Form Initial Hypothesis

Your best guess based on available information. One sentence. Confidence: `exploring`.

Don't skip this step — even a weak hypothesis focuses investigation better than no hypothesis.

### 3. Gather Evidence

Read code, check docs, run tests, trace execution. Record what you find at each step. Every piece of evidence should be evaluated against the current hypothesis.

### 4. Evaluate Against Hypothesis

Does the evidence support, contradict, or require revision of your hypothesis? Be explicit:

- **Supports:** confirms a specific aspect of the hypothesis
- **Contradicts:** rules out a specific aspect, requiring revision
- **Requires revision:** the hypothesis was wrong in some way — update it now

### 5. Update Confidence

Based on evidence quality and coverage, update the confidence level. See `confidence-tracking.md` for levels and escalation rules.

### 6. Decide: Continue or Conclude

- **Continue:** identify exactly what's missing and loop back to step 3 with a specific target
- **Conclude:** if confidence is `high` or `certain`, synthesize findings and present

## Anti-Patterns

**Evidence hoarding** — Reading file after file without updating the hypothesis. Every read should either confirm, contradict, or refine your current hypothesis. If it doesn't, you're reading the wrong thing.

**Premature conclusion** — Jumping to a conclusion before gathering evidence. A hypothesis is not a conclusion. Don't present it as one.

**Permanent exploring** — Staying at `exploring` without narrowing. If you've checked 5+ things, you should have SOME hypothesis. Formulate one and commit to testing it.

**Shiny object syndrome** — Abandoning a productive line of inquiry because a new idea appeared. Finish the current branch or explicitly record why you're switching, then switch.

**Circular investigation** — Revisiting the same evidence without new framing. If you're back where you started, the hypothesis needs to change, not the evidence gathering.
