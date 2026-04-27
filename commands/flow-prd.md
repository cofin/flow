---
description: Analyze goals and generate Master Roadmap (Sagas)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion
---

# Flow PRD

**Beads mode:** Skip every `bd` invocation below when the SessionStart hook reports `Beads Backend: Missing (None)` or `Disabled via plugin config (useBeads=false)`. Treat `spec.md` markers as fallback source of truth and skip `/flow:sync`. Never halt for missing Beads. See `skills/flow/references/discipline.md`.

> Lifecycle skill: use `flow-planning` through the `flow` router.

## The Orchestrator Mandate

**CRITICAL:** `/flow:prd` is the entry point for large features. Its primary role is to initialize the **Beads Epic** (source of truth) and define the high-level roadmap.

---

## 1.0 Environment & Backend Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context`.
2. **Verify Writable:** Ensure the flow root directory is writable.

---

## 2.0 Complexity Analysis

**PROTOCOL: Determine if this is a Flow or a Saga.**

1. **Simple feature?** -> Suggest `/flow:plan`.
2. **Multi-module/Complex?** -> **Saga (PRD)**. Initialize Beads Epic.

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
2. **Draft prd.md**: Define North Star goals and global constraints.

---

## 5.0 Beads Integration (Source of Truth)

**PROTOCOL: Create Beads epics with full context.**

1. **Master Epic**:
    - Run `<active_backend_create_prd_epic>`.
    - The `--description` MUST include the North Star goal.
2. **Sub-Epics (Chapters)**:
    - For each chapter in the roadmap, create a child epic.
3. **Contextual Notes**:
    - Attach high-level architectural decisions as notes to the master epic using `bd note`.

---

## 6.0 Auto-Plan First Flow

**PROTOCOL: Create a unified spec.md for the first chapter.**

1. **Plan Workflow**: Execute read-only code analysis and draft `spec.md`.
2. **Beads Tasks**: Create initial implementation tasks in Beads under the chapter epic.
3. **Refine**: Ensure the first chapter is implementation-ready.

---

## 7.0 Artifact Creation

**PROTOCOL: Create all required files.**

1. **Registry**: Append to `.agents/flows.md`.
2. **Sync**: Follow `syncPolicy.flowSyncAfterMutation`; when enabled, run `/flow:sync` so Markdown views match the new Beads state.

---

## Critical Rules

1. **BEADS FIRST** - Initialize epics and notes before finalizing Markdown.
2. **NO CODE MODIFICATION** - Planning documents only.
3. **SYNC AFTER CREATION** - Follow `syncPolicy.flowSyncAfterMutation`; default setup runs `/flow:sync` to generate Markdown from Beads state.
4. **HARD STOP** - End with explicit instruction to run `/flow:implement`.
