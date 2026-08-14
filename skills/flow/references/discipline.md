
# Flow Discipline Rules

Consolidated enforcement rules for change-appropriate verification, debugging, and fresh evidence. Every task declares and justifies one strategy before implementation.

## Contents

- [Verification strategies](#verification-strategy-contract)
- [Debugging](#debugging-iron-law)
- [Fresh evidence](#verification-iron-law)
- [Critical thinking and review](#critical-thinking-iron-law)
- [Subagent orchestration](#subagent-orchestration)

## Verification strategy contract

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
waiver:
  strategy_still_required: true
  required: [rationale, approver, compensating_evidence]
  missing_fields: refuse
low_signal_tests:
  reject:
    - incidental_prompt_phrase
    - private_implementation_shape
    - duplicate_snapshot
    - file_existence_without_operational_contract
    - source_scanner_when_native_gate_exists
  retain:
    - observable_behavior
    - public_contract
    - proven_regression
    - operationally_meaningful_structure
```
<!-- verification-strategy-contract: end -->

The planner and refiner choose the strategy from the actual change class, state why it fits, and name exact commands and expected results. A waiver does not replace the declared strategy; it records why one required proof cannot run, who approved that exception, and what compensating evidence remains.

### Strategy execution

- **Behavior TDD:** write one minimal behavioral test, run it, and confirm it fails because the behavior is absent. Implement minimally, rerun green, then refactor while green.
- **Regression TDD:** reproduce the reported defect first, verify the intended failing symptom, implement the narrow fix, and rerun the regression plus relevant suite.
- **Characterization:** record a green focused baseline before behavior-preserving cleanup, make the smallest change, and require unchanged behavior afterward. Do not manufacture a red test.
- **Static validation:** run the native parser, lint, type, or build baseline. Prove a new or replacement gate with a representative isolated violation, require the expected failure/diagnostic, restore it, and require green.
- **Documentation validation:** use link, example, docs-build, spelling, or structure checks appropriate to the documentation. Do not invent a unit-test failure for prose.
- **Integration acceptance:** begin from a green focused baseline for the already-implemented contracts, compose the end-to-end scenario, and inject negative states to prove refusal paths. If implementation is missing, stop and route the gap through revise; do not repair it inside the acceptance task.

### Low-signal test policy

Reject assertions over incidental prompt phrases, private implementation shape, duplicate snapshots, and pure file existence when no operational contract depends on the path. Prefer configured parsers, linters, type checkers, and build tools to ad hoc source scanners when they express the rule. Retain meaningful structural tests when layout, signatures, exports, immutability, memory, compilation, reflection, serialization, or isolation is the contract.

---

## Debugging Iron Law

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

### The Task-First Investigation Mandate

**CRITICAL:** Every investigation finding, root cause discovery, and hypothesis test MUST be recorded directly in the active task file (e.g. `.agents/bundles/specs/<flow_id>/tasks/<task_id>.md`) under the `## Notes & Discoveries` heading, prefixed with a timestamp.

1. **Investigate**: Trace data flow, read errors, reproduce.
2. **Note**: Append to `## Notes & Discoveries`: `[YYYY-MM-DD HH:MM] Root cause: [Description]. Found in [file:line].`
3. **Commit**: Discoveries and decisions recorded in the task file survive context compaction and session resets. Learnings should be consolidated in `learnings.md` at the end of the task.

### Four-Phase Protocol

1. **Root Cause Investigation** — Read error messages completely. Reproduce consistently. Check recent changes. Trace data flow to source.
2. **Pattern Analysis** — Find working examples. Compare against references. Identify every difference.
3. **Hypothesis Testing** — Form single hypothesis. Test with smallest possible change. One variable at a time.
4. **Implementation** — Create failing test reproducing bug. Implement single fix. Verify fix.

### Escalation Rule

If 3+ fixes have failed: **STOP**. Question the architecture. Each fix revealing new problems in different places = wrong pattern, not wrong fix. Discuss with user before attempting more.

### Debugging Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. |
| "Emergency, no time" | Systematic is FASTER than thrashing. |
| "Just try this first" | First fix sets the pattern. Do it right. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding root cause. |

### Debugging Red Flags — STOP

- "Quick fix for now, investigate later"
- "Just try changing X and see"
- Proposing solutions before tracing data flow
- Adding multiple changes at once
- "One more fix attempt" after 2+ failures

**Full reference:** `superpowers:systematic-debugging`

---

## Verification Iron Law

```text
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this response, you cannot claim it passes.

### The Gate Function

```text
BEFORE claiming any status:
1. IDENTIFY — What command proves this claim?
2. RUN — Execute the command (fresh, complete)
3. READ — Full output, check exit code
4. VERIFY — Does output confirm the claim?
5. CLAIM — Only then state the result WITH evidence
```

### Verification Requirements

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test output: 0 failures | "Should pass", previous run |
| Coverage met | Coverage report | Extrapolation |
| Build succeeds | Build exit 0 | Linter passing |
| Bug fixed | Original symptom gone | Code changed, assumed fixed |
| Phase complete | Requirements checklist verified | Tests passing alone |

### Verification Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Done!", "Perfect!")
- About to commit/push without verification
- Trusting agent success reports without independent check

**Full reference:** `superpowers:verification-before-completion`

---

## Critical Thinking Iron Law

```text
NO PROPOSALS OR CLAIMS WITHOUT CRITICAL REASSESSMENT FIRST
```

Before accepting a claim (your own or others), proposing a solution, or making a technical decision, you **MUST** run it through the **CRITICAL REASSESSMENT** pattern.

**No exceptions:**

- Even if it "seems obvious"
- Even if it's "the only way"
- Even if you've done it before

### The CRITICAL REASSESSMENT Pattern

1. **EVALUATE ACCURACY** — Verify facts. Identify unstated assumptions. Check for logical gaps.
2. **EVALUATE COMPLETENESS** — Look for missing considerations, omitted perspectives, and failure modes.
3. **EVALUATE REASONING QUALITY** — Check if conclusions are proportional to evidence. Identify logical fallacies.
4. **INVESTIGATE IF NEEDED** — Read actual code and docs. **Never reason from memory.**
5. **DELIVER HONEST ASSESSMENT** — Provide specific flaws or explain *why* reasoning holds. Avoid hedging and meta-commentary.

### Critical Thinking Rationalizations

| Excuse | Reality |
|--------|---------|
| "I've done this 100 times" | This codebase or context might be different. Verify. |
| "Reviewer knows better" | Reviewers are human (or AI). They can be wrong. |
| "It's just a simple change" | Simple changes have side effects. |
| "Don't want to be negative" | Honesty > performance. |

### Critical Thinking Red Flags — STOP

- Hedging: "This might be right but could be wrong"
- Reflexive agreement: "You're absolutely right!"
- Proposing solutions without investigating the actual code first
- Meta-commentary: "Let me challenge this for you" (just do the analysis)
- Manufacture of 50/50 doubt (no artificial balance)

**Full reference:** `superpowers:perspectives:critical-thinking`

---

## Code Review Discipline

### Requesting Review

At phase completion or before merge:

1. Get git range (base SHA to HEAD)
2. Dispatch code review subagent with: what was implemented, spec requirements, git range
3. Act on feedback: fix Critical immediately, fix Important before proceeding, note Minor for later

### Receiving Review

- **No performative agreement** ("You're absolutely right!", "Great point!")
- **Verify** suggestions against codebase before implementing (follow **Critical Thinking Iron Law**)
- **Push back** with technical reasoning if reviewer is wrong
- **YAGNI check:** if reviewer suggests adding unused features, question the need
- **Clarify** all unclear items BEFORE implementing any

**Full reference:** `superpowers:requesting-code-review`, `superpowers:receiving-code-review`

---

## Subagent Orchestration

When executing parallel tasks or dispatching implementation work:

### Model Selection

- **Mechanical tasks** (1-2 files, clear spec) → fast model
- **Integration tasks** (multi-file, coordination) → standard model
- **Review/architecture tasks** → most capable model

### Two-Stage Review

After each task completion:

1. **Spec compliance review** — Does implementation match requirements? Nothing missing, nothing extra?
2. **Code quality review** — Is implementation well-built? Clean, tested, maintainable?

Spec compliance MUST pass before code quality review begins.

**Full reference:** `superpowers:subagent-driven-development`
