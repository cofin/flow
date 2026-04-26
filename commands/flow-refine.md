---
description: Refine coarse tasks into implementation-ready plans
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Refine

> Lifecycle skill: use `flow-planning` through the `flow` router.

Refining flow: **$ARGUMENTS**

## The Refiner Mandate

**CRITICAL:** `/flow:refine` is the quality gate. Its primary role is to ensure every task in **Beads** has sufficient detail (files, lines, snippets) for a "stateless" executor.

---

## 3.0 Refinement Workflow

**PROTOCOL: Update Beads tasks with high-definition detail.**

1. **Deep Code Dive**: Read more code until affected surfaces (file:line) are known.
2. **Update Beads**: Use `bd note` to attach:
    - Exact file/line targets.
    - Implementation strategy (code snippets).
    - Expected failure reason for TDD.
3. **Sync Markdown**: Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow:sync` to reflect these details in `spec.md`.

---

## 4.0 Completion

**PROTOCOL: Finalize and sync.**

1. **Sync**: Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow:sync` to ensure `spec.md` acts as a perfect worksheet.
2. **Hard Stop**: End with explicit instruction to run `/flow:implement`.

---

## Critical Rules

1. **NO GUESSWORK** - Forbid vague instructions like "wire up".
2. **BEADS FIRST** - Store refined detail in Beads notes/descriptions.
3. **SYNC AFTER REFINE** - Follow `syncPolicy.flowSyncAfterMutation`; default setup runs `/flow:sync` to generate the worksheet.
