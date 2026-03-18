---
description: Execute tasks from plan (context-aware)
---

# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`/flow:implement {flow_id}` or `/flow:implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Artifacts:**
    - `.agents/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agents/specs/{flow_id}/learnings.md`
2. **Read Project Context:** `.agents/patterns.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read `.agents/specs/<parent_id>/prd.md`.
4. **Load Beads:**
    - `br status` (workspace overview)
    - `br ready` (list unblocked tasks)
    - `br list --status in_progress` (resume active work)

**CRITICAL:** Before starting, check `.gitignore`. If `.agents/` is ignored, do NOT commit changes to artifacts inside it using git. Update them on disk only.

## Phase 2: Select Task (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers.

### 2.1 Check for Resume State

```bash
cat .agents/specs/{flow_id}/implement_state.json 2>/dev/null
```

### 2.2 Find Next Task

**Primary: Use Beads**

```bash
br ready
```

**Fallback: Parse spec.md**

If Beads unavailable, parse `spec.md` Implementation Plan section for pending tasks.

## Phase 3: Task Execution (TDD)

### 3.1 Mark In Progress

**If task not in Beads, create it first:**

```bash
br create "{task_description}" --parent {epic_id} -p 2 \
  --description="{what_needs_to_be_done_and_why}"
br update {new_task_id} --notes "Phase {N}, Task {M}. Files: {affected_files}. Created by /flow:implement"
```

Then mark in progress:

```bash
br update {task_id} --status in_progress
```

**CRITICAL:** Do NOT write `[~]` markers to spec.md. Beads is source of truth.

### 3.2 Red Phase - Write Failing Tests

1. Create/update test file
2. Write tests that define expected behavior
3. Run tests to confirm they fail

### 3.3 Green Phase - Implement

1. Write minimum code to pass tests
2. Run tests until green

### 3.4 Refactor Phase

1. Clean up while tests pass
2. Apply patterns from patterns.md

### 3.5 Verify Coverage

Target: 80% minimum

## Phase 4: Commit

```bash
git add -A
git commit -m "<type>(<scope>): <description>"
```

## Phase 5: Sync to Beads (Source of Truth)

```bash
br close {task_id} --reason "commit: {sha}"
```

### Markdown Sync (Automatic)

The git pre-commit hook automatically exports Beads state to spec.md on commit.
**CRITICAL:** Do NOT write markers directly to spec.md and do NOT run sync manually.

### 5.2 Log Learnings

Add discoveries to `.agents/specs/{flow_id}/learnings.md`

## Phase 6: Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **BEADS IS SOURCE OF TRUTH** - Never write markers to spec.md
5. **LOG LEARNINGS** - Capture patterns as you go
6. **LOCAL ONLY** - Never push automatically
7. **USE `br ready`** - Always check Beads for next task
