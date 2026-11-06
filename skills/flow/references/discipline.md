# Flow Discipline Rules

Normative rules for change-appropriate verification, Public-Seam TDD, Hypothesis-Driven Bug Diagnosis, critical reassessment, and subagent/`run_workflow` orchestration.

## 1. Verification Strategy Contract & Public-Seam TDD

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
    - mocking_the_system_under_test_or_internal_collaborators
    - tautological_expected_value_recomputation
    - horizontal_bulk_test_slicing
    - standalone_remediation_or_audit_test_files
    - incidental_prompt_phrase
    - private_implementation_shape
    - duplicate_snapshot
    - file_existence_without_operational_contract
  retain:
    - observable_behavior_at_public_seam
    - public_contract
    - proven_regression
    - operationally_meaningful_structure
```
<!-- verification-strategy-contract: end -->

### Public-Seam & Test-Strength Rules

- **The Interface Is the Test Surface**: Tests verify observable behavior through confirmed public seams, never private methods or internal wiring. A good test survives internal refactors unchanged.
- **Reject Test Anti-Patterns**:
  1. **Implementation-Coupled**: Mocks the System Under Test or internal collaborators, asserts internal call counts/order, or bypasses the public retrieval seam to inspect internal storage directly.
  2. **Tautological**: Recomputes the expected value using the same formula as the production code (`expect(total(items)).toBe(items.reduce(...))`) so it passes by construction. Expected values must come from an independent known literal or worked example in `spec.md`.
  3. **Horizontal Slicing**: Writing all tests in bulk before any implementation. Work in **vertical slices**: one public seam, one test, one minimal implementation per cycle.
- **Canonical Test Modules Only**: Always add tests to the existing canonical test file for the module under test; never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Inner-Loop Speed vs. Milestone Gates**: Run `make lint` and focused task tests in inner loops; run full test suites and debloat sweeps at **Phase Recovery Checkpoints** and `/flow:finish`.

## 2. Hypothesis-Driven Bug Diagnosis Loop

```text
NO FIXES OR THEORIES WITHOUT A TIGHT RED-CAPABLE FEEDBACK LOOP FIRST
```

When diagnosing a hard bug, test failure, or performance regression, execute these stages in order:

1. **Stage 1 — Build a Tight Red-Capable Feedback Loop**:
   - Construct **one fast, deterministic, agent-runnable command** (focused unit/integration test, CLI invocation with fixture input, trace replay, or minimal harness) that drives the bug code path and goes **Red** on the exact user symptom.
   - Tighten the loop (cache setup, narrow scope, pin time/RNG). For flaky bugs, loop the trigger or narrow timing windows until the reproduction rate is deterministic enough to debug.
   - **Stop Condition**: Do not read code to invent theories before this red-capable command has been run and observed failing.
2. **Stage 2 — Reproduce & Minimise**:
   - Watch the command go red on the exact reported symptom.
   - Strip inputs, callers, config, and steps **one at a time**, re-running the loop after each cut, until **every remaining element is load-bearing** (removing any one makes the loop go green).
3. **Stage 3 — Generate Ranked Falsifiable Hypotheses**:
   - Avoid anchoring on a single guess. State `3–5` ranked hypotheses, each with a falsifiable prediction:
     > *"If `<X>` is the cause, then `<changing Y>` will make the symptom disappear / `<changing Z>` will make it worse."*
   - Record the ranked hypotheses and root-cause notes with a timestamp under `## Notes & Discoveries` in `tasks/<id>-<slug>.md`.
4. **Stage 4 — Targeted Single-Variable Instrumentation**:
   - Map each probe to a specific prediction from Stage 3 and **change one variable at a time**.
   - Tag every temporary debug log with a unique prefix (`[DEBUG-a4f2]`) so cleanup is a single grep.
   - For performance regressions, establish a baseline measurement (profiler, timing harness, query plan) first before bisecting.
5. **Stage 5 — Public-Seam Regression Test & Narrow Fix**:
   - Turn the minimized repro into a failing regression test at the appropriate **public seam** (if no public seam can exercise the real call-site bug pattern, record that architectural seam gap in `## Notes & Discoveries` and route via `/flow:revise`).
   - Watch the regression test fail, apply the minimal fix, watch it pass, and re-run the Stage 1 feedback loop against the original un-minimized scenario.
