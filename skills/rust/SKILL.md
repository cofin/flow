---
name: rust
description: "Rust development patterns for high-performance systems: workspace architecture, async runtimes (tokio), platform abstraction, PyO3/maturin Python bindings, napi-rs Node/Bun bindings, C ABI/FFI, zero-copy IPC, error handling (thiserror), and testing with criterion. Use when: writing Rust code, designing cross-platform systems, building Python extensions with PyO3/maturin, building Node/Bun extensions with napi-rs, exposing C ABI, or optimizing performance-critical paths."
---

# Rust (Systems & Performance)

## Overview

Patterns for multi-crate Rust workspaces targeting cross-platform, high-performance systems with polyglot extension surfaces. Covers workspace layout, async runtimes, platform abstraction, PyO3/maturin Python bindings, napi-rs Node/Bun bindings, C ABI/FFI, error handling, and benchmarking.

## Code Style

- Edition 2021, resolver 2.
- Workspace-level lint config in root `Cargo.toml`:

```toml
[workspace.lints.rust]
unexpected_cfgs = { level = "allow", check-cfg = ['cfg(Py_GIL_DISABLED)'] }

[workspace.lints.clippy]
too_many_arguments = "allow"
type_complexity = "allow"
```

- Crates inherit lints: `[lints] workspace = true`.
- Format: `cargo fmt`. Lint: `cargo clippy -- -D warnings`.
- Use `tracing` (not `log`) for structured instrumentation.
- Document public APIs with `///` doc comments.
- Prefer `Arc<T>` over `Rc<T>` in async contexts.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Workspace Architecture](references/workspace.md)**
  Centralized dependency management, release profiles, feature flags, module hierarchy.
- **[Async & Concurrency](references/async.md)**
  Tokio runtime patterns, GIL-free async with pyo3_async_runtimes, crossbeam channels, parking_lot.
- **[PyO3 & Maturin Bindings](references/pyo3.md)**
  Module registration, frozen classes, signature macros, zero-copy batch access, free-threaded Python, build.rs, maturin config.
- **[Error Handling](references/errors.md)**
  thiserror 2.0 derive, PyErr conversion, platform-specific error types, From impls.
- **[Platform Abstraction](references/platform.md)**
  Conditional modules per OS, target-specific dependencies, futex/ulock/WaitOnAddress, libc/rustix/windows-sys.
- **[napi-rs Node/Bun Bindings](references/napi.md)**
  Module setup, #[napi] macros, async tasks, ThreadsafeFunction (TSFN), buffer handling, error mapping, deno_core embedding, Bun compatibility, cross-platform npm distribution.
- **[C ABI & FFI](references/c_abi.md)**
  Stable C ABI distribution, raw pointer + length patterns, cbindgen header generation, cross-language error mapping, zero-copy strategies for C consumers.
- **[Testing & Benchmarking](references/testing.md)**
  Integration tests, criterion 0.5 benchmarks, CI matrix, maturin develop workflow.

---

## Official References

- <https://doc.rust-lang.org/book/>
- <https://blog.rust-lang.org/releases/>
- <https://tokio.rs/>
- <https://pyo3.rs/>
- <https://maturin.rs/>
- <https://napi.rs/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
