# Flow Discipline Rules

Core rules for change-appropriate verification, public interface TDD, bug diagnosis, evidence-based review, and subagent or `run_workflow` execution.

## 1. Verification Strategy & Public Interface TDD

<!-- verification-strategy-contract: start -->
```yaml
required_task_field: verification_strategy
strategies:
  behavior_tdd:
    change_class: new_observable_behavior
    initial_evidence: focused_behavioral_test_fails_for_missing_behavior
  regression_tdd:
    change_class: defect_correction
    initial_evidence: focused_reproduction_fails_for_reported_defect
  characterization:
    change_class: behavior_preserving_refactor_or_deletion
    initial_evidence: focused_behavior_baseline_passes_before_change
  static_validation:
    change_class: manifest_config_generated_or_tooling
    initial_evidence: native_parser_lint_type_or_build_baseline
    check_proof: isolated_representative_violation_fails_with_expected_diagnostic
  documentation_validation:
    change_class: links_examples_or_document_structure
    initial_evidence: docs_native_baseline
  integration_acceptance:
    change_class: composition_of_existing_contracts
    initial_evidence: focused_integration_baseline_passes
    check_proof: injected_negative_states_prove_refusal_paths
low_signal_tests:
  reject:
    - mocking_the_module_under_test_or_internal_collaborators
    - mock_only_expected_value_recomputation
    - bulk_tests_written_before_any_code
    - standalone_remediation_or_audit_test_files
    - incidental_prompt_phrase
    - private_implementation_shape
    - duplicate_snapshot
    - file_existence_without_operational_contract
  retain:
    - observable_behavior_at_public_interface
    - public_contract
    - proven_regression
    - operationally_meaningful_structure
```
<!-- verification-strategy-contract: end -->

### Public Interface & Test-Strength Rules

- **The Interface Is the Test Surface**: Tests verify observable behavior through confirmed public interfaces, never private methods or internal wiring. A good test survives internal refactors unchanged.
- **Reject Weak Tests**:
  1. **Private-Detail Tests**: Mocks the module under test or internal collaborators, asserts internal call counts, or inspects internal storage instead of the public interface.
  2. **Mock-Only Tests**: Recomputes the expected value with the same formula as production code (`expect(total(items)).toBe(items.reduce(...))`). Expected values come from an independent known literal or worked example in `spec.md`.
  3. **Bulk Layer Tests**: Writing all tests before any implementation. Work one task at a time: one public interface, one test, one minimal implementation per cycle.
- **Canonical Test Modules Only**: Add tests to the existing test file for the module under test; never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Fast Chapter Check (`< 60s`) vs. Full Release Check (`> 60s`)**: Group edits across the active chapter (`<= 4` tasks per worker) so shared files are edited once.
- **Chapter Check Cadence**: Run the fast chapter check (`make lint` plus targeted unit tests in `< 60s`) once per chapter; run the full suite (`> 60s`) once at `/flow:finish` or CI.

## 2. Bug Diagnosis Loop

```text
NO FIXES OR THEORIES WITHOUT A FAST FAILING TEST FIRST
```

When diagnosing a hard bug, test failure, or performance regression, run these stages in order:

1. **Build a Fast Failing Test**:
   - Build one fast, repeatable, agent-runnable command (focused unit/integration test, CLI run with fixture input, or trace replay) that hits the bug path and fails on the reported symptom.
   - Tighten the loop by caching setup, narrowing scope, and pinning time or RNG. For flaky bugs, repeat the trigger until reproduction is reliable.
   - **Stop Condition**: Do not read code to invent theories before this failing command has been run and observed failing.
2. **Reproduce & Minimize**:
   - Watch the command fail on the reported symptom.
   - Strip inputs, callers, config, and steps one at a time, re-running after each cut until removing any remaining element makes the test pass.
3. **List Ranked Falsifiable Hypotheses**:
   - State `3–5` ranked hypotheses, each with a falsifiable prediction:
     > *"If `<X>` is the cause, then `<changing Y>` will make the symptom disappear or `<changing Z>` will make it worse."*
   - Record the hypotheses and root-cause notes with a timestamp under `## Notes & Discoveries` in `tasks/<id>-<slug>.md`.