6. **Stage 6 — Cleanup**:
   - Remove all `[DEBUG-...]` instrumentation (`grep` the prefix), delete any throwaway harness in `.agents/scratch/`, and state the confirmed root cause in the commit message and `## Notes & Discoveries`.
   - **Escalation Rule**: If 3 fixes fail in a row, **STOP**—mark the task `state: blocked` and route to `/flow:revise` to question the architecture with the user.

## 3. Critical Thinking, Verification, & Finding Adjudication (`ADOPT` / `CONTEST` / `ESCALATE`)

- **Verification Iron Law**: Never claim a test, build, or lint gate passes without running the exact command freshly in the current turn, reading its full output, and confirming exit code `0`. Never use hedging (`"should pass"`, `"probably fixed"`).
- **Zero Performative Agreement**: Never reflexively agree with a subagent reviewer or user assertion, and never use flattery (`"Great point"`, `"Brilliant"`, `"You're absolutely right"`) or polite apologies. Lead directly with technical evidence and trade-offs.
- **Evidence-Backed Adjudication**: Verify every review finding against the live codebase (`path/to/file::Symbol`) and `.agents/skills/review-*/references/false-positive-suppressions.md`:
  - **`ADOPT`**: Valid finding — apply the fix in present tense and re-verify.
  - **`CONTEST`**: False positive, misread of existing code, or YAGNI scope creep — refute by citing the exact `path/to/file::Symbol` or `FP-*` suppression rule.
  - **`ESCALATE`**: Genuine product/architectural trade-off — present a `structured-choice-v1` decision to the user.

## 4. Thin Coordinator, Horizontal Subagent Scaling, & Present-Tense Sync

- **Thin Coordinator Budget (`< 25k` Exploration Tokens) & Anti-Truncation**:
  - Keep the top-level coordinator focused on user co-design, locking cross-chapter contracts in root `specs/<flow_id>/spec.md` + `chapters/index.md`, orchestrating subagents, and enforcing chapter boundaries so sessions never run for hours or compact repeatedly.
  - Scale detail **horizontally across isolated subagents**, never by truncating scope or compressing distinct behaviors into vague tasks: decompose larger initiatives into as many bounded chapters (`ch01..chNN`, `1–4` tasks per chapter, `<= 250` net lines and `read_set <= 6` files per task) as required—including dedicated OKF knowledge and user-documentation tasks/chapters—authored upfront in parallel Chapter Planner subagents.
- **Present-Tense Living Markdown Sync (Zero History Inside Docs)**:
  - Whenever a chapter completes (`/flow:implement`) or a plan changes (`/flow:revise`), rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, root `specs/<flow_id>/spec.md` (`## 6. Current State & Remaining Plan Snapshot`), `.agents/bundles/knowledge/**`, and `docs/**` **in place in present tense** *before* chapter code review so reviewers verify both code and Markdown fidelity.
  - Living Markdown states only current verified reality, remaining chapters/tasks, and the full plan; chronological history belongs exclusively in `.agents/bundles/log.md` and signed Git commits.
- **Always Inherit Model & Full-Capability Subagent Dispatch**:
  - Default all subagent dispatches (`invoke_subagent`, `run_workflow` `agent(...)`, or host subagent tools) to `model: inherit` unless the user explicitly asks for another model.
  - **Google Antigravity (`run_workflow` & `invoke_subagent`)**: Always dispatch subagents with `type_name="self"` (`TypeName="self"`, `model="inherit"`), passing the on-disk `agents/<role>.md` (or `.agents/agents/<domain>-*.md`) contract path in the brief so subagents inherit full file read/write, shell, code search, and MCP capabilities. After read-only scout or review phases (`researcher`, `code-reviewer`, `quality-reviewer`), assert `git status --porcelain` matches the pre-dispatch working tree.
  - Use `phase(name)` and `log(msg)` to surface stage progress, `parallel(items, fn)` for sharded `SubsystemDigest` scouts, upfront parallel Chapter Planner authoring, per-chapter zero-context reviews (reusing persistent multi-turn handles `reviewer = agent(...); await reviewer(...)` across adjudication rounds), and sharded OKF/documentation synthesis, and `pipeline(worksheets, fn)` for sequential single-chapter task execution (`<= 4` tasks per chapter, then hard stop).
- **Zero-Context Isolation**: Pass **only disk paths** (`spec.md`, `chapters/`, `tasks/*.md`, `.agents/skills/`, `knowledge/` chapters, and `docs/`) and exact `base_commit..head_commit` ranges to reviewers—never pass conversational planning transcripts.
