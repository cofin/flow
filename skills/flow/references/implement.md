
# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

## Usage

`flow-implement {flow_id}` or `flow-implement` (uses current flow)

## Worksheet execution contract

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - fail-closed-no-production-mutation
  - fresh-validated-plan-resume
transitions:
  - preflight-claim
  - mismatch-discover-block
  - nonblocking-discover-release
  - revised-plan-resume
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

<!-- flow-execution-contract: start -->
```yaml
contract: worksheet-execution-v1
preflight:
  checks:
    - dependencies_closed
    - worksheet_complete
    - verification_strategy_declared
    - plan_identity_matches
    - state_revision_matches
  before_operation: claim
  failure_transition: mismatch-discover-block
mismatch_classes:
  - code_drift
  - missing_decision
  - invalid_file_symbol_or_test_target
  - acceptance_contradiction
  - scope_expansion
  - invalid_verification_command
mismatch_report:
  required:
    - mismatch_class
    - evidence
    - impact
    - task_operation
    - unblock_condition
    - next_exact_planning_action
  unknown_fields: refuse
transitions:
  preflight-claim:
    operations: [claim]
    production_mutations: [worksheet_changes_only]
  mismatch-discover-block:
    operations: [discover, block]
    production_mutations: []
  nonblocking-discover-release:
    operations: [discover, release]
    production_mutations: []
  revised-plan-resume:
    operations: [claim]
    production_mutations: [worksheet_changes_only]
mismatch_routes:
  code_drift:
    transition: mismatch-discover-block
    task_operation: block
    handoff: revise
    unblock_condition: drift_resolved_in_new_validated_plan
    next_exact_planning_action: revise_then_refine_and_validate
  missing_decision:
    transition: mismatch-discover-block
    task_operation: block
    handoff: refine
    unblock_condition: decision_recorded_in_new_validated_plan
    next_exact_planning_action: refine_then_revise_and_validate
  invalid_file_symbol_or_test_target:
    transition: mismatch-discover-block
    task_operation: block
    handoff: revise
    unblock_condition: target_corrected_in_new_validated_plan
    next_exact_planning_action: revise_then_refine_and_validate
  acceptance_contradiction:
    transition: mismatch-discover-block
    task_operation: block
    handoff: revise
    unblock_condition: contradiction_resolved_in_new_validated_plan
    next_exact_planning_action: revise_then_refine_and_validate
  scope_expansion:
    transition: mismatch-discover-block
    task_operation: block
    handoff: revise
    unblock_condition: scope_decision_recorded_in_new_validated_plan
    next_exact_planning_action: revise_then_refine_and_validate
  invalid_verification_command:
    transition: mismatch-discover-block
    task_operation: block
    handoff: revise
    unblock_condition: verification_corrected_in_new_validated_plan
    next_exact_planning_action: revise_then_refine_and_validate
resume:
  transition: revised-plan-resume
  requires:
    - plan_identity_changed
    - plan_validation_passed
    - tracked_markdown_reloaded
    - preflight_repeated
  otherwise: stop_without_production_mutation
```
<!-- flow-execution-contract: end -->

The symbolic values above are the closed, testable execution policy. The
executor reports them together with concrete repository evidence and exact
commands or paths; it does not call a policy evaluator.

| Situation | Allowed work | State-sidecar operations | Planning handoff |
| --- | --- | --- | --- |
| All five preflight checks pass | Request `claim`, then execute only the selected worksheet | `claim` | none |
| A declared mismatch invalidates the worksheet | Read and reproduce only; make no production edit | `discover`, then `block` | the exact `revise` or `refine` route in `mismatch_routes` |
| A read-only discovery does not invalidate the worksheet, but the claimant stops | Make no further production edit | `discover`, then `release` | the release payload's exact next step |
| A revised task is ready to resume | Reload tracked Markdown and repeat all five checks | `claim` only after every resume guard passes | none |

The preflight reads the spec, task, dependencies, declared targets, and
canonical workflow. `plan_identity_matches` means the task and spec carry the
same `plan_revision` and `plan_commit`. `state_revision_matches` means the
executor uses the freshly read spec revision as the request's expected revision
and verifies the task revision is legal under the state contract. Worksheet
completeness includes its named files, symbols, tests, commands, acceptance
criteria, and selected `verification_strategy`; a syntactically complete but
stale target fails closed.

Every lifecycle mutation is an explicit request to `flow-reconciler` under the
Flow state contract. The executor never edits task/spec state fields or
checklist markers directly and never stores an `implement_state.json` or other
hidden execution-state copy.

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Read Spec Artifacts:**
    - `.agents/bundles/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agents/bundles/specs/{flow_id}/learnings.md` (if exists)
2. **Read Project Context:** `.agents/bundles/knowledge/patterns.md` and `.agents/bundles/knowledge/workflow.md`
3. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga.
    - If yes, read the parent roadmap's `.agents/bundles/specs/<parent_id>/spec.md`.
