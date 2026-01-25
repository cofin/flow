---
name: rust-bindings
description: Patterns for creating high-performance Rust extensions for Python (PyO3) and Node/Bun (NAPI).
---

# Rust Bindings Skill

## Overview

This skill covers bridging Rust with high-level languages to achieve native performance for critical paths.

## Core Patterns

### 1. Structure

For polyglot libraries, use a workspace structure:

- `core`: Pure Rust business logic, no FFI dependencies.
- `bindings-py`: Python bindings using `pyo3`.
- `bindings-js`: Node/Bun bindings using `napi-rs`.
- `bindings-c`: (Optional) C ABI if needed.

### 2. Python Bindings (PyO3)

Use `pyo3` and `maturin`.

**Cargo.toml**:

```toml
[lib]
name = "my_module"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.27", features = ["extension-module"] }
```

**Implementation**:

```rust
use pyo3::prelude::*;

#[pyclass]
struct MyClass { inner: InnerType }

#[pymethods]
impl MyClass {
    #[new]
    fn new() -> Self { ... }
    
    fn compute(&self, py: Python<'_>) -> PyResult<usize> {
        // Release GIL for CPU work
        py.allow_threads(|| self.inner.compute())
    }
}
```

### 3. Node/Bun Bindings (NAPI-RS)

Use `napi` and `napi-derive`.

**Cargo.toml**:

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "2.14", features = ["tokio_rt"] }
napi-derive = "2.14"
```

**Implementation**:

```rust
use napi_derive::napi;

#[napi]
struct MyClass { inner: InnerType }

#[napi]
impl MyClass {
    #[napi(constructor)]
    pub fn new() -> Self { ... }
    
    #[napi]
    pub async fn compute(&self) -> Result<u32> {
        // Async is handled automatically off-thread
        Ok(self.inner.compute().await)
    }
}
```

## Best Practices

- **Pure Core**: Keep the logic in the core crate. Bindings should only handle type conversion.
- **Zero-Copy**: Use `Arrow` or shared memory for large data transfer. Avoid copying large strings/buffers across the boundary.
- **Error Mapping**: Convert Rust results to language-specific exceptions (e.g., `PyValueError`, `Error` object).
- **Testing**: Test the core logic in Rust. Test bindings in the target language (pytest, vitest/bun test).
