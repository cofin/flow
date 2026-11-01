# Flow Implement (`/flow:implement`)

Execute approved task worksheets (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`) one vertical slice per subagent turn using the declared verification strategy, SUT integrity, atomic Git commits, and direct Markdown state synchronization.

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

## Usage

```text
/flow:implement [flow_id] [task_id]
```

## Phase 1: Load Context & Select Ready Task Worksheet

1. Read `.agents/bundles/specs/<flow_id>/spec.md`, `tasks/*.md`, `learnings.md` (if present), `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`.
2. **Resume or Select Next Ready Task**:
   - If a task has `state: in_progress`, inspect `git log -n 5 --oneline` and `git status --short -b` to see whether its commit already landed; if not, resume it.
   - Otherwise, select the first task with `state: pending` (or `open`) whose `depends_on` tasks are all `completed` (or `closed`), ordered by `(priority, created_at, id)`.
3. **Preflight Checks (Fail Closed Before Any Production Edit)**:
   - Verify `plan_revision` and `plan_commit` match between `spec.md` and the task worksheet.
   - Verify all target `files:` and `path/to/file::Symbol` anchors in the worksheet match current repository reality.
   - If code reality drifted or a decision is missing, do **not** improvise production edits: mark the task `state: blocked` (`blocked_reason`, `unblock_condition`, `next_step: "/flow:revise <flow_id>"`), update `spec.md` checklist to `[!]`, and hand off to `/flow:revise <flow_id>`.

## Phase 2: Claim Task & Dispatch Isolated `@executor`

1. Update the task worksheet frontmatter (`state: in_progress`, `claimed_by`, `claimed_at`, `state_revision: state_revision + 1`) and `spec.md` (`state: active`, `current_task: <id>`, checklist `- [~] <id> — ...`).
2. **Subagent / `run_workflow` Pipeline Execution**:
   - Dispatch `@executor` (`model: inherit`) with the task worksheet path, `spec.md` path, and matching `.agents/skills/<domain>/SKILL.md` and `knowledge/` chapters.
   - When executing multiple sequential ready worksheets on Google Antigravity, prefer `run_workflow` `pipeline(worksheets, run_worksheet)` where each stage invokes `agent(type_name="executor", role=f"Execute {task_id}", schema=TASK_RESULT_SCHEMA, model="inherit")` so intermediate file reads and test output stay out of the main conversation's context window.

## Phase 3: Execute Declared Verification Strategy & Enforce SUT Integrity

| Strategy | Initial Evidence | Implementation & Final Evidence |
| --- | --- | --- |
| `behavior_tdd` | Write the behavioral test in the canonical test module and run it to confirm it fails (Red) because the behavior is absent. | Implement the minimal production change, rerun until Green (`exit 0`), and run fast lint/typecheck gates. |
| `regression_tdd` | Write the reproduction test in the canonical test module and confirm it fails (Red) with the reported defect symptom. | Implement the fix, rerun the regression test and module suite until Green (`exit 0`). |
| `characterization` | Run the focused behavior baseline and confirm it passes before refactoring. | Refactor/debloat while keeping the behavior baseline unchanged and Green (`exit 0`). |
| `static_validation` | Run the native validator, linter, or typechecker baseline. | Prove any new check catches a representative isolated violation, restore clean state, and verify exit code `0`. |
| `documentation_validation` | Run the Markdown/link/OKF validation baseline. | Apply documentation updates and verify all link, schema, and lint checks exit `0`. |
| `integration_acceptance` | Run the focused integration baseline. | Verify end-to-end composition and negative refusal paths exit `0`. |

### System-Under-Test (SUT) & Code Hygiene Rules

- **Canonical Test Files Only**: Add or update tests inside the existing canonical module test files (`tests/<module>/test_<unit>.py`). Never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Never Mock the SUT**: Exercise the real System Under Test; mock only external network, process, or third-party I/O boundaries when necessary.
- **Inner-Loop Speed**: Run fast targeted tests and `make lint` during task execution; reserve the full test suite for **Phase Recovery Checkpoints** and `/flow:finish`.

## Phase 4: Atomic Commit, Direct State Close & Phase Checkpoints

1. Update the task worksheet frontmatter (`state: completed`, `commit: <sha>`, `last_verified_at`, `last_verified_commit`, `verification_evidence`, `claimed_by: null`, `claimed_at: null`) and append any non-obvious findings to `## Notes & Discoveries` (and `learnings.md` if reusable across the flow).
2. Update the corresponding `spec.md` checklist line (`- [x] [<sha>] <id> — ...`) and `## 5. Continuity Snapshot`.
3. Stage only the task-owned files (`files:`, `tests:`, and tracked `.agents/bundles/specs/<flow_id>/` files when `ignore_policy` is `shared`) and create one atomic local commit (`<type>(<scope>): <concise summary>`). Never use `git add -A` or `git add -f`.
4. **Phase Recovery Checkpoint**: When the last task of a phase in `spec.md` completes, execute the phase's **Phase N Recovery Checkpoint** command and update `last_verified_checkpoint` in `spec.md`.
5. When all tasks in `spec.md` are `[x] [<sha>]`, hand off to `/flow:review <flow_id>` or `/flow:finish <flow_id>`.
