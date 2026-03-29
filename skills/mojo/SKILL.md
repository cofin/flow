---
name: mojo
description: "Auto-activate for .mojo files, .🔥 files. Mojo development patterns for high-performance computing: SIMD, zero-copy Python interop, GIL-free parallelism, C FFI, and Hatch build integration. Use when: writing Mojo code, .mojo files, SIMD kernels, Python-Mojo hybrid projects, hatch-mojo build hooks, or packaging Mojo extensions into wheels."
---

# Mojo (High-Performance Computing)

## Overview

Mojo is a high-performance language designed for numeric, AI, and data-intensive workloads, offering Python-like syntax with C-level performance.

---

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

---

## Core Rules

- **Prefer `fn` over `def`**: Strict type checking and performance.
- **Memory Safety**: Leverage ownership (`owned`, `borrowed`, `inout`).
- **Explicit Types**: Required for predictable performance.

---

## Official References

- <https://docs.modular.com/mojo/>
- <https://docs.modular.com/llms-mojo.txt>
- <https://docs.modular.com/mojo/manual/python/>
