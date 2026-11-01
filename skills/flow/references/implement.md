# Flow Implement (`/flow:implement`)

Execute approved task worksheets (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`) one vertical slice per isolated subagent turn using execution preflight checks, public-seam verification strategy, atomic Git commits, and direct Markdown state synchronization.

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - execution-preflight
  - public-seam-tdd-no-mocked-sut
  - fail-closed-no-production-mutation
  - atomic-task-commit
authority: skills/flow/references/implement.md
preflight:
  checks:
    - dependencies_closed
    - worksheet_complete
    - verification_strategy_declared
    - plan_identity_matches
    - target_symbols_exist
mismatch_classes:
  - code_drift
  - missing_decision
  - invalid_file_symbol_or_test_target
  - acceptance_contradiction
  - scope_expansion
  - invalid_verification_command
```
<!-- flow-execution-policy: end -->

## Usage

```text
/flow:implement [flow_id] [task_id]
```

## Phase 1: Load Context, Select Ready Task, & Run Execution Preflight

1. Read `.agents/bundles/specs/<flow_id>/spec.md`, `tasks/*.md`, `learnings.md` (if present), `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`.
2. **Resume or Select Next Ready Task**:
   - If a task has `state: in_progress`, inspect `git log -n 5 --oneline` and `git status --short -b` to see whether its commit already landed; if not, resume it.
   - Otherwise, select the first task with `state: pending` (or `open`) whose `depends_on` tasks are all `completed` (or `closed`), ordered by `(priority, created_at, id)`.
3. **Execution Preflight & Fail-Closed Mismatch Routing**:
   - Verify all preflight conditions before any production edit:
     1. `dependencies_closed`: Every task in `depends_on` is `completed`/`closed` with a valid `commit` SHA.
     2. `worksheet_complete`: `## Objective`, `## Context`, `## Steps`, `## Verification`, and `## Acceptance Criteria` are populated without placeholders.
     3. `verification_strategy_declared`: `verification_strategy` matches the task's change class.
     4. `plan_identity_matches`: `plan_revision` and `plan_commit` match between `spec.md` and the task worksheet.
     5. `target_symbols_exist`: All target `files:`, `tests:`, and `path/to/file::Symbol` anchors match current repository reality.
   - If any check fails, classify the mismatch (`code_drift`, `missing_decision`, `invalid_file_symbol_or_test_target`, `acceptance_contradiction`, `scope_expansion`, `invalid_verification_command`) and **make zero production code edits**:
     - Append the concrete evidence to `## Notes & Discoveries` in the task worksheet.
     - Set task `state: blocked`, `blocked_reason`, `unblock_condition`, and `next_step: "/flow:revise <flow_id>"`, update `spec.md` checklist to `[!]`, and hand off to `/flow:revise <flow_id>`.

## Phase 2: Claim Task & Dispatch Isolated `@executor`

1. Update the task worksheet frontmatter (`state: in_progress`, `claimed_by`, `claimed_at`, `state_revision: state_revision + 1`) and `spec.md` (`state: active`, `current_task: <id>`, checklist `- [~] <id> — ...`).
2. **Isolated Subagent / `run_workflow` Pipeline Execution**:
   - Dispatch `@executor` (`model: inherit`) with the task worksheet path, `spec.md` path, and matching `.agents/skills/<domain>/SKILL.md` and `knowledge/` chapters.
   - Never dispatch implementation subagents in parallel when tasks touch shared files.
   - When executing multiple sequential ready worksheets on Google Antigravity, prefer `run_workflow` `pipeline(worksheets, run_worksheet)` where each stage invokes `agent(type_name="executor", role=f"Execute {task_id}", schema=TASK_RESULT_SCHEMA, model="inherit")` so intermediate file reads and test output stay out of the main conversation's context window.

## Phase 3: Execute Declared Verification Strategy & Public-Seam TDD

| Strategy | Initial Evidence | Implementation & Final Evidence |
| --- | --- | --- |
| `behavior_tdd` | Write one focused behavioral test at the confirmed public seam in the canonical test module and run it to confirm it fails (Red) because the behavior is absent. | Implement the minimal production change, rerun until Green (`exit 0`), and run fast lint/typecheck gates. |
| `regression_tdd` | Write the minimized reproduction test at the public seam in the canonical test module and confirm it fails (Red) with the reported defect symptom. | Implement the narrow fix, rerun the regression test and module suite until Green (`exit 0`). |
| `characterization` | Run the focused behavior baseline at the public seam and confirm it passes before refactoring. | Refactor/debloat while keeping the behavior baseline unchanged and Green (`exit 0`). |
| `static_validation` | Run the native validator, linter, or typechecker baseline. | Prove any new check catches a representative isolated violation, restore clean state, and verify exit code `0`. |
| `documentation_validation` | Run the Markdown/link/OKF validation baseline. | Apply documentation updates and verify all link, schema, and lint checks exit `0`. |
| `integration_acceptance` | Run the focused integration baseline. | Verify end-to-end composition and negative refusal paths exit `0`. |

### Public-Seam & Test-Quality Rules

- **The Interface Is the Test Surface**: Test strictly through confirmed public interfaces. Respect the project's domain terminology from `knowledge/domains/<domain>.md`.
- **Never Write Implementation-Coupled or Tautological Tests**:
  - Never mock the System Under Test, mock internal collaborators, test private methods, or assert internal call counts. Mock only external system boundaries (third-party HTTP APIs, clock/randomness) when no local stand-in exists.
  - Never write tautological assertions that recompute the expected value using the same logic as the implementation; assert against an independent known literal or worked example from `spec.md`.
- **Canonical Test Files Only**: Add or update tests inside existing canonical module test files (`tests/<module>/test_<unit>.py`). Never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Inner-Loop Speed vs. Milestone Gates**: Run fast targeted tests and `make lint` during task execution; reserve the full test suite for **Phase Recovery Checkpoints** and `/flow:finish`.
- **When Tests Fail**: Follow the **Hypothesis-Driven Bug Diagnosis Loop** in [`discipline.md`](discipline.md). If 3 fixes fail in a row, stop, mark the task `blocked`, and route to `/flow:revise`.

## Phase 4: Atomic Commit, Direct State Close & Phase Recovery Checkpoints

1. Update the task worksheet frontmatter (`state: completed`, `commit: <sha>`, `last_verified_at`, `last_verified_commit`, `verification_evidence`, `claimed_by: null`, `claimed_at: null`) and append any non-obvious findings to `## Notes & Discoveries` (and `learnings.md` if reusable across the flow).
2. Update the corresponding `spec.md` checklist line (`- [x] [<sha>] <id> — ...`) and `## 5. Continuity Snapshot`.
3. Stage only the task-owned files (`files:`, `tests:`, and tracked `.agents/bundles/specs/<flow_id>/` files when `ignore_policy` is `shared`) and create one atomic signed local commit (`git commit -S -m "<type>(<scope>): <concise summary>"`). Never use `git add -A` or `git add -f`.
4. **Phase Recovery Checkpoint**:
   - When the last task of a phase in `spec.md` completes:
     1. Inspect the phase git diff and remove any temporary scaffolding, unused imports, or duplicate assertions (`debloat`).
     2. Execute the phase's **Phase Recovery Checkpoint** command (`make lint` + full phase/repository test suite) and confirm exit code `0`.
     3. Update `last_verified_checkpoint: <HEAD_SHA>` in `spec.md`.
5. When all tasks in `spec.md` are `[x] [<sha>]`, hand off to `/flow:review <flow_id>` or `/flow:finish <flow_id>`.
