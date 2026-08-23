---
name: debloat
description: "Use when reviewing or simplifying existing code, removing dead abstractions, eliminating low-signal tests, or replacing custom scanners with native quality gates."
---

# Code & Test Debloat

Prune redundant abstractions, dead code branches, over-engineered wrappers, and low-signal tests while strictly preserving observable behavior, typing, and safety invariants.

## Workflow

1. **Scan for Bloat Patterns**: Inspect code for dead abstractions, low-signal tests, speculative generality, or bespoke scanners.
2. **Prove Invariant Preservation**: Confirm public exports, type annotations, and integration tests remain protected.
3. **Execute Targeted Pruning**: Remove redundant code and rerun test gates to prove green status.

## Guardrails

- Never delete tests that protect business logic, error boundaries, regression fixes, or security checks.
- Do not optimize for raw line-count reduction at the expense of readability or explicit type contracts.

## Output

Return the debloat report listing pruned items, rationale, preserved invariants, and verification commands.

## Validation

Confirm that test suites and linters pass cleanly (exit code 0) after pruning.

## Example

Replace a 50-line custom file crawler script with a single standard glob pattern in the linter configuration.
