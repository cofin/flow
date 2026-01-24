---
name: pyo3
description: "PyO3 bindings for Vertebra: module setup, async bridging, buffer protocol, GIL handling, and error mapping. Use when exposing Rust IPC to Python."
---

# PyO3 (Vertebra)

## Core Rules
- Export module as `_vertebra` and add `__version__`.
- Map Rust errors to Python exceptions deterministically.
- Release the GIL for CPU-bound work (`allow_threads`).
- Prefer `PyBuffer`/memoryview for zero-copy where safe.
- Avoid returning references to Rust-owned buffers without lifetime guarantees.

## Async
- Use `pyo3-async-runtimes` when bridging async Rust to Python.

## ABI
- Consider `abi3` only when stability across Python versions is required.
- Add optional C ABI only if PyO3 cannot satisfy compatibility needs.
