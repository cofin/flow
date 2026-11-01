---
name: debloat
description: "Use when reviewing or simplifying code, tests, prose, or repository gates while preserving public behavior, typing, performance, and project conventions."
---

# Debloat

Reduce the semantic surface a maintainer or agent must understand without changing what users can observe. Deletion is a behavior-preserving refactor, not proof that the deleted material was unnecessary.

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

### 3. Simplify & deepen modules

- **Apply the Deletion Test & Deep-Module Seam Rule**:
  - Ask of every pass-through helper, 1:1 interface wrapper, or internal seam: *"If I delete this boundary and inline the call, does any caller or test lose leverage?"*
  - Enforce **"One adapter = hypothetical seam; two adapters = real seam"**—do not introduce an abstract interface or port for a single in-process implementation.
  - Consolidate standalone private `_...` module helpers used only by a single domain class onto that class as private methods below its public methods.
- **Preserve explicit code**: Keep straightforward duplication when consolidation would create condition-heavy or overly generic abstractions.
- **Remove backward-compatibility shims & chronological sediment**: Delete unused aliases, re-export shims, one-time migration flags, historical revision notes, phase labels, stale TODOs, and comments that merely restate code.
- **Preserve non-obvious rationale**: Keep docstrings explaining external quirks, security properties, invariants, and rejected alternatives. Treat repository-defined instruction comments such as `ai:` as user instructions.
- **Prefer behavior-oriented tests and native gates**: Prefer public-seam vertical-slice tests and native lint, type, parser, or build rules over implementation snapshots and ad hoc source scanners. Keep structural tests when structure is operationally meaningful (memory layout, hashing, compilation, reflection, serialization, signatures, and supported exports).

### 4. Prove replacement gates

When adding or relying on a replacement gate, inject a representative violation into a temporary tree, isolated fixture, or gate self-test. Require a non-zero result and the expected diagnostic. Restore the violation and require the gate to pass. Never leave deliberate violations in the working tree or overwrite user files.

Confirm that canonical aggregate commands inspect new and untracked files. Record any discovery gap instead of treating a vacuous green result as proof.

### 5. Compare and finish

Review the final diff for semantic drift and newly introduced cleverness. Run focused behavior checks, affected lint/type/build checks, coverage comparison when deleting behavioral coverage, and `git diff --check`. Report the invariants preserved, exact checks, and any limitation.

## Anti-slop prose, agent doc, and comment policy

Strip synthetic AI filler and context bloat from docs, specs, worksheets, `.agents/` files, commit messages, and code:

- **No AI puffery**: Remove significance inflation (`pivotal`, `crucial`, `testament to`, `delve`, `tapestry`, `seamless`, `robust`, `comprehensive`, `leverage`, `unlock`, `foster`, `underscore`, `showcase`).
- **No negative parallelisms or throat-clearing**: Replace `"It is not just X — it is Y"`, `"Not only... but also..."`, `"Moreover"`, `"Furthermore"`, and trailing participle clauses (`"...ensuring seamless integration"`) with direct active-voice statements.
- **No count-prefixed buzzwords or artificial rule codes**: Never use fragile numbered labels (`3-Layer Sizing`, `7-Point Factor`, `4-Stage Pipeline`) or invented codes in prose, headings, or filenames.
- **Prune `.agents/` cache vs. environment & chronological sediment**: Never duplicate file trees, command matrices, or schema dumps in `.agents/` docs when a context pointer (`path/to/file::Symbol`) points to the live source of truth; rewrite living docs in present tense without revision logs.
- **Comment and typing discipline**: In Python, never use inline `#` comments; move necessary rationale into module, class, or function docstrings and enforce PEP 585/604 built-in types (`list[str]`, `dict[str, Any]`, `X | None`).

## Low-signal test policy

Reject and refactor the 3 test anti-patterns:

- **Implementation-Coupled Tests**: Tests that assert call counts/order on internal collaborators or break during behavior-preserving refactors.
- **Tautological (Mock-Echo) Tests**: Tests that mock the System Under Test or internal collaborator and assert that the mock returned what it was configured to return.
- **Standalone Audit/Remediation Test Files**: Never leave `test_*remediation*.py`, `test_*audit*.py`, or `test_task_*.py` files in the tree; merge valid behavior assertions into the canonical module test file.

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
