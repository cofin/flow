---
description: Refine coarse tasks into implementation-ready plans
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Refine

> Lifecycle skill: use `flow-planning` through the `flow` router.
>
> **Grill before finalizing:** interrogate every open decision one question at a time (each with your recommended answer + trade-off), and explore the repo / `patterns.md` / `knowledge/` instead of asking when the answer is in the code. Refinement is done only when a zero-context executor could implement from the worksheet alone. See `flow-planning` → "Interrogate Before Finalizing".

Refining flow: **$ARGUMENTS**

## The Refiner Mandate

**CRITICAL:** `/flow:refine` is the quality gate. Its primary role is to ensure every task file under `.agents/bundles/specs/<flow_id>/tasks/` has sufficient detail (files, lines, snippets) for a "stateless" executor.

---

## 3.0 Refinement Workflow

**PROTOCOL: Update task files with high-definition detail.**

1. **Deep Code Dive**: Read more code until affected surfaces (file:line) are known.
2. **Update Task Files**: Write into each task file's body:
    - Exact file/line targets (and `files:`/`tests:` frontmatter arrays).
    - Implementation strategy (code snippets).
    - Expected failure reason for TDD.
3. **Sync Markdown**: Run `/flow:sync` so the `spec.md` checklist stays reconciled with the task files.

---

## 4.0 Completion

**PROTOCOL: Finalize and sync.**

1. **Sync**: Run `/flow:sync` to ensure `spec.md` acts as a perfect worksheet.
2. **Hard Stop**: End with explicit instruction to run `/flow:implement`.

---

## Critical Rules

1. **NO GUESSWORK** - Forbid vague instructions like "wire up".
2. **TASK FILES FIRST** - Store refined detail in the task files themselves.
3. **SYNC AFTER REFINE** - Run `/flow:sync` so the worksheet matches task file state.
