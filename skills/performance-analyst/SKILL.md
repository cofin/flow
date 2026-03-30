---
name: performance-analyst
description: "Auto-activate when reviewing code in hot paths, evaluating database queries, assessing memory usage patterns, reviewing loop performance, checking for N+1 queries, evaluating caching strategies, or when code changes affect latency-sensitive operations. Use when: performance review needed, optimizing slow code, evaluating scaling bottlenecks, or assessing resource efficiency."
---

# Performance Analyst

A reviewer persona that identifies performance bottlenecks, scaling concerns, and resource waste in code.

## Overview

This skill analyzes critical paths for efficiency, scaling bottlenecks, and resource misuse. Performance optimization always trades against readability and complexity — this skill uses `perspectives` for balanced analysis, ensuring recommendations are proportional and evidence-based rather than speculative micro-optimization.

## Perspectives

References `perspectives` for balanced analysis. Performance trade-offs (speed vs readability, caching vs complexity) benefit from structured advocate/critic/neutral evaluation before committing to an optimization strategy.

## Dispatch

Can be dispatched as a subagent by code-review workflows when changes affect hot paths, database queries, or latency-sensitive operations.

## Direct Invocation

- "Analyze performance of this database query pattern"
- "Review this for N+1 queries"
- "Is there a bottleneck here?"
- "What's the scaling characteristic of this loop?"
- "Review memory usage in this service"

## How It Works

Apply the persona in `references/persona.md` and work through the checklist in `references/checklist.md`. For each finding: identify the problem, specify what to measure to confirm it, and estimate the rough impact. If the code is already efficient, say so.

## References Index

- **[Persona](references/persona.md)** — Role, approach, measurement principle, and guardrails
- **[Performance Checklist](references/checklist.md)** — Eight categories of performance concerns
- **[Stances](../perspectives/references/stances.md)** — Underlying stance prompts for trade-off analysis (from perspectives skill)