4. **Targeted Single-Variable Probes**:
   - Map each probe to a prediction from Stage 3 and change one variable at a time.
   - Tag temporary debug logs with a unique prefix (`[DEBUG-a4f2]`) for easy cleanup.
   - For performance regressions, measure a baseline (profiler, timing harness, query plan) before bisecting.
5. **Public Interface Regression Test & Narrow Fix**:
   - Turn the minimized repro into a failing regression test at the public interface (if none can exercise the bug, note the gap in `## Notes & Discoveries` and route to `/flow:revise`).
   - Watch the regression test fail, apply the minimal fix, watch it pass, and re-run the Stage 1 command against the original scenario.
6. **Cleanup**:
   - Remove all `[DEBUG-...]` logs, delete throwaway files in `.agents/scratch/`, and state the confirmed root cause in the commit message and `## Notes & Discoveries`.
   - **Stop-Loop Limit**: If 3 fixes fail in a row, stop, mark the task `state: blocked`, and route to `/flow:revise`.

## 3. Verification & Finding Decisions

- **Run the Check Before Claiming It Passed**: Never claim a test, build, or lint check passes without running the exact command in the current turn, reading its full output, and confirming exit code `0`. Never hedge (`"should pass"`, `"probably fixed"`).
- **Direct Technical Evidence**: Never reflexively agree with a reviewer or user claim, and skip flattery or apologies. Lead with technical evidence and trade-offs.
- **Decide on Each Finding**: Verify every review finding against live code (`path/to/file::Symbol`) and `.agents/skills/review-*/references/false-positive-suppressions.md`:
  - **`ADOPT`**: Valid finding — apply the fix in present tense and re-verify.
  - **`CONTEST`**: False positive, misread of code, or out-of-scope creep — refute with `path/to/file::Symbol` or the matching `FP-*` rule.
  - **`ESCALATE`**: Genuine product or architecture trade-off — present options to the user via [`interaction.md`](interaction.md).

## 4. Thin Coordinator, Parallel Workers & Sync

- **Thin Coordinator Budget (`< 25k` Exploration Tokens) & Plan the Whole Scope**:
  - Keep the top-level coordinator focused on user planning, locking shared contracts in root `specs/<flow_id>/spec.md` + `chapters/index.md`, running workers, and checking chapter boundaries.
  - Default cohesive single features to `has_chapters: false`. Split into `chapters/` (`ch01..chNN`) only for staged checkpoints, parallel subsystems, or `empirical_dependent` triggers, with no artificial caps on task count, `read_set`, `files`, or `estimated_loc`.
  - Allow `compact` worksheets for straightforward tasks, and author multi-chapter specs in parallel Chapter Planner subagents.
- **Current-State Markdown Sync**:
  - When a chapter completes (`/flow:implement`) or a plan changes (`/flow:revise`), rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, root `specs/<flow_id>/spec.md` (`## 6. Current State & Remaining Plan Snapshot`), `.agents/bundles/knowledge/**`, and `docs/**` in place in present tense *before* review.
  - Living Markdown states current reality, remaining work, and the full plan; chronological history belongs in `.agents/bundles/log.md` and signed Git commits.
- **Model Routing & Packaged Workflows ([`orchestration.md`](orchestration.md))**:
  - Resolve `(model, effort)` via `flow models route --json`. Planning, independent spec review, semantic validation, and adversarial review use the strongest model (`strong`); stamp `planning_quality: degraded` and `planning_degraded_reason` (`planned_with_model`) whenever quota fallback prevents it.
  - Run tasks (`<= 250` LOC, `<= 3` files, `< 4k`-token pre-extracted briefs) in parallel steps (`<= 4` workers editing separate files) with `flow sync` between steps.
  - **Google Antigravity (`run_workflow` & `invoke_subagent`)**: Prefer packaged workflows (`workflows/flow-scout/workflow.py`, `workflows/flow-spec-planning/workflow.py`, `workflows/flow-chapter-pipeline/workflow.py`, `workflows/flow-dual-review/workflow.py`) using `type_name="self"`, compact schema cards, and `with_budget(...)`. Check `git status --porcelain` after read-only phases.
- **Independent Review Isolation**: Pass only disk paths (`spec.md`, `chapters/`, `tasks/*.md`, `.agents/skills/`, `knowledge/`, `docs/`) and exact `base_commit..head_commit` ranges to reviewers—never pass planning transcripts.
