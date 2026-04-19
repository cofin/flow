---
name: mojo
description: "Auto-activate for .mojo files, .🔥 files. Mojo development patterns for high-performance computing: SIMD, zero-copy Python interop, GIL-free parallelism, C FFI, and Hatch build integration. Use when: writing Mojo code, .mojo files, SIMD kernels, Python-Mojo hybrid projects, hatch-mojo build hooks, or packaging Mojo extensions into wheels. Produces high-performance Mojo code with SIMD kernels, Python interop, and Hatch build integration. Not for pure Python performance work or C extensions (see python/cpp)."
---

# Mojo (High-Performance Computing)

## Overview

Mojo is a high-performance language designed for numeric, AI, and data-intensive workloads, offering Python-like syntax with C-level performance.

---

<workflow>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Performance Optimization](references/performance.md)**
  - SIMD-First vectorization and GIL-free parallelism.
- **[Python Interop](references/interop.md)**
  - Zero-copy data exchange (NumPy) and C-API extensions.
- **[C FFI](references/ffi.md)**
  - Static `external_call`, dynamic `DLHandle`, and struct mapping.
- **[Build System](references/build.md)**
  - `hatch-mojo` configuration and manual compilation.
- **[Hatch-Mojo Build Hook](references/hatch_mojo.md)** — Hatch build hook for compiling .mojo sources, pyproject.toml config, cibuildwheel, and CI/CD.
- **[Testing](references/testing.md)**
  - Mojo unit tests and boundary integration tests.

## Core Rules

- **Prefer `fn` over `def`**: Strict type checking and performance.
- **Memory Safety**: Leverage ownership (`owned`, `borrowed`, `inout`).
- **Explicit Types**: Required for predictable performance.

## Official Modular Skills (Highly Recommended)

For comprehensive support for modern Mojo syntax, project initialization, and GPU programming, we highly recommend installing the official Modular agent skills:

- **mojo-syntax**: Overcomes agent misconceptions and ensures correct modern syntax.
- **new-modular-project**: Wizard for initializing Mojo/MAX projects with Pixi and UV.
- **mojo-python-interop**: Expert guidance for zero-copy Python interaction.
- **mojo-gpu-fundamentals**: Patterns for high-performance accelerator programming.

**Installation:**

```bash
npx skills add modular/skills
```

</workflow>

---

## Official References

- <https://docs.modular.com/mojo/>
- <https://docs.modular.com/llms-mojo.txt>
- <https://docs.modular.com/mojo/manual/python/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Mojo](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/mojo.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

- **Always prefer `fn` over `def`** -- `fn` enforces strict typing and is required for optimal performance and safety.
- **Explicitly define memory ownership** -- Use `owned`, `borrowed`, and `inout` to manage data flow and avoid unnecessary copies.
- **Use `SIMD` for performance-critical logic** -- Mojo excels at vectorization; always consider SIMD when processing large arrays.
- **Use `alias` for compile-time constants** -- These are evaluated at compile time, leading to zero runtime overhead.
- **Verify data alignment** -- Ensure pointers are aligned for the target architecture, especially when using SIMD operations.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] `fn` is used for all performance-critical functions
- [ ] Explicit ownership markers are correctly applied to arguments
- [ ] SIMD vectorization is implemented where applicable
- [ ] `alias` is used for all constants and compile-time values
- [ ] No `def` usage is present in performance-sensitive code
- [ ] Memory safety is verified through ownership and borrowing checks
</validation>

<example>
## Example: SIMD Vector Addition

```mojo
from algorithm import vectorize
from memory import UnsafePointer

fn vector_add[type: DType, size: Int](a: UnsafePointer[Scalar[type]], b: UnsafePointer[Scalar[type]], result: UnsafePointer[Scalar[type]], n: Int):
    """Adds two vectors using SIMD acceleration."""
    alias nelts = simdwidthof[type]()

    @parameter
    fn add_simd[width: Int](i: Int):
        let va = a.load[width=width](i)
        let vb = b.load[width=width](i)
        result.store[width=width](i, va + vb)

    vectorize[add_simd, nelts](n)
```

</example>
