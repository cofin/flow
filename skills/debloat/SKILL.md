---
name: debloat
description: "Use when reviewing or simplifying code, tests, prose, or repository gates while preserving public behavior, typing, performance, and project conventions."
---

# Debloat

Reduce the semantic surface a maintainer must understand without changing what users can observe. Deletion is a behavior-preserving refactor, not proof that the deleted material was unnecessary.

## Operating mode

- For a review, inspect and report evidence-backed findings only. Do not edit.
- For a change request, implement the smallest coherent cleanup and verify it.
- Read repository instructions, task state, and relevant architecture guidance first.
- Inspect the worktree before editing and preserve user and other-agent changes.
- Keep public API removals, compatibility breaks, dependency changes, and broad redesigns out of scope unless explicitly authorized.

## Workflow

### 1. Establish scope and invariants

Identify the contracts that must remain stable:

- runtime behavior and error semantics;
- public imports, signatures, serialization shapes, and configuration;
- supported versions and optional-dependency boundaries;
- performance-sensitive paths;
- test coverage and repository quality gates.

Use call-site tracing to classify each candidate as public, private-live, private-dead, generated, or test-only. Check direct calls, re-exports, registration, reflection, configuration strings, generated references, docs, and tests before declaring code dead.

### 2. Capture a proportional baseline

Run focused verification before editing. Observable behavior and bug fixes use the task's TDD strategy. Behavior-preserving deletion, consolidation, or reordering uses a green-before/green-after characterization baseline. Read [test and gate debloat](references/test-and-gate-debloat.md) before deleting tests or replacing a gate.

### 3. Simplify

- Remove wrappers only when they add no contract, dispatch, instrumentation, or type boundary.
- Preserve explicit code when consolidation would create condition-heavy or overly generic abstractions.
- Remove historical narration, phase labels, stale TODOs, and comments that merely restate code.
- Preserve rationale for non-obvious constraints, external quirks, security properties, and rejected alternatives.
- Treat repository-defined instruction comments such as `ai:` as user instructions.
- Prefer behavior-oriented tests and native lint, type, parser, or build rules over implementation snapshots and ad hoc source scanners.
- Keep structural tests when structure is operationally meaningful, including memory layout, hashing, compilation, reflection, serialization, signatures, and supported exports.

### 4. Prove replacement gates

When adding or relying on a replacement gate, inject a representative violation into a temporary tree, isolated fixture, or gate self-test. Require a non-zero result and the expected diagnostic. Restore the violation and require the gate to pass. Never leave deliberate violations in the working tree or overwrite user files.

Confirm that canonical aggregate commands inspect new and untracked files. Record any discovery gap instead of treating a vacuous green result as proof.

### 5. Compare and finish

Review the final diff for semantic drift and newly introduced cleverness. Run focused behavior checks, affected lint/type/build checks, coverage comparison when deleting behavioral coverage, and `git diff --check`. Report the invariants preserved, exact checks, and any limitation.

## Low-signal test policy

Reject tests that lock incidental prompt phrases, private implementation shape, duplicate snapshots, or file existence without an operational contract. Reject source scanners when a native parser, lint, type, or build contract expresses the rule. Retain tests for observable behavior, public contracts, error paths, interoperability, regressions, and operationally meaningful structure.

## Guardrails

- Do not optimize for deleted line count.
- Do not remove supported behavior or weaken a safety property.
- Do not call code dead after one textual search.
- Do not replace readable duplication with a generic framework.
- Do not trust a replacement gate until an isolated violation proves it fails correctly.
- Stop and request plan revision when cleanup requires a public break, architecture change, unsupported scope expansion, or inseparable unrelated edits.

## Validation

Relevant verification must remain equal or stronger after cleanup. Preserve observable behavior, public APIs, typing, performance, import boundaries, and repository-native quality gates.

## Example

When replacing a pytest source scanner with a configured linter rule, first prove the linter rejects the same representative violation in an isolated fixture. Only then remove the superseded scanner and run the focused plus aggregate gates.
