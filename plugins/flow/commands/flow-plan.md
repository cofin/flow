---
description: Create unified spec.md for a single Flow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion
---

# Flow Plan

> Lifecycle skill: use `flow-planning` through the `flow` router.

## The Planner Mandate

**CRITICAL:** `/flow:plan` is the entry point for single flows. Its primary role is to define the roadmap by creating **Beads Tasks** (source of truth) and syncing them to a human-readable `spec.md`.

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

## 3.4 Beads Integration (Source of Truth)

**PROTOCOL: Create Beads tasks with full context.**

1. **Epic Linkage**: Ensure the flow is backed by a Beads Epic.
2. **Task Creation**: Create granular implementation tasks in Beads linked to the epic.
3. **Checklist & Notes**: Include specific file targets, line numbers, and expected failure reasons in task descriptions or notes.

---

## 3.5 Completion

**PROTOCOL: Finalize artifacts and sync.**

1. **Registry**: Append to `.agents/flows.md`.
2. **Sync**: Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow:sync` to generate the `spec.md` worksheet from the new Beads tasks.

---

## Critical Rules

1. **BEADS FIRST** - Create tasks in the issue tracker before finalizing Markdown.
2. **NO CODE MODIFICATION** - Planning documents only.
3. **SYNC POLICY** - Follow `syncPolicy.flowSyncAfterMutation`; default setup runs `/flow:sync` after planning to ensure consistency.
4. **HARD STOP** - End with explicit instruction to run `/flow:implement`.
