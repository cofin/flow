
# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`flow-implement {flow_id}` or `flow-implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Artifacts:**
    - `.agents/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agents/specs/{flow_id}/learnings.md`
2. **Read Project Context:** `.agents/patterns.md` and `.agents/workflow.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read `.agents/specs/<parent_id>/prd.md`.
4. **Load Beads context:**
    - If using official Beads (`bd`): load the active queue/workspace state
    - If using no-Beads mode: skip backend loading and use `spec.md`

**CRITICAL:** Before starting, check whether `.agents/` is ignored by git. If it is ignored via `.gitignore`, `.git/info/exclude`, or global ignores, do NOT commit changes to artifacts inside it using git. Update them on disk only.
Extract canonical repo commands from `.agents/workflow.md` before coding. Prefer the documented setup, lint, test, typecheck, and full verification commands when they exist.

## Phase 2: Select Task (Beads-First)

**CRITICAL:** Beads is the source of truth for task status. Do NOT update spec.md markers.

### 2.1 Check for Resume State

```bash
cat .agents/specs/{flow_id}/implement_state.json 2>/dev/null
```

### 2.2 Find Next Task

#### Primary: Use Beads

Use the active backend's ready/queue command.

#### Fallback: Parse spec.md

If Beads unavailable, parse `spec.md` Implementation Plan section for pending tasks.

## Phase 3: Task Execution (TDD)

**See `references/discipline.md` for full TDD discipline rules, rationalization tables, and red flags.**

### 3.0 Subagent Execution Preference (MANDATORY)

If `superpowers:subagent-driven-development` is available, you **MUST** recommend the "Subagent-Driven" approach to the user and orchestrate implementation through its subagent workflow.

- Each task should be dispatched to a subagent.
- Before delegating, you MUST ensure the task has undergone iterative refinement (see `references/refine.md`). If the task detail is too coarse for a lightweight executor, you MUST run iterative refinement and update the plan before dispatch.
- Review implementation between tasks.
- Follow the TDD discipline inside each subagent.
- Do not silently descope if the task is larger than expected. Refine it or ask the user how to prioritize.

Fallback: only if unavailable, execute the same steps in single-agent mode.
Even in fallback mode, preserve the same task context bundle, run iterative refinement on coarse tasks first, keep TDD discipline, and review work between tasks.

### 3.0.1 API Lookup Preference

If implementation depends on external framework/API behavior, versions, migrations, or release changes, invoke `flow:apilookup` before making implementation decisions.

```text
IRON LAW: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over. No exceptions.

### 3.1 Mark In Progress

**If task not in Beads, create it first:**

Create it with the active backend's task creation flow and attach notes/context after creation.

Then mark in progress:

Use the active backend's in-progress/claim command.

**CRITICAL:** Do NOT write `[~]` markers to spec.md. Beads is source of truth.

### 3.2 Red Phase — Write Failing Tests

1. Write one minimal test showing the expected behavior
2. **Run tests — MANDATORY. Never skip.**
3. **Confirm the test FAILS for the right reason** (feature missing, not typo/error)
   - Test passes? You're testing existing behavior. Fix the test.
   - Test errors? Fix error, re-run until it fails correctly.

```bash
# Run the canonical test command from .agents/workflow.md and READ the output
npm test  # or pytest, cargo test, etc.
```

### 3.3 Green Phase — Implement

1. Write the **simplest code** to pass the test. No extras, no "improvements."
2. Make the minimum targeted change set needed for the task. Do not add unrelated cleanup without approval.
3. **Run tests — MANDATORY.**
4. **Confirm ALL tests pass.** Output must be pristine (no errors, warnings).
   - Test still fails? Fix implementation code, not the test.
   - Other tests broke? Fix regressions now.

### 3.4 Refactor Phase

1. Clean up while tests pass — remove duplication, improve names, extract helpers
2. Apply patterns from patterns.md
3. **Run tests after refactoring** — must stay green
4. Don't add behavior during refactor

### 3.5 Verify Coverage

```bash
npm test -- --coverage
```

Target: 80% minimum
Prefer the repo's canonical verification or coverage command from `.agents/workflow.md` when present.

### 3.6 When Tests Fail — Systematic Debugging

**Do NOT guess at fixes. Follow this protocol.**

