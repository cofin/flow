---
description: Execute tasks from plan (context-aware)
---

# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`/flow-implement {flow_id}` or `/flow-implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Artifacts:**
    - `.agents/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agents/specs/{flow_id}/learnings.md`
2. **Read Project Context:** `.agents/patterns.md` and `.agents/workflow.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read `.agents/specs/<parent_id>/prd.md`.
4. **Load Beads:**
    - If using official Beads (`bd`): load the active queue/workspace state
    - If using `br`: `br status`, `br ready`, `br list --status in_progress`
    - If using no-Beads mode: skip backend loading and use `spec.md`

**CRITICAL:** Before starting, check whether `.agents/` artifacts are ignored by `.gitignore`, `.git/info/exclude`, or global git ignores. If they are ignored, do NOT commit those artifacts. Update them on disk only.

## Phase 2: Select Task (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers.

### 2.1 Check for Resume State

```bash
cat .agents/specs/{flow_id}/implement_state.json 2>/dev/null
```

### 2.2 Find Next Task

**Primary: Use Beads**

Use the active backend's ready/queue command.

**Fallback: Parse spec.md**

If Beads unavailable, parse `spec.md` Implementation Plan section for pending tasks.

## Phase 3: Task Execution (TDD)

### 3.0 Subagent Execution Preference

If `superpowers:subagent-driven-development` is available in this host, invoke it before implementation and use its implementation-subagent workflow for task execution and review checkpoints.

- Before delegating, ask: "Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?"
- If not, invoke `flow-refine` first and update the plan before dispatch.
- Preserve subagent context by passing the relevant spec or PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements.
- Do not silently descope if the task is larger than expected. Refine it or ask the user how to prioritize.

Fallback: if the skill is unavailable, continue with the single-agent TDD workflow below.
In fallback mode, preserve the same task context bundle, refine coarse tasks first, and keep the same review checkpoints.

### 3.0.1 API Lookup Preference

If task execution depends on external framework/API behavior, versions, migrations, or release changes, invoke `flow:apilookup` before implementation decisions.

### 3.1 Mark In Progress

**If task not in Beads, create it first:**

```bash
<active_backend_create_task>
<active_backend_attach_notes>
```

Then mark in progress:

```bash
<active_backend_mark_in_progress>
```

**CRITICAL:** Do NOT write `[~]` markers to spec.md. Beads is source of truth.

### 3.2 Red Phase - Write Failing Tests

1. Create/update test file
2. Write tests that define expected behavior
3. Run the canonical test command from `.agents/workflow.md` when present to confirm they fail

### 3.3 Green Phase - Implement

1. Write minimum code to pass tests
2. Run tests until green
3. Make the minimum targeted change set needed for the task. Do not add unrelated cleanup without approval.

### 3.4 Refactor Phase

1. Clean up while tests pass
2. Apply patterns from patterns.md

### 3.5 Verify Coverage

Target: 80% minimum
Prefer the repo's canonical verification or coverage command from `.agents/workflow.md` when present.

## Phase 4: Commit

```bash
git add <implementation_files> <non_ignored_context_files>
git commit -m "<type>(<scope>): <description>"
```

Never use `git add -A` or `git add -f` for Flow work. If a file is ignored, leave it local-only.
Never force-add ignored Flow artifacts.

## Phase 5: Sync to Beads (Source of Truth)

```bash
<active_backend_close_task>
```

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. It is MANDATORY that you run `/flow-sync` to update the markdown state after any task completion or status change.

### 5.2 Log Learnings

Add discoveries to `.agents/specs/{flow_id}/learnings.md`
If a backend is enabled, attach the same learning summary through the active backend's notes mechanism.

## Phase 6: Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **BEADS IS SOURCE OF TRUTH** - Never write markers to spec.md
4. **PREFER SUPERPOWERS SUBAGENTS** - Use `superpowers:subagent-driven-development` when available, otherwise follow the same protocol inline
5. **PREFER API LOOKUP** - Use `flow:apilookup` for external API/version/doc questions before coding
6. **LOG LEARNINGS** - Capture patterns as you go
7. **LOCAL ONLY** - Never push automatically
8. **USE THE ACTIVE BACKEND'S READY QUEUE** - Always check Beads for next task when a backend is enabled
9. **USE CANONICAL REPO COMMANDS** - Prefer the commands documented in `.agents/workflow.md`
10. **BE COLLABORATIVE** - Describe unrelated blockers factually and constructively; never use dismissive ownership-deflecting language
