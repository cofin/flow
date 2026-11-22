---
name: debloat
description: "Use when reviewing or simplifying code, tests, prose, or repository checks through behavior-preserving cuts while keeping typing, performance, and conventions intact. Don't use for adding new features, planning specs (use flow-planning), or running full workflow closeouts (use flow-completion)."
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
- test coverage and repository quality checks.

Classify each candidate as public, private-live, private-dead, generated, or test-only via repo-wide call-site tracing before recommending cuts.

### 2. Capture a proportional baseline

Run focused verification before editing. Observable behavior and bug fixes use the task's TDD strategy. Behavior-preserving deletion, consolidation, or reordering uses a green-before/green-after characterization baseline. Read [test and check debloat](references/test-and-check-debloat.md) before deleting tests or replacing a check.

### 3. Simplify & deepen modules

- **Apply the Deletion Test & Deep-Module Rule**:
  - Ask of every pass-through helper, 1:1 interface wrapper, or internal boundary: *"If I delete this boundary and inline the call, does any caller or test lose value?"*
  - Enforce **"One adapter = hypothetical boundary; two adapters = real boundary"**—do not introduce an abstract interface or port for a single in-process implementation.
  - Consolidate standalone private `_...` module helpers used only by a single domain class onto that class as private methods below its public methods.
- **Preserve explicit code**: Keep straightforward duplication when consolidation would create condition-heavy or overly generic abstractions.
- **Remove backward-compatibility shims & stale history**: Delete unused aliases, re-export shims, one-time migration flags, historical revision notes, phase labels, stale TODOs, and comments that merely restate code.
- **Preserve non-obvious rationale**: Keep docstrings explaining external quirks, security properties, invariants, and rejected alternatives. Treat repository-defined instruction comments such as `ai:` as user instructions.
- **Prefer behavior-oriented tests and native checks**: Prefer public-interface tests and native lint, type, parser, or build rules over implementation snapshots and ad hoc source scanners. Keep structural tests when structure is operationally meaningful (memory layout, hashing, compilation, reflection, serialization, signatures, and supported exports).
- **Prove absence before recommending deletion**: Run an untruncated repo-wide `git grep -n -F '<symbol>'` across tracked files before marking code dead. Also check `__all__` exports, CLI flags, wire schemas, config files, templates, SQL views, fixtures, reflection, and dynamic dispatch.
- **Separate safe cuts from scope changes**: Follow [`../../templates/agent/simplify-card.md`](../../templates/agent/simplify-card.md). Report cuts read-only during review passes without modifying files. In change-request mode, apply `equivalent` cuts after lint and tests pass, and confirm `behavior_change` cuts with the owner first.
- **No lateral motion**: Skip changes that relocate lines without reducing indirection, branching, or net concepts.

### 4. Prove replacement checks

When adding or relying on a replacement check, inject a representative violation into a temporary tree, isolated fixture, or check self-test. Require a non-zero result and the expected diagnostic. Restore the violation and require the check to pass. Never leave deliberate violations in the working tree or overwrite user files.

Confirm that canonical aggregate commands inspect new and untracked files. Record any discovery gap instead of treating a vacuous green result as proof.

### 5. Compare and finish

Review the final diff for semantic drift and newly introduced cleverness. Run focused behavior checks, affected lint/type/build checks, coverage comparison when deleting behavioral coverage, and `git diff --check`. Report the invariants preserved, exact checks, and any limitation.

## Anti-slop prose and comment policy

Strip synthetic AI filler and context bloat from docs, specs, worksheets, `.agents/` files, commit messages, and code:

- **No AI puffery**: Remove significance inflation (`pivotal`, `crucial`, `testament to`, `delve`, `tapestry`, `seamless`, `robust`, `comprehensive`, `leverage`, `unlock`, `foster`, `underscore`, `showcase`).
- **No negative parallelisms or throat-clearing**: Replace `"It is not just X -- it is Y"`, `"Not only... but also..."`, `"Moreover"`, `"Furthermore"`, and trailing participle clauses (`"...ensuring seamless integration"`) with direct active-voice statements.
- **No numbered buzzwords or artificial rule codes**: Never use fragile numbered labels or invented rule codes in prose, headings, or filenames.
- **Prune stale cache and history**: Never duplicate file trees, command matrices, or schema dumps in `.agents/` docs when a context pointer (`path/to/file::Symbol`) points to the live source. Rewrite living docs in present tense without revision logs.
- **Comment and typing discipline**: In Python, never use inline `#` comments; move necessary rationale into module, class, or function docstrings and enforce PEP 585/604 built-in types (`list[str]`, `dict[str, Any]`, `X | None`).

## Low-signal test policy

Reject and refactor test anti-patterns:

- **Private-Detail Tests**: Tests that assert call counts/order on internal collaborators or break during behavior-preserving refactors.
- **Mock-Only Tests**: Tests that mock the module under test or internal collaborator and assert that the mock returned what it was configured to return.
- **Standalone Audit/Remediation Test Files**: Never leave `test_*remediation*.py`, `test_*audit*.py`, or `test_task_*.py` files in the tree; merge valid behavior assertions into the canonical module test file.

## Guardrails

- Do not optimize for deleted line count; keep readable code that protects clarity and invariants.
- Do not remove supported behavior or weaken a safety property to shrink a diff.
- Do not call code dead after one textual search because exports, configs, and reflection hide callers.
- Do not replace straightforward duplication with a generic framework that raises cognitive load.
- Do not trust a replacement check until an isolated violation proves it catches the failure.
- Stop and request plan revision when cleanup requires a public break, architecture change, or unrelated edits.

## Validation

Relevant verification must remain equal or stronger after cleanup. Preserve observable behavior, public APIs, typing, performance, import boundaries, and repository-native quality checks.

## Example

Verify call sites across the whole repository before proposing a deletion or replacing a scanner with a linter rule:

```bash
git grep -n -F "LegacyHelper"
flow review plan --range main..HEAD --mode simplify --json
```

When replacing a pytest source scanner with a configured linter rule, first prove the linter rejects the same representative violation in an isolated fixture. Only then remove the superseded scanner and run the focused plus aggregate checks.
