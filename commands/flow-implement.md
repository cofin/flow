---
description: Execute tasks from plan (context-aware)
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch
---

# Flow Implement

Implementing flow: **$ARGUMENTS**

## Phase 0: Load Context

1. Load flow from `.agents/specs/{flow_id}/`
2. Read `spec.md` (unified spec+plan), `learnings.md`
3. Read `.agents/patterns.md` for project patterns
4. Read `.agents/workflow.md` for process guidelines and canonical repo commands

---

## 1.1 INITIALIZATION

**PROTOCOL: Load the Flow context.**

1. **Check for User Input:** First, check if the user provided a flow ID as an argument.
    * **If provided:** Use that `flow_id` and proceed to step 3.
    * **If NOT provided:** Proceed to step 2 to auto-discover the flow.

2. **Auto-Discovery (No Argument Provided):**
    * **Scan for Active Flows:** Read `.agents/flows.md` and look for flows marked as "Active" or "In Progress".
    * **Heuristics:**
        * If exact one active flow, select it.
        * If multiple, choose most recent.
        * If none, list pending and ask.

3. **Load Flow Context:**
    * **Read Artifacts:** `spec.md` (unified spec+plan), `learnings.md` (create if missing).
    * **Read Project Context:** Read `.agents/patterns.md` and `.agents/workflow.md`.
    * **Read Parent Context:** If this flow is part of a PRD/Saga, read `.agents/specs/<parent_id>/prd.md`.
    * **Read Durable Knowledge:** Load relevant `.agents/knowledge/` chapters before coding.
    * **Extract Canonical Commands:** Prefer the repo's existing setup, lint, test, typecheck, and full verification commands from `.agents/workflow.md` before inventing raw tool commands.

**CRITICAL:** Before starting, check whether `.agents/` artifacts are ignored by `.gitignore`, `.git/info/exclude`, or global git ignores. If they are ignored, do NOT commit those artifacts. Update them on disk only.

---

## Phase 1: Beads Sync

Use the active backend's workspace, ready-queue, in-progress, and flow-status commands.
If no backend is configured, skip backend sync and rely on `spec.md`.

---

## Phase 2: Task Selection (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers.

### 2.1 Primary: Use Beads

Use the active backend's ready/queue view and flow-status view.

Select task from the active backend's ready output. If multiple ready tasks, ask user which to start.

### 2.2 Fallback: Parse spec.md

If Beads unavailable or no tasks found:

1. Parse `spec.md` Implementation Plan section
2. Find first pending task (not yet in Beads or no status)
3. Create task in Beads if missing

---

## Phase 3: Task Execution Loop

For each task from the active backend's ready queue or `spec.md`:

### 3.0 Refinement and Delegation Gate

- Ask: "Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?"
- If not, invoke `flow-refine` before implementation or subagent dispatch.
- Before delegating to a lightweight executor, preserve context by passing the relevant spec or PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements.
- Do not silently descope if the task is larger than expected. Refine the task or ask the user how to prioritize.

### 3.1 Mark In Progress

**If task not in Beads, create it first:**

```bash
<active_backend_create_task>
<active_backend_mark_in_progress>
<active_backend_attach_notes>
```

**If task exists in Beads:**

```bash
<active_backend_mark_in_progress>
```

**CRITICAL:**

* Always include a clear description when creating tasks, then attach notes/context with the active backend's notes mechanism
* Beads is the source of truth - do NOT write `[~]` markers to spec.md

### 3.2 Write Failing Tests (Red Phase)

**CRITICAL:** Write tests BEFORE implementation.

1. Create test file following project conventions
2. Write tests that define expected behavior
3. Run the canonical test command from `.agents/workflow.md` when present; otherwise use `{test_command}`
4. **VERIFY tests fail as expected**

### 3.3 Implement (Green Phase)

1. Write minimum code to pass tests
2. Follow patterns from `patterns.md`
3. Run tests to verify they pass
4. Make the minimum targeted change set needed for the task. Do not add unrelated cleanup without approval.

### 3.4 Refactor

1. Clean up code with test safety
2. Ensure no duplication
3. Verify tests still pass

### 3.5 Verify Coverage

Use the canonical verification or coverage command from `.agents/workflow.md` when present; otherwise run:

```bash
{coverage_command}
```

Target: >80% coverage for new code.

### 3.6 Commit

```bash
git add {implementation_files} {non_ignored_context_files}
git commit -m "{type}({scope}): {description}"
```

Never use `git add -A` or `git add -f` for Flow work. If a file is ignored, leave it local-only.
Never force-add ignored Flow artifacts.

### 3.7 Sync to Beads (Source of Truth)

```bash
<active_backend_close_task>
```

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. It is MANDATORY that you run `/flow-sync` to update the markdown state after any task completion or status change.

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
<active_backend_attach_learning_note>
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

Prefer the repo's canonical aggregate verification command from `.agents/workflow.md` when it exists.

### 4.3 Manual Verification Plan

Present step-by-step verification for user:

```text
Manual Verification Steps:
1. {Command to run}
2. {Expected outcome}
3. {What to verify}
```

### 4.4 Await User Confirmation

> Does this meet your expectations? (yes/no)

### 4.5 Create Checkpoint

```bash
git commit --allow-empty -m "chore(checkpoint): Phase {N} complete"
```

Record in Beads:

```bash
<active_backend_record_checkpoint_note>
```

### Markdown Sync (Manual)

**CRITICAL:** Do NOT write markers directly to spec.md. It is MANDATORY that you run `/flow-sync` to update the markdown state after any task completion or status change.

### 4.7 Offer Pattern Elevation

> Any learnings from this phase worth elevating to patterns.md?

---

## Phase 5: Flow Completion

When all tasks complete:

1. Run `/flow-archive {flow_id}` to archive
2. Elevate remaining learnings to `patterns.md`
3. If a backend is enabled, finalize the flow there and run `/flow-sync` instead of editing markdown markers manually

---

## Error Handling

If implementation fails:

1. Check error message
2. Use standard debugging tools for complex issues
3. Update `learnings.md` with issue details
4. If blocked, use the active backend's blocked/notes command, or record the block in markdown-only mode if no backend is configured.
5. Describe unrelated failures factually and collaboratively. Never say the failure is "not your issue"; offer the smallest helpful next step and ask the user whether to handle it now or separately.

**Companion Skills for Debugging:**

* Use `flow:deepthink` to track hypothesis evolution and prevent circular investigation when debugging complex issues.
* Use `flow:tracer` to systematically trace execution paths before forming hypotheses about root causes.

---

## Final Summary

```text
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
5. **NO SKIP** - Use the active backend's skip/close flow with a recorded reason, or document the skip in markdown-only mode
6. **USE THE ACTIVE BACKEND'S READY QUEUE** - Always check Beads for next task when a backend is enabled
