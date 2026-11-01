---
name: flow-execution
description: "Use when implementing Flow task worksheets from .agents/bundles/specs/<flow_id>/tasks/ (/flow:implement) or reporting active flow and task status (/flow:status)."
disable-model-invocation: true
---

# Flow Execution

<!-- lifecycle-ownership: owner=flow-execution; operations=implement,status -->

## Trigger

Use for `implement` ([`../flow/references/implement.md`](../flow/references/implement.md)) and `status` ([`../flow/references/status.md`](../flow/references/status.md)).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - sut-integrity-no-mocked-sut
  - fail-closed-no-production-mutation
  - atomic-task-commit
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

## Workflow

1. **Status & Preflight (`/flow:status` or `/flow:implement`)**:
   - Read `.agents/bundles/specs/<flow_id>/spec.md` and `tasks/<id>-<slug>.md` directly ([`../flow/references/state.md`](../flow/references/state.md)).
   - Verify all `depends_on` tasks have `state: completed` and a recorded `commit` SHA.
   - Claim the ready task worksheet by setting `state: in_progress`, `claimed_by`, `claimed_at`, and `[-]` &rarr; `[~]` in `spec.md`.
2. **Isolated Subagent or `run_workflow` Pipeline Execution**:
   - Execute one task worksheet per `@executor` subagent turn (`model: inherit`). When executing multiple ready worksheets on Google Antigravity, prefer `run_workflow` `pipeline(worksheets, run_worksheet)` so each worksheet runs in a fresh isolated `@executor` context with `schema=TASK_RESULT_SCHEMA`.
3. **Initial Evidence & SUT-First Implementation**:
   - Collect the declared `verification_strategy` initial evidence (`behavior_tdd` and `regression_tdd` require observing the failing test first).
   - Implement the vertical slice against the real System Under Test (mocking only external I/O boundaries) and place all tests in canonical module test files.
4. **Phase Checkpoints, Atomic Commit & Direct Markdown Close**:
   - Run the worksheet's verification and fast lint gates until exit code `0`.
   - Update the task worksheet (`state: completed`, `commit`, `last_verified_at`, `last_verified_commit`, `verification_evidence`, `## Notes & Discoveries`) and `spec.md` checklist (`- [x] [<sha>] <id> — ...`), and create one atomic local Git commit.
   - At each **Phase N Recovery Checkpoint** in `spec.md`, run the phase's aggregate test/lint gate and update `last_verified_checkpoint` in `spec.md`.

## Guardrails

- Execute one task worksheet per subagent turn; never batch unrelated tasks into one commit.
- Never mark a task `completed` without running its verification command and observing exit code `0`.
- If code reality contradicts the worksheet (`plan_commit` drift or symbol mismatch), mark the task `state: blocked` with `blocked_reason` and `unblock_condition`, and route to `/flow:revise <flow_id>`.
- Never create or mutate Git tags or push without explicit user instruction.

## Output

Return the executed task ID, verification output, atomic commit SHA, updated flow status table, and next ready task or `/flow:review` handoff.

## Validation

Confirm the task worksheet's declared verification command exited `0`, `tasks/<id>-<slug>.md` frontmatter (`state`, `commit`) matches the `spec.md` checklist marker (`[x] [<sha>]`), and only task-owned paths were staged.