4. **Load Task List**:
    - Scan task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.

**CRITICAL:** Before starting, check whether `.agents/` is ignored by git. If it is ignored via `.gitignore`, `.git/info/exclude`, or global ignores, do NOT commit changes to artifacts inside it using git. Update them on disk only.
Extract canonical repo commands from `.agents/workflow.md` before coding. Prefer the documented setup, lint, test, typecheck, and full verification commands when they exist.

## Phase 2: Select Task

**PROTOCOL: Scan and select the next pending task from the filesystem.**

### 2.1 Check for Resume State

Check `.agents/bundles/specs/{flow_id}/tasks/` for any task file with `state: in_progress`. If one is found, resume it.

### 2.2 Find Next Task

1. **Scan**: Scan task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
2. **Parse & Resolve Dependencies**: Parse the YAML frontmatter of each task. A task is ready if its `state` is `"open"` and all dependencies listed in `depends_on` have `state` set to `"closed"`.
3. **Select**: Sort the ready tasks by priority (`P0` > `P1` > `P2` > `P3` > `P4`), then select the first one.

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

Complete the five-check preflight above against freshly loaded Markdown. Only
then request `claim` from `flow-reconciler`, including the expected plan
identity, expected spec state revision, explicit task target, and exact first
worksheet step. Reread the committed result before any production edit.

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

## Phase 5: Close Task

After fresh verification, request `close` from `flow-reconciler` with the exact
commit, command/result evidence, acceptance-criterion ids, expected plan
identity, expected spec state revision, and explicit task target. The sidecar
updates the task first and derived spec state last. Reread the terminal result;
do not close or reconcile Markdown directly.

The compact `verification_evidence` must be inside the `close request`; the
executor never writes verification Markdown separately. Only after the close
transaction succeeds may it optionally append a detailed `flow-git-note-v1`
record to the same functional commit with the procedure in
[Git Notes](../../../docs/git-notes.md). Before appending, it checks the note
stream for the stable attachment attempt id: exact record replay skips append,
while a different record with that id conflicts.
It must then request `note(category=git_note_attachment)` with the stable
attachment attempt id and the `attached|failed` diagnostic. Exact replay is a
sidecar no-op; a conflicting replay is refused. Attachment failure never
reopens the closed task, and no Flow workflow pushes notes. Never create or
mutate Git tags as evidence or as a fallback for an unavailable notes ref.

### 5.1 Log Learnings

If any patterns were discovered, append them to `.agents/bundles/specs/{flow_id}/learnings.md` using the Ralph format.

If `.agents/skills/flow-memory-keeper/SKILL.md` exists, invoke it so learnings, failures, sync cleanup, and archive prep are refined consistently.

## Phase 7: Phase Checkpoint

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

At the end of each phase:

1. **Run full test suite** — read output, confirm 0 failures.
2. **Run coverage check** — confirm target met.
3. **Dispatch code review** (recommended for multi-task phases):
   - Get the git range from the task file commit history (e.g. comparing the last checkpoint commit to HEAD).
   - Dispatch review subagent with: `spec.md` requirements, `patterns.md`, and the git range.
   - Fix Critical issues immediately, Important issues before proceeding.
   - Log findings to `learnings.md`.
4. **Record a phase checkpoint**: put the affected task ids, exact command/result evidence, and last functional commit in the spec-only `checkpoint` payload. Never create an empty checkpoint commit.
5. **Optionally attach detail**: only after checkpoint succeeds, append the detailed phase Git note to the last functional commit and report `attached|failed` through the canonical idempotent `note` operation.
6. **Prompt for pattern elevation**: "Are there learnings from this phase to elevate to `patterns.md`?"
7. **Ask user to verify**

**Verification red flags — STOP before claiming completion:**

- Using "should", "probably", "seems to"
- Expressing satisfaction before running verification ("Done!", "Perfect!")
- Trusting agent reports without independent check

## Parallel Task Execution Mode

When a phase has independent tasks that can be executed concurrently (prefer this mode when `superpowers:subagent-driven-development` is available):

1. **Controller** (flow:implement) manages task file status state transitions for all tasks
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
5. **TASK FILES ARE SOURCE OF TRUTH** — Read task status and SHAs from task Markdown; mutate them only through `flow-reconciler`.
6. **ALWAYS-SYNCED TASK LIST** — Every task state request must include the derived checklist/spec update in the same sidecar transaction.
7. **LOG LEARNINGS** — Capture patterns as you go
8. **LOCAL ONLY** — Never push automatically
9. **CODE REVIEW** — Dispatch review at phase checkpoints. Fix Critical/Important before proceeding.
10. **USE CANONICAL REPO COMMANDS** — Prefer the commands documented in `.agents/workflow.md`
11. **BE COLLABORATIVE** — Describe unrelated blockers factually and constructively; never use dismissive ownership-deflecting language
