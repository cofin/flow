---
name: deepthink
description: "Auto-activate when a problem resists quick answers, when initial analysis feels shallow, when debugging hits a wall, when architectural reasoning needs depth, or when confidence in a conclusion is low. Use when: complex reasoning needed, hypothesis testing required, going in circles on a problem, need to track what has been explored vs what remains, or when the first answer feels too easy for a hard problem."
---

# Deepthink

Structured extended reasoning with hypothesis tracking and confidence progression. Prevents circular thinking by explicitly tracking what's been explored, what evidence exists, and what confidence level has been reached.

## Overview

When a problem resists quick answers, deepthink provides a structured framework: form a hypothesis, gather evidence, evaluate, update confidence, and decide whether to continue or conclude. By tracking state at each step, it prevents the two failure modes of extended investigation — going in circles and stopping too early.

References `perspectives` for multi-angle evaluation when confidence is stuck and a fresh frame is needed.

## How It Works

Follow the workflow in `references/reasoning-strategy.md`:

1. **Frame the problem** — state what you're trying to understand or decide, specifically
2. **Form initial hypothesis** — best guess based on available information; confidence: `exploring`
3. **Gather evidence** — read code, check docs, trace execution; record findings
4. **Evaluate against hypothesis** — does evidence support, contradict, or require revision?
5. **Update confidence** — based on evidence quality and coverage (see `references/confidence-tracking.md`)
6. **Decide: continue or conclude** — if confidence is sufficient, synthesize; if not, identify what's missing and loop

## Complements

- **systematic-debugging** — deepthink provides structured hypothesis evolution when debugging stalls after 3+ iterations
- **brainstorming** — deepthink enables deeper analysis during the design phase when approaches need thorough evaluation
- **flow-plan** — deepthink supports thorough requirement analysis for complex decomposition decisions

## References Index

- **[Reasoning Strategy](references/reasoning-strategy.md)** — When to use deepthink, the 6-step workflow, and anti-patterns to avoid
- **[Confidence Tracking](references/confidence-tracking.md)** — Confidence levels table, what to track at each step, escalation rule, and completion criteria
