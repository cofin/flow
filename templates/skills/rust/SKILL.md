---
name: rust
description: "Rust development for Vertebra core: shared memory, lock-free channels, IPC transport backends, bindings (PyO3/napi-rs), and performance-critical code. Use when editing Rust in src/rs or designing cross-platform IPC primitives."
---

# Rust (Vertebra)

## Scope
- Work in `src/rs/vertebra-core`, `src/rs/vertebra-py`, `src/rs/vertebra-js`, `src/rs/vertebra-broker`.
- Keep IPC primitives OS-abstracted (Linux/macOS/Windows backends).

## Core Rules
- Prefer `rustix` for POSIX APIs; isolate OS-specific code in `platform/` modules.
- Document every `unsafe` block with a `# Safety` section.
- Specify atomic `Ordering` explicitly; do not default to `SeqCst`.
- Use RAII for OS handles (fd, mapping, socket, pipe).
- Return slices/views for zero-copy when safe; avoid hidden copies.

## IPC + Performance
- Align shared memory headers and buffers to cache lines (64B).
- Keep ring buffers bounded and power-of-two where possible.
- Measure baseline latency before tuning; record results in PRDs.

## FFI Surface
- Expose APIs via PyO3 + napi-rs first.
- Add optional C ABI only if required for compatibility or stable ABI distribution.
- Map errors deterministically; never panic across FFI.

## Testing
- Use `cargo test` for unit/integration; `proptest` for invariants.
- Run Miri on unsafe code paths.
- Use valgrind/asan for binding layers.
