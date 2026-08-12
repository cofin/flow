---
description: Create unified spec.md for a single Flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion
---

# Flow Plan

> Lifecycle skill: use `flow-planning` through the `flow` router.
>
> **Grill before finalizing:** interrogate every open decision one question at a time (each with your recommended answer + trade-off), and explore the repo / `patterns.md` / `knowledge/` instead of asking when the answer is in the code. See `flow-planning` → "Interrogate Before Finalizing".

## The Planner Mandate

**CRITICAL:** `/flow:plan` is the entry point for single flows. Its primary role is to define the roadmap by creating a unified `spec.md` worksheet at `.agents/bundles/specs/<flow_id>/spec.md` containing the YAML frontmatter and the implementation plan.

---

## 1.0 Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
2. **Verify Writable:** Ensure the flow root directory is writable.

---

## 3.0 New Flow Initialization

**PROTOCOL: Define the standard Flow artifacts.**

1. **Code Analysis**: Deeply analyze the codebase to understand the affected surfaces.
2. **Interactive Questions**: Ask informed questions based on the code analysis.
3. **Draft spec.md**: Create a unified specification containing requirements and a high-level plan.

---

## 3.4 Task File Creation

**PROTOCOL: Create one task file per checklist entry.**

1. **Checklist Linkage**: Every `- [ ] Task <short_id>: Title` line in the Implementation Plan gets a matching file at `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`.
2. **Task Frontmatter**: Populate `type: Task`, `id: <flow_id>:<short_id>`, `title`, `state: open`, `depends_on`, `files`, `tests`, `created_at`, `updated_at`.
3. **Checklist & Notes**: Include specific file targets, line numbers, and expected failure reasons in the task file bodies.

---

## 3.5 Completion

**PROTOCOL: Finalize artifacts.**

1. **Save Spec**: Save the spec file directly at `.agents/bundles/specs/<flow_id>/spec.md` with all YAML frontmatter populated.
2. **Sync**: Run `/flow:sync` to reconcile the `spec.md` checklist markers with the task files.

---

## Critical Rules

1. **SPEC FIRST** - Write the `spec.md` with YAML frontmatter at `.agents/bundles/specs/<flow_id>/spec.md` before starting implementation.
2. **TASK FILES** - Create task files under `.agents/bundles/specs/<flow_id>/tasks/` before finalizing the plan.
3. **NO CODE MODIFICATION** - Planning documents only.
4. **SYNC AFTER CREATION** - Run `/flow:sync` so checklist markers match task file state.
5. **HARD STOP** - End with explicit instruction to run `/flow:implement`.
