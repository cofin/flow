---
description: Execute tasks from flow plan with TDD workflow
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__pal__thinkdeep, mcp__pal__debug, mcp__pal__analyze
---

# Flow Implement

Implementing flow: **$ARGUMENTS**

## Phase 0: Load Context

1. Load flow from `.agent/specs/{flow_id}/`
2. Read `spec.md` (unified spec+plan), `learnings.md`
3. Read `.agent/patterns.md` for project patterns
4. Read `.agent/workflow.md` for process guidelines

---

## 1.1 INITIALIZATION

**PROTOCOL: Load the Flow context.**

1. **Check for User Input:** First, check if the user provided a flow ID as an argument.
    * **If provided:** Use that `flow_id` and proceed to step 3.
    * **If NOT provided:** Proceed to step 2 to auto-discover the flow.

2. **Auto-Discovery (No Argument Provided):**
    * **Scan for Active Flows:** Read `.agent/flows.md` and look for flows marked as "Active" or "In Progress".
    * **Heuristics:**
        * If exact one active flow, select it.
        * If multiple, choose most recent.
        * If none, list pending and ask.

3. **Load Flow Context:**
    * **Read Artifacts:** `spec.md` (unified spec+plan), `learnings.md` (create if missing).
    * **Read Project Context:** Read `.agent/patterns.md` and `.agent/workflow.md`.
    * **Read Parent Context:** If this flow is part of a PRD/Saga, read `.agent/prd/<parent_id>/prd.md`.

**CRITICAL:** Before starting, check `.gitignore`. If `.agent/` is ignored, do NOT commit changes to artifacts inside it using git. Update them on disk only.

---

## Phase 1: Beads Sync

```bash
bd prime                    # Load AI-optimized context
bd ready                    # List unblocked tasks
bd show {epic_id}          # View flow status
```

---

## Phase 2: Task Selection (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update plan.md markers.

### 2.1 Primary: Use Beads

```bash
bd ready                    # List unblocked tasks ready to work
bd show {epic_id}          # View epic with all tasks
```

Select task from `bd ready` output. If multiple ready tasks, ask user which to start.

### 2.2 Fallback: Parse spec.md

If Beads unavailable or no tasks found:
1. Parse `spec.md` Implementation Plan section
2. Find first pending task (not yet in Beads or no status)
3. Create task in Beads if missing

---

## Phase 3: Task Execution Loop

For each task from `bd ready` or spec.md:

### 3.1 Mark In Progress

**If task not in Beads, create it first:**

```bash
bd create "{task_description}" --parent {epic_id} -p 2 \
  --description="{what_needs_to_be_done_and_why}" \
  --notes="Phase {N}, Task {M}. Files: {affected_files}. Created by /flow-implement"
bd update {new_task_id} --status in_progress
```

**If task exists in Beads:**

```bash
bd update {task_id} --status in_progress
```

**CRITICAL:** 
- Always include `--description` and `--notes` when creating tasks
- Beads is the source of truth - do NOT write `[~]` markers to spec.md

### 3.2 Write Failing Tests (Red Phase)

**CRITICAL:** Write tests BEFORE implementation.

1. Create test file following project conventions
2. Write tests that define expected behavior
3. Run tests: `{test_command}`
4. **VERIFY tests fail as expected**

### 3.3 Implement (Green Phase)

1. Write minimum code to pass tests
2. Follow patterns from `patterns.md`
3. Run tests to verify they pass

### 3.4 Refactor

1. Clean up code with test safety
2. Ensure no duplication
3. Verify tests still pass

### 3.5 Verify Coverage

```bash
{coverage_command}
```

Target: >80% coverage for new code.

### 3.6 Commit

```bash
git add {files}
git commit -m "{type}({scope}): {description}"
```

### 3.7 Sync to Beads (Source of Truth)

```bash
bd close {task_id} --reason "commit: {sha}"
```

**CRITICAL:** Beads is the source of truth. Do NOT update spec.md with `[x]` markers.

### 3.9 Record Learning (if any)

If pattern discovered, append to `learnings.md`:

```markdown
## [YYYY-MM-DD HH:MM] - Phase N Task M: {description}

- **Implemented:** {what}
- **Files changed:** {files}
- **Commit:** {sha}
- **Learnings:**
  - Pattern: {pattern discovered}
  - Gotcha: {gotcha found}
```

Sync to Beads:

```bash
bd update {task_id} --notes "{learning}"
```

---

## Phase 4: Phase Completion Protocol

When a phase completes:

### 4.1 Test Coverage Verification

```bash
git diff --name-only {phase_start_sha} HEAD
```

Verify tests exist for all code files.

### 4.2 Run Full Test Suite

```bash
CI=true {test_command}
```

### 4.3 Manual Verification Plan

Present step-by-step verification for user:

```
Manual Verification Steps:
1. {Command to run}
2. {Expected outcome}
3. {What to verify}
```

### 4.4 Await User Confirmation

> Does this meet your expectations? (yes/no)

### 4.5 Create Checkpoint

```bash
git commit --allow-empty -m "flow(checkpoint): Phase {N} complete"
```

Record in Beads:

```bash
bd update {epic_id} --append-notes "Phase {N} verified: tests passed, user confirmed, checkpoint: {sha}"
```

### 4.7 Offer Pattern Elevation

> Any learnings from this phase worth elevating to patterns.md?

---

## Phase 5: Flow Completion

When all tasks complete:

1. Run `/flow-archive {flow_id}` to archive
2. Elevate remaining learnings to `patterns.md`
3. Update `.agent/prds.md` status to `[x]`

---

## Error Handling

If implementation fails:

1. Check error message
2. Use `mcp__pal__debug` for complex issues
3. Update `learnings.md` with issue details
4. If blocked, run `/flow-block {task_id} "{reason}"`

---

## Final Summary

```
Implementation Progress: {flow_id}

Tasks: {completed}/{total}
Current Phase: {N}
Last Commit: {sha}

Quality Gates:
- [ ] All tests pass
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] Patterns followed

Next Task: {description}
```

---

## Critical Rules

1. **TDD MANDATORY** - Write failing tests first
2. **BEADS IS SOURCE OF TRUTH** - Never write `[x]` or `[~]` markers to spec.md
3. **LEARNINGS CAPTURE** - Record patterns as discovered
4. **PHASE CHECKPOINTS** - Verify and checkpoint at phase end
5. **NO SKIP** - Use `/flow-skip` if task must be skipped
6. **USE `bd ready`** - Always check Beads for next task
