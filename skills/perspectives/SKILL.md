---
name: perspectives
description: "Auto-activate when analyzing trade-offs, evaluating decisions, comparing approaches, playing devil's advocate, considering pros and cons, weighing options, assessing risks, reviewing assumptions, or needing multiple viewpoints on a problem. Use when: any decision needs structured multi-angle analysis. Shared prompt library — produces stance prompts and critical thinking frameworks for use by other skills. Not typically invoked directly — loaded by challenge, consensus, and reviewer skills."
---

# Perspectives

Shared prompt library for structured multi-perspective analysis. Provides stance prompts (advocate, critic, neutral) and critical thinking frameworks used by other Flow skills.

## Overview

This skill provides the foundation that other skills build on:

- **Stance prompts** — three perspectives (advocate, critic, neutral) each with ethical guardrails that prevent harmful analysis
- **Critical thinking framework** — structured reassessment pattern for evaluating claims and assumptions

Typically loaded by other skills (`challenge`, `consensus`, persona skills) rather than invoked directly. Can be invoked directly when you want raw stance prompts for custom analysis.

## References Index

- **[Stance Prompts](references/stances.md)** — Advocate, critic, and neutral perspective prompts with ethical guardrails
- **[Critical Thinking Framework](references/critical-thinking.md)** — CRITICAL REASSESSMENT pattern and anti-patterns
