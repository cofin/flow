# Flow Discipline Rules

Normative rules for change-appropriate verification, System-Under-Test (SUT) integrity, root-cause debugging, critical thinking, and subagent/`run_workflow` orchestration.

## 1. Verification Strategy Contract

<!-- verification-strategy-contract: start -->
```yaml
contract: verification-strategy-v1
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
    gate_proof: isolated_representative_violation_fails_with_expected_diagnostic
  documentation_validation:
    change_class: links_examples_or_document_structure
    initial_evidence: docs_native_baseline
  integration_acceptance:
    change_class: composition_of_existing_contracts
    initial_evidence: focused_integration_baseline_passes
    gate_proof: injected_negative_states_prove_refusal_paths
low_signal_tests:
  reject:
    - mocking_the_system_under_test
    - standalone_remediation_or_audit_test_files
    - incidental_prompt_phrase
    - private_implementation_shape
    - duplicate_snapshot
    - file_existence_without_operational_contract
  retain:
    - observable_behavior
    - public_contract
    - proven_regression
    - operationally_meaningful_structure
```
<!-- verification-strategy-contract: end -->

### System-Under-Test (SUT) Integrity

- **Never Mock the SUT**: Unit and integration tests must exercise the real System Under Test. Mock only external network, process, or third-party boundary interfaces when required.
- **Canonical Test Modules Only**: Always add tests to the existing canonical test file for the module under test; never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Inner-Loop Speed vs. Milestone Gates**: Run `make lint` and focused task tests in inner loops; run full test suites and debloat sweeps at **Phase Recovery Checkpoints** and `/flow:finish`.

## 2. Root-Cause Debugging Discipline

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

1. **Reproduce & Trace**: Read error outputs completely, reproduce consistently, and trace dataflow to the source (`path/to/file::Symbol`).
2. **Record in Task Worksheet**: Log root-cause findings with a timestamp under `## Notes & Discoveries` in `tasks/<id>-<slug>.md` so context survives session compaction.
3. **Single-Variable Hypothesis**: Test one specific hypothesis at a time. If 3 fixes fail in a row, stop, mark the task `blocked`, and route to `/flow:revise` to re-evaluate the architecture.

## 3. Finding Adjudication & Critical Thinking (`ADOPT` vs. `CONTEST`)

- **Zero Performative Agreement**: Never reflexively agree with a subagent reviewer or apply unverified suggestions.
- **Evidence-Backed Adjudication**: Verify every review finding against the actual codebase (`path/to/file::Symbol`) and `.agents/skills/review-*/references/false-positive-suppressions.md`. Explicitly mark each finding **`ADOPT`** (with the fix applied) or **`CONTEST`** (citing the exact code or `FP-*` suppression rule that refutes it).

## 4. Subagent & Python `run_workflow` Orchestration

- **Always Inherit Model**: Default all subagent dispatches (`invoke_subagent`, `run_workflow` `agent(...)`, or host subagent tools) to `model: inherit` unless the user explicitly asks for another model.
- **Prefer `run_workflow` When Available (Google Antigravity)**:
  - Use `phase(name)` and `log(msg)` to surface stage progress.
  - Use `parallel(items, fn)` with `agent(prompt, schema=..., role=..., type_name=..., model="inherit")` for concurrent zero-context spec/code review fan-out and parallel `@researcher` subsystem audits, enforcing strict JSON Schema validation on subagent responses.
  - Reuse persistent multi-turn subagent handles (`reviewer = agent(...); await reviewer(...)`) across review rounds so reviewers verify `ADOPT` fixes in their existing isolated context.
  - Use `pipeline(worksheets, fn)` for sequential multi-worksheet execution in isolated `@executor` turns.
- **Zero-Context Review Isolation**: Pass **only disk paths** (`spec.md`, `tasks/*.md`, `.agents/skills/`, and `knowledge/` chapters) and exact `base_commit..head_commit` ranges to reviewers—never pass conversational planning transcripts.
