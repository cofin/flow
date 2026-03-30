---
name: consensus
description: "Auto-activate when evaluating architectural decisions, comparing technology choices, weighing design trade-offs, assessing feature proposals, making build-vs-buy decisions, choosing between competing approaches, or when a decision has significant long-term consequences. Use when: decisions need structured multi-perspective analysis, risk assessment from multiple angles, or when the stakes are high enough to warrant deliberate evaluation."
---

# Consensus

Structured decision evaluation through stance rotation — analyze from advocate, critic, and neutral perspectives, then synthesize. References the `perspectives` skill for stance prompts and ethical guardrails.

## Overview

Evaluates decisions by rotating through three perspectives:

1. **Neutral** — objective analysis of all factors
2. **Advocate** — strongest case FOR (with ethical guardrails)
3. **Critic** — rigorous scrutiny of risks (with ethical guardrails)
4. **Synthesis** — weigh all three, produce recommendation with confidence level

Two modes based on decision complexity:
- **Sequential** (default) — all perspectives in one pass, fast
- **Subagent** — three isolated subagents for true independence, used for high-stakes decisions

## Usage Patterns

- "Should we migrate from REST to GraphQL?"
- "Evaluate this architecture proposal"
- "Is this the right database choice for our use case?"
- "Weigh the trade-offs of splitting this into microservices"
- "I need a thorough analysis of whether to rewrite vs refactor"

## How It Works

### Mode Selection

Follow `references/consensus-strategy.md` to choose:
- **Sequential mode** — bounded scope, clear constraints, time pressure
- **Subagent mode** — affects >3 months of work, irreversible, perspectives suspiciously aligned

### Stance Rotation

Follow `references/stance-rotation.md` for the rotation steps and synthesis framework.

### Decision Scope Guide

| Decision Scope | Recommended Mode |
| -------------- | ---------------- |
| Bounded, reversible | Sequential |
| Multi-month, irreversible | Subagent |
| Perspectives suspiciously aligned | Escalate to subagent |

## References Index

- **[Consensus Strategy](references/consensus-strategy.md)** — Mode selection and escalation criteria
- **[Stance Rotation](references/stance-rotation.md)** — Rotation steps, subagent dispatch, synthesis framework
- **[Stance Prompts](../perspectives/references/stances.md)** — Advocate, critic, neutral prompts (from perspectives skill)
