# Async & Concurrency

## Tokio as Standard Runtime

Select tokio features per crate based on actual needs. Only the server/http crate needs `"full"`:

```toml
# Core crate — minimal tokio
tokio = { workspace = true }

# HTTP crate — explicit feature selection
tokio = { version = "1.49.0", features = ["rt-multi-thread", "macros", "net", "sync", "fs", "time", "io-util", "signal"] }
```

Use `#[tokio::main]` for binaries; pass runtime handle to libraries.

## GIL-Free Async: future_into_py

For async Python functions that return awaitables, use `pyo3_async_runtimes::tokio::future_into_py`. This bridges a Rust future into a Python coroutine:

```rust
use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

fn to_py_err(e: impl std::fmt::Display) -> PyErr {
    PyRuntimeError::new_err(format!("Operation error: {e}"))
}

/// Async read — returns a Python awaitable.
#[pyfunction]
pub fn read_object<'py>(
    py: Python<'py>,
    store: &StorageStore,
    path: &str,
) -> PyResult<Bound<'py, PyAny>> {
    let inner = store.inner().clone();
    let p = StorePath::from(path);
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = inner.get(&p).await.map_err(to_py_err)?;
        let bytes = result.bytes().await.map_err(to_py_err)?;
        Ok(bytes.to_vec())
    })
}
```

## Sync Calls: LazyLock Runtime + py.detach()

For sync Python functions that must run async Rust code, use a `LazyLock` runtime and `py.detach()` to release the GIL during I/O:

```rust
use std::sync::LazyLock;

/// Lazy-initialized shared tokio runtime for sync operations.
static RUNTIME: LazyLock<tokio::runtime::Runtime> = LazyLock::new(|| {
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .enable_all()
        .build()
        .expect("Failed to create tokio runtime")
});

/// Sync read — releases GIL during I/O.
#[pyfunction]
pub fn read_object_sync(
    py: Python<'_>,
    store: &StorageStore,
    path: &str,
) -> PyResult<Py<PyBytes>> {
    let inner = store.inner().clone();
    let p = StorePath::from(path);
    let bytes = py.detach(|| {
        RUNTIME
            .block_on(async { inner.get(&p).await?.bytes().await })
            .map_err(to_py_err)
    })?;
    Ok(PyBytes::new(py, &bytes).unbind())
}
```

For simple blocking operations:

```rust
/// Sync URL signing — releases GIL during I/O.
#[pyfunction]
#[pyo3(signature = (store, path, expires_in_secs = 3600))]
pub fn signed_url_sync(
    py: Python<'_>,
    store: &StorageStore,
    path: &str,
    expires_in_secs: u64,
) -> PyResult<String> {
    let signer = store.signer().ok_or_else(not_supported)?;
    let p = StorePath::from(path);
    let dur = Duration::from_secs(expires_in_secs);
    py.detach(|| {
        RUNTIME
            .block_on(async { signer.signed_url(http::Method::GET, &p, dur).await })
            .map(|url| url.to_string())
            .map_err(to_py_err)
    })
}
```

## Crossbeam Channels

Use crossbeam for MPSC/SPSC channels when you need cross-thread communication without async:

```toml
[dependencies]
crossbeam-channel = { workspace = true }
crossbeam-utils = { workspace = true }
```

## Tokio Utilities

Use `tokio_util` for compatibility layers and helpers:

```toml
tokio-util = { version = "0.7", features = ["compat"] }
```

Key patterns:

- `tokio::task::spawn_blocking` for CPU-heavy or blocking FFI calls.
- `CancellationToken` for graceful shutdown.
- `tokio::select!` for racing futures.
