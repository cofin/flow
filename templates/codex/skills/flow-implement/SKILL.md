---
name: flow-implement
description: "Execute tasks from flow using TDD workflow"
---

# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`/flow:implement {flow_id}` or `/flow:implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Artifacts:**
    - `.agent/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agent/specs/{flow_id}/learnings.md`
2. **Read Project Context:** `.agent/patterns.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read `.agent/prd/<parent_id>/prd.md`.
4. **Load Beads context:**
    - `br status` (workspace overview)
    - `br ready` (list unblocked tasks)
    - `br list --status in_progress` (resume active work)

**CRITICAL:** Before starting, check `.gitignore`. If `.agent/` is ignored, do NOT commit changes to artifacts inside it using git. Update them on disk only.

## Phase 2: Select Task (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers.

### 2.1 Check for Resume State

```bash
cat .agent/specs/{flow_id}/implement_state.json 2>/dev/null
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

```bash
# Run tests
npm test  # or pytest, cargo test, etc.
```

### 3.3 Green Phase - Implement

1. Write minimum code to pass tests
2. Run tests until green

### 3.4 Refactor Phase

1. Clean up while tests pass
2. Apply patterns from patterns.md

### 3.5 Verify Coverage

```bash
npm test -- --coverage
```

Target: 80% minimum

## Phase 4: Commit

```bash
git add -A
git commit -m "<type>(<scope>): <description>"
```

Format: conventional commits

## Phase 5: Sync to Beads (Source of Truth)

```bash
br close {task_id} --reason "commit: {sha}"
```

## Phase 5.1: Sync to Markdown (MANDATORY)

Run `/flow:sync {flow_id}` to export Beads state to spec.md.

**CRITICAL:** Do NOT write `[x]` markers directly to spec.md. Beads is the source of truth — use `/flow:sync` instead.

### 5.2 Log Learnings

If any patterns discovered, add to `.agent/specs/{flow_id}/learnings.md`

## Phase 6: Save State

Save progress to `.agent/specs/{flow_id}/implement_state.json`:

```json
{
  "current_phase": 1,
  "current_task": "1.2",
  "last_commit": "abc1234",
  "timestamp": "ISO timestamp"
}
```

## Phase 7: Phase Checkpoint

At end of each phase:

1. Run full test suite
2. Create tag: `checkpoint/{flow_id}/phase-{N}`
3. Sync to markdown: run `/flow:sync {flow_id}` (MANDATORY)
4. Prompt for pattern elevation
5. Ask user to verify

## Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

If continuing, loop back to Phase 2.

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **BEADS IS SOURCE OF TRUTH** - Never write markers to spec.md
4. **MANDATORY SYNC** - Run `/flow:sync` after every `br close` and phase completion
5. **LOG LEARNINGS** - Capture patterns as you go
6. **LOCAL ONLY** - Never push automatically
7. **USE `br ready`** - Always check Beads for next task
