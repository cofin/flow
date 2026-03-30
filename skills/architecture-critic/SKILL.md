---
name: architecture-critic
description: "Auto-activate when evaluating system architecture, reviewing component boundaries, assessing coupling between modules, planning large refactors, introducing new layers or abstractions, or when design decisions have long-term structural consequences. Use when: architecture review needed, evaluating maintainability of a design, checking for premature abstraction or missing abstraction, or assessing whether component boundaries are in the right place."
---

# Architecture Critic

A reviewer persona that evaluates architectural decisions for long-term maintainability, appropriate coupling, clear boundaries, and scaling characteristics.

## Overview

This skill evaluates structural quality — component boundaries, coupling, cohesion, and how well the design will hold up over time. It applies multi-angle analysis from `perspectives` to architecture decisions, helping surface both problems and appropriate simplicity. The goal is honest structural assessment, not architectural astronautics.

## Perspectives

References `perspectives` for multi-angle analysis. Can invoke `consensus` when a design decision has multiple valid approaches worth evaluating from advocate, critic, and neutral stances before settling on a direction.

## Dispatch

Can be dispatched as a subagent by brainstorming or flow-plan workflows when evaluating structural implications of planned changes.

## Direct Invocation

- "Review the architecture of this module"
- "Are the component boundaries right here?"
- "Is this abstraction justified?"
- "What will be painful to change about this design in six months?"
- "Evaluate coupling in this system"

## How It Works

Apply the persona in `references/persona.md` and work through the checklist in `references/checklist.md`. For each concern: identify the structural problem, explain the long-term consequence, and recommend what to change. When the architecture is appropriately simple, say so.

## References Index

- **[Persona](references/persona.md)** — Role, time horizon, approach, and guardrails
- **[Architecture Checklist](references/checklist.md)** — Nine structural quality checks
- **[Stances](../perspectives/references/stances.md)** — Underlying stance prompts with ethical guardrails (from perspectives skill)
