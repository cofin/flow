# C++ Design Best Practices

## Overview

Use this reference to keep C++ code practical and safe: explicit ownership, strong API boundaries, predictable error handling, and measurable performance.

## Core rules

1. Prefer RAII for all resource lifetimes.
2. Make ownership obvious at type boundaries (`unique_ptr`, references, value types).
3. Keep interfaces small and stable.
4. Use `const` and immutability by default.
5. Avoid hidden global state.

## Design guidance

1. Separate pure logic from I/O and side effects.
2. Make invalid states unrepresentable with types where possible.
3. Favor composition over deep inheritance.
4. Keep headers minimal to reduce coupling and rebuild cost.
5. Hide platform-specific code behind narrow adapters.

## Error and API conventions

1. Prefer explicit status/exception policy per module (do not mix ad hoc).
2. Do not throw across C ABI boundaries.
3. Validate inputs early and return actionable diagnostics.
4. Keep error messages stable enough for CI/debugging.

## Performance hygiene

1. Measure first; optimize real hotspots.
2. Avoid accidental allocations in hot loops.
3. Keep data layouts cache-friendly.
4. Re-check branchy code with representative workloads before and after changes.

## Concurrency hygiene

1. Prefer message passing or clear lock ownership over ad hoc shared mutable state.
2. Keep critical sections short.
3. Document thread-safety guarantees for each public type.
4. Use sanitizers and thread tooling in CI where feasible.

## Code review checklist

1. Are ownership and lifetimes explicit?
2. Are ABI/error boundaries safe?
3. Are tests focused on behavior and regressions?
4. Are performance claims backed by data?
5. Is the design simple enough for future contributors?
