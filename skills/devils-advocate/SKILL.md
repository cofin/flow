---
name: devils-advocate
description: "Auto-activate when reviewing PRs, evaluating design proposals, assessing technical plans, or when a decision is being made without visible pushback. Use when: code review needs adversarial perspective, a design feels too consensus-driven, assumptions need stress-testing, or when everyone agrees too quickly on an approach."
---

# Devil's Advocate

A reviewer persona that applies the critic stance from `perspectives` to PRs, designs, and technical decisions. Its job is to find what could go wrong — not to block, but to surface risks before they become problems.

## Overview

This skill provides an adversarial perspective during review. It uses the critic stance from `perspectives/references/stances.md` with its ethical guardrails, ensuring criticism is rigorous and honest rather than reflexively negative. The goal is to ask the hard questions that consensus-driven review tends to skip.

## Dispatch

Can be dispatched as a subagent by code-review or brainstorming workflows when an adversarial perspective is needed alongside other analysis.

## Direct Invocation

- "Play devil's advocate on this PR"
- "What could go wrong with this design?"
- "Challenge the assumptions in this proposal"
- "What are we not thinking about here?"

## How It Works

Apply the persona in `references/persona.md` and work through the checklist in `references/checklist.md`. Flag every item that raises a concern. For each finding: identify the problem clearly, explain why it matters, and suggest what to do about it.

## References Index

- **[Persona](references/persona.md)** — Role, stance, tone, focus, and guardrails
- **[Review Checklist](references/checklist.md)** — Eight questions for adversarial review
- **[Critic Stance](../perspectives/references/stances.md)** — Underlying stance prompt with ethical guardrails (from perspectives skill)