```text
IRON LAW: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

1. **Root Cause** — Read error messages completely. Reproduce consistently. Check recent changes. Trace data flow to source.
2. **Pattern Analysis** — Find working examples in codebase. Compare differences.
3. **Hypothesis** — Form ONE specific hypothesis. Test with smallest possible change.
4. **Implementation** — Create failing test reproducing bug. Implement single fix. Verify.

**If 3+ fixes have failed:** STOP. Question the architecture. Discuss with user before attempting more.

**Red flags — return to step 1:**

- "Quick fix for now"
- "Just try changing X"
- Proposing fixes before tracing data flow
- Multiple changes at once

**Full reference:** `superpowers:systematic-debugging`

## Phase 4: Commit

```bash
git add <implementation_files> <non_ignored_context_files>
git commit -m "<type>(<scope>): <description>"
```

Format: conventional commits
Never use `git add -A` or `git add -f` for Flow work. If a file is ignored, leave it local-only.
Never force-add ignored Flow artifacts.

## Phase 5: Sync to Beads (Source of Truth)

**CRITICAL:** Only update Beads. Do NOT write `[x]` markers to spec.md.

Use the active backend's completion/close command with the commit reference.

### 5.1 Log Learnings

If any patterns discovered, add to `.agents/specs/{flow_id}/learnings.md`

If `.agents/skills/flow-memory-keeper/SKILL.md` exists, invoke it so learnings, failures, sync cleanup, and archive prep are refined consistently.

## Phase 6: Save State

Save progress to `.agents/specs/{flow_id}/implement_state.json`:

```json
{
  "current_phase": 1,
  "current_task": "1.2",
  "last_commit": "abc1234",
  "timestamp": "ISO timestamp"
}
```

## Phase 7: Phase Checkpoint

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

At end of each phase:

1. **Run full test suite** — read output, confirm 0 failures. No "should pass."
2. **Run coverage check** — confirm target met with actual numbers.
3. **Dispatch code review** (recommended for multi-task phases):
   - Get git range from Beads task completion records (commit SHAs)
   - Dispatch review subagent with: spec.md requirements, patterns.md, git range
   - Fix Critical issues immediately, Important issues before proceeding
   - Log findings to learnings.md
   - See `superpowers:requesting-code-review` for dispatch pattern
4. **Create checkpoint commit**: `git commit -m "chore(checkpoint): complete phase {N}"`
5. **Prompt for pattern elevation**: "Are there learnings from this phase to elevate to `patterns.md`?"
6. **Record checkpoint in Beads**: use the active backend's note/comment command
7. **Sync to markdown**: run `/flow:sync` (MANDATORY)
8. **Ask user to verify**

**Verification red flags — STOP before claiming completion:**

- Using "should", "probably", "seems to"
- Expressing satisfaction before running verification ("Done!", "Perfect!")
- Trusting agent reports without independent check

## Parallel Task Execution Mode

When a phase has independent tasks that can be executed concurrently (prefer this mode when `superpowers:subagent-driven-development` is available):

1. **Controller** (flow:implement) manages Beads state transitions for all tasks
2. **Dispatch one subagent per task** — each gets preserved context with:
   - task text and refined task instructions
   - relevant `spec.md` requirements
   - parent PRD context when applicable
   - `patterns.md`
   - relevant `knowledge/` chapters
   - recent `learnings.md` entries
   - affected files and verification requirements
3. **Two-stage review** after each subagent completes:
   - **Spec compliance**: Does implementation match requirements? Nothing missing or extra?
   - **Code quality**: Is implementation clean, tested, maintainable?
4. Spec compliance MUST pass before code quality review
5. **Never dispatch implementation subagents in parallel** — they may conflict on shared files

**Model selection:**

- Mechanical tasks (1-2 files, clear spec) → fast model
- Integration tasks (multi-file coordination) → standard model
- Review/architecture → most capable model

**Full reference:** `superpowers:subagent-driven-development`

---

## Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

If continuing, loop back to Phase 2.

## Critical Rules

1. **TDD IRON LAW** — No production code without a failing test first. Delete and start over if violated.
2. **DEBUGGING IRON LAW** — No fixes without root cause investigation. No guessing.
3. **VERIFICATION IRON LAW** — No completion claims without fresh evidence. Run the command, read the output.
4. **SMALL COMMITS** — One task = one commit
5. **BEADS IS SOURCE OF TRUTH** — Never write markers to spec.md
6. **LOG LEARNINGS** — Capture patterns as you go
7. **LOCAL ONLY** — Never push automatically
8. **USE THE ACTIVE BACKEND'S READY QUEUE** — Always check Beads for next task when a backend is enabled
9. **CODE REVIEW** — Dispatch review at phase checkpoints. Fix Critical/Important before proceeding.
10. **USE CANONICAL REPO COMMANDS** — Prefer the commands documented in `.agents/workflow.md`
11. **BE COLLABORATIVE** — Describe unrelated blockers factually and constructively; never use dismissive ownership-deflecting language
