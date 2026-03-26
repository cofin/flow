# Error Handling

## thiserror 2.0 Derive Pattern

Use `thiserror` for library errors. Define domain-specific error enums per crate:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SyncError {
    #[error("platform wait is not implemented")]
    Unsupported,
    #[error("system call failed: {0}")]
    Syscall(std::io::Error),
}
```

```rust
#[derive(Debug, Error)]
pub enum ShmError {
    #[error("invalid shared memory size")]
    InvalidSize,
    #[error("invalid shared memory name")]
    InvalidName,
    #[error("system call failed: {0}")]
    Sys(#[from] std::io::Error),
    #[error("invalid shared memory name: {0}")]
    Name(#[from] std::ffi::NulError),
    #[error("shared memory mapping failed")]
    MapFailed,
}
```

For tool/application crates with structured variants:

```rust
#[derive(Debug, Error)]
pub enum BundlerError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Parse error in {path}: {message}")]
    Parse { path: String, message: String },
    #[error("Transform error: {0}")]
    Transform(String),
    #[error("Pool exhausted - all workers busy")]
    PoolExhausted,
}

pub type Result<T> = std::result::Result<T, BundlerError>;
```

## PyErr Conversion

Convert Rust errors to Python exceptions. Two patterns:

### From impl (for crate-level errors)

```rust
use pyo3::exceptions::PyRuntimeError;
use pyo3::PyErr;

impl From<BundlerError> for PyErr {
    fn from(err: BundlerError) -> PyErr {
        PyRuntimeError::new_err(err.to_string())
    }
}
```

### to_py_err helper (for ad-hoc conversions)

```rust
fn to_py_err(e: impl std::fmt::Display) -> PyErr {
    PyRuntimeError::new_err(format!("Operation error: {e}"))
}

// Usage in async contexts:
pyo3_async_runtimes::tokio::future_into_py(py, async move {
    let result = inner.get(&path).await.map_err(to_py_err)?;
    Ok(result.bytes().await.map_err(to_py_err)?.to_vec())
})
```

## From Impls for Library Error Wrapping

Use `#[from]` for automatic conversion from upstream errors:

```rust
#[derive(Debug, Error)]
pub enum CoreError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serde(#[from] serde_json::Error),
    #[error("sync error: {0}")]
    Sync(#[from] SyncError),
    #[error("shared memory error: {0}")]
    Shm(#[from] ShmError),
}
```

## Rules

- Use `thiserror` for library errors; `anyhow`/`eyre` only in binaries.
- Never panic across FFI boundaries. Catch and convert to PyErr.
- Define domain-specific error enums per crate, not one global enum.
- Use `#[from]` for automatic upstream error wrapping.
- Provide `type Result<T> = std::result::Result<T, MyError>` aliases.
