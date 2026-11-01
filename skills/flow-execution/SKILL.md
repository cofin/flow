---
name: flow-execution
description: "Use when executing Flow task worksheets in isolated Goldfish turns (/flow:implement) or reporting active flow and task status (/flow:status)."
disable-model-invocation: true
---

# Flow Execution (Isolated Goldfish Executor & Public-Seam TDD)

<!-- lifecycle-ownership: owner=flow-execution; operations=implement,status -->

## Trigger

Use for `implement` ([`../flow/references/implement.md`](../flow/references/implement.md)) and `status` ([`../flow/references/status.md`](../flow/references/status.md)).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - five-check-preflight
  - public-seam-tdd-no-mocked-sut
  - fail-closed-no-production-mutation
  - atomic-task-commit
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

## Workflow

1. **Status & Five-Check Preflight (`/flow:status` or `/flow:implement`)**:
   - Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/<id>-<slug>.md` directly ([`../flow/references/state.md`](../flow/references/state.md)).
   - Run the five-check preflight (`dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`).
   - If any preflight check fails (such as `code_drift`, `missing_decision`, or `invalid_file_symbol_or_test_target`), stop before any production edit, record the evidence in `## Notes & Discoveries`, mark the task `state: blocked`, and route to `/flow:revise <flow_id>`.
   - Claim the ready task worksheet by setting `state: in_progress`, `claimed_by`, `claimed_at`, and `[ ]` &rarr; `[~]` in `spec.md`.
2. **Isolated Goldfish Subagent or `run_workflow` Pipeline Execution**:
   - Execute one vertical-slice task worksheet per `@executor` subagent turn (`model: inherit`). When executing multiple ready worksheets on Google Antigravity, prefer `run_workflow` `pipeline(worksheets, run_worksheet)` so each worksheet runs in a fresh isolated `@executor` context with `schema=TASK_RESULT_SCHEMA`.
3. **Public-Seam Vertical-Slice TDD & Hypothesis-Driven Bug Diagnosis**:
   - Collect the declared `verification_strategy` initial evidence (`behavior_tdd` and `regression_tdd` require observing the failing test at the confirmed public seam first).
   - Implement the vertical slice through the real System Under Test (mocking only external boundaries; never mocking the SUT or internal collaborators, and never writing tautological assertions) and place all tests in canonical module test files.
   - If a test or runtime failure is non-obvious, execute the 6-phase **Hypothesis-Driven Bug Diagnosis Loop** in [`../flow/references/discipline.md`](../flow/references/discipline.md) (tight red-capable feedback loop &rarr; reproduce & minimize &rarr; 3–5 ranked falsifiable hypotheses &rarr; `[DEBUG-<id>]` single-variable probe &rarr; public-seam regression test & fix &rarr; strip debug tags).
4. **Phase Checkpoints, Atomic Commit & Direct Markdown Close**:
   - Run the worksheet's verification and fast lint gates until exit code `0`.
   - Update the task worksheet (`state: completed`, `commit`, `last_verified_at`, `last_verified_commit`, `verification_evidence`, `## Notes & Discoveries`) and `spec.md` checklist (`- [x] [<sha>] <id> — ...`), and create one atomic signed local Git commit.
   - At each **Phase N Recovery Checkpoint** in `spec.md`, run the phase's aggregate test/lint/debloat gate and update `last_verified_checkpoint` in `spec.md`.

## Guardrails

- Execute one task worksheet per subagent turn; never batch unrelated tasks into one commit.
- Never mark a task `completed` without running its verification command freshly and observing exit code `0`.
- Never create or mutate Git tags or push without explicit user instruction.

## Output

Return the executed task ID, verification output, atomic commit SHA, updated flow status table, and next ready task or `/flow:review` handoff.

## Validation

Confirm the task worksheet's declared verification command exited `0`, `tasks/<id>-<slug>.md` frontmatter (`state`, `commit`) matches the `spec.md` checklist marker (`[x] [<sha>]`), and only task-owned paths were staged.
