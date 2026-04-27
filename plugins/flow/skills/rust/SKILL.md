---
name: rust
description: "Use when editing Rust files, .rs, Cargo.toml, Cargo.lock, workspaces, async code, error handling, PyO3, maturin, napi-rs, C ABI, platform support, tests, or performance-critical Rust paths."
---

# Rust (Systems & Performance)

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

## Quick Reference

### Workspace Setup

```text
project/
├── Cargo.toml              # [workspace] root
├── crates/
│   ├── core/               # Pure logic, no FFI deps
│   ├── http/               # Runtime + networking (binary)
│   ├── py/                 # PyO3 bindings (cdylib)
│   └── node/               # napi-rs bindings
└── rust-toolchain.toml
```

Core crate has zero FFI dependencies. Binding crates wrap it. Pin shared dependencies in workspace root with `[workspace.dependencies]`; crates reference with `{ workspace = true }`.

### Error Handling Pattern (thiserror)

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error in {path}: {message}")]
    Parse { path: String, message: String },
    #[error("not found: {0}")]
    NotFound(String),
}

pub type Result<T> = std::result::Result<T, AppError>;
```

### Async Tokio Essentials

- Use `#[tokio::main]` for binaries; pass runtime handle to libraries.
- Select tokio features per crate -- only the server crate needs `"full"`.
- Use `Arc<T>` for shared state across tasks, never `Rc<T>`.
- Use `tokio::sync::Mutex` only when holding the lock across `.await`; otherwise use `parking_lot::Mutex`.

### PyO3 Pattern

```rust
use pyo3::prelude::*;

#[pyclass(frozen)]  // frozen = immutable, safe across threads
#[derive(Clone, Debug)]
pub struct Config {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub max_retries: u32,
}

#[pymodule]
#[pyo3(name = "_native")]
pub fn pymodule_init(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Config>()?;
    Ok(())
}
```

<workflow>

## Workflow

### Step 1: Workspace Layout

Create a workspace with `resolver = "2"`. Separate pure-logic core from binding crates (py, node, c_abi). Pin all shared dependencies in `[workspace.dependencies]`.

### Step 2: Error Types

Define per-crate error enums with `thiserror`. Use `#[from]` for automatic conversion. Add `PyErr` conversion (`From<AppError> for PyErr`) in binding crates.

### Step 3: Core Logic

Write business logic in the core crate with no FFI dependencies. Use `async` for I/O-bound work. Test with `cargo test` and benchmark hot paths with `criterion`.

### Step 4: Bindings

Wrap core types/functions in binding crates. For PyO3: use `#[pyclass(frozen)]` for immutable data, `future_into_py` for async. For napi-rs: use `#[napi]` macros.

### Step 5: Validate

Run `cargo clippy -- -D warnings`, `cargo fmt --check`, and `cargo test --workspace`. For PyO3: `maturin develop` and run Python tests.

</workflow>

<guardrails>

## Guardrails

- **Prefer `Arc` over `Rc` in async code** -- `Rc` is not `Send` and will fail to compile in tokio tasks. Use `Arc<T>` for shared ownership across tasks.
- **Use `thiserror` for library error types** -- provides `#[derive(Error)]` with `Display` and `From` impls. Reserve `anyhow` for binaries/scripts only.
- **Workspace for multi-crate projects** -- centralize dependency versions, lint config, and release profiles. Never duplicate version pins across crates.
- **Core crate has zero FFI deps** -- keep PyO3, napi-rs, and libc out of core. Binding crates depend on core and add FFI.
- **`#[pyclass(frozen)]` for immutable data** -- enables safe sharing across Python threads without per-access locking.
- **`tracing` over `log`** -- structured instrumentation with spans, levels, and subscriber flexibility.
- **Pin `rust-toolchain.toml`** -- ensures consistent compiler version across CI and local builds.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering Rust code, verify:

- [ ] Workspace uses `resolver = "2"` and `[workspace.dependencies]`
- [ ] Error types use `thiserror` with `#[from]` conversions
- [ ] Async code uses `Arc<T>` (not `Rc<T>`) for shared state
- [ ] Core crate has no FFI dependencies (PyO3, napi-rs, libc)
- [ ] `cargo clippy -- -D warnings` passes
- [ ] Public APIs have `///` doc comments
- [ ] `rust-toolchain.toml` is present and pinned

</validation>

<example>

## Example

**Task:** Error type and async function with proper error handling.

```rust
// crates/core/src/error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("object not found: {key}")]
    NotFound { key: String },
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serde(#[from] serde_json::Error),
    #[error("connection timeout after {elapsed_ms}ms")]
    Timeout { elapsed_ms: u64 },
}

pub type Result<T> = std::result::Result<T, StorageError>;
```

```rust
// crates/core/src/store.rs
use std::sync::Arc;
use tokio::fs;
use crate::error::{Result, StorageError};

pub struct ObjectStore {
    base_path: Arc<str>,
}

impl ObjectStore {
    pub fn new(base_path: impl Into<Arc<str>>) -> Self {
        Self { base_path: base_path.into() }
    }

    /// Read an object by key, returning its bytes.
    pub async fn get(&self, key: &str) -> Result<Vec<u8>> {
        let path = format!("{}/{}", self.base_path, key);
        fs::read(&path).await.map_err(|e| match e.kind() {
            std::io::ErrorKind::NotFound => StorageError::NotFound {
                key: key.to_string(),
            },
            _ => StorageError::Io(e),
        })
    }

    /// Write bytes to an object key.
    pub async fn put(&self, key: &str, data: &[u8]) -> Result<()> {
        let path = format!("{}/{}", self.base_path, key);
        if let Some(parent) = std::path::Path::new(&path).parent() {
            fs::create_dir_all(parent).await?;
        }
        fs::write(&path, data).await?;
        Ok(())
    }
}
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Workspace Architecture](references/workspace.md)** -- Centralized deps, release profiles, feature flags, module hierarchy.
- **[Async & Concurrency](references/async.md)** -- Tokio patterns, GIL-free async with pyo3_async_runtimes, crossbeam, parking_lot.
- **[PyO3 & Maturin Bindings](references/pyo3.md)** -- Module registration, frozen classes, signature macros, zero-copy, maturin config.
- **[Error Handling](references/errors.md)** -- thiserror 2.0 derive, PyErr conversion, platform-specific errors, From impls.
- **[Platform Abstraction](references/platform.md)** -- Conditional modules per OS, target-specific deps, futex/ulock/WaitOnAddress.
- **[napi-rs Node/Bun Bindings](references/napi.md)** -- Module setup, #[napi] macros, async tasks, TSFN, cross-platform npm distribution.
- **[C ABI & FFI](references/c_abi.md)** -- Stable C ABI, raw pointer patterns, cbindgen, zero-copy for C consumers.
- **[Testing & Benchmarking](references/testing.md)** -- Integration tests, criterion 0.5 benchmarks, CI matrix, maturin develop.

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
