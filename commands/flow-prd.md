---
description: Analyze goals and generate Master Roadmap (Sagas)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion
---

# Flow PRD

> Lifecycle skill: use `flow-planning` through the `flow` router.
>
> **Grill before finalizing:** interrogate every open decision one question at a time (each with your recommended answer + trade-off), and explore the repo / `patterns.md` / `knowledge/` instead of asking when the answer is in the code. Do not finish the roadmap while obvious research gaps remain. See `flow-planning` → "Interrogate Before Finalizing".

## The Orchestrator Mandate

**CRITICAL:** `/flow:prd` is the entry point for large features. Its primary role is to create the **roadmap spec bundle** (source of truth) and define the high-level roadmap.

---

## 1.0 Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
2. **Verify Writable:** Ensure the flow root directory is writable.

---

## 2.0 Complexity Analysis

**PROTOCOL: Determine if this is a Flow or a Saga.**

1. **Simple feature?** -> Suggest `/flow:plan`.
2. **Multi-module/Complex?** -> **Saga (PRD)**. Create a roadmap spec bundle.

---

## 3.5 Problem Analysis (Interactive)

**PROTOCOL: Analyze the problem and ask clarifying questions BEFORE proposing chapters.**

1. **Code Analysis**: Search relevant files to understand current architecture.
2. **Informed Questions**: Ask 3-5 specific questions about scope and constraints.
3. **Confirm Understanding**: Summarize goals before creating the roadmap.

---

## 4.0 Roadmap Generation

**PROTOCOL: Create the Master Roadmap.**

1. **Breakdown Chapters**: Propose 3-10 granular Flows (Chapters).
2. **Draft Roadmap Spec**: Define North Star goals and global constraints in the roadmap `spec.md`.

---

## 5.0 Roadmap Bundle Creation (Source of Truth)

**PROTOCOL: Create the spec bundles with full context.**

1. **Roadmap Spec Bundle**:
    - Create `.agents/bundles/specs/<prd_id>/spec.md` with frontmatter `type: Spec`, `flow_id`, `title`, `state: planned`, `created_at`, `updated_at`.
    - The spec body MUST include the North Star goal.
2. **Child Flow Bundles (Chapters)**:
    - For each chapter in the roadmap, create its own spec bundle at `.agents/bundles/specs/<flow_id>/spec.md` (`state: planned`).
3. **Contextual Notes**:
    - Record high-level architectural decisions directly in the roadmap spec body.

---

## 6.0 Auto-Plan First Flow

**PROTOCOL: Create a unified spec.md for the first chapter.**

1. **Plan Workflow**: Execute read-only code analysis and draft `spec.md`.
2. **Task Files**: Create one task file per checklist entry under `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md` (frontmatter `type: Task`, `id: <flow_id>:<short_id>`, `title`, `state: open`).
3. **Refine**: Ensure the first chapter is implementation-ready.

---

## 7.0 Artifact Creation

**PROTOCOL: Create all required files.**

1. **Discovery**: No registry file — flows are discovered by scanning spec frontmatter under `.agents/bundles/specs/`.
2. **Sync**: Run `/flow:sync` so the `spec.md` checklist markers match the task files.

---

## Critical Rules

1. **SPEC FIRST** - Create the spec bundles and task files before finalizing the roadmap.
2. **NO CODE MODIFICATION** - Planning documents only.
3. **SYNC AFTER CREATION** - Run `/flow:sync` so checklist markers match task file state.
4. **HARD STOP** - End with explicit instruction to run `/flow:implement`.
