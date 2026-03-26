# PyO3 & Maturin Bindings

## Module Registration

Register the native extension module with `#[pymodule]`. Add classes and functions explicitly:

```rust
use pyo3::prelude::*;

/// Whether this build targets free-threaded Python (3.14t+).
#[cfg(Py_GIL_DISABLED)]
pub const FREE_THREADED: bool = true;
#[cfg(not(Py_GIL_DISABLED))]
pub const FREE_THREADED: bool = false;

/// The `_native` extension module.
#[pymodule]
#[pyo3(name = "_native")]
pub fn pymodule_init(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("FREE_THREADED", FREE_THREADED)?;

    // Types
    m.add_class::<MyRequest>()?;
    m.add_class::<MyResponse>()?;

    // Functions
    m.add_function(wrap_pyfunction!(get_batch, m)?)?;
    m.add_function(wrap_pyfunction!(submit_results, m)?)?;

    Ok(())
}
```

For modules that never need the GIL, use `gil_used = false`:

```rust
#[pymodule(gil_used = false)]
fn _http(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__free_threaded__", FREE_THREADED)?;
    m.add_function(wrap_pyfunction!(serve, m)?)?;
    m.add_class::<Router>()?;
    Ok(())
}
```

## Frozen Classes

Use `#[pyclass(frozen)]` for immutable config/data classes. This allows safe sharing across threads:

```rust
#[pyclass(frozen, from_py_object)]
#[derive(Clone, Debug)]
pub struct ObjectMeta {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub size: u64,
    #[pyo3(get)]
    pub last_modified: String,
    #[pyo3(get)]
    pub etag: Option<String>,
}

#[pymethods]
impl ObjectMeta {
    fn __repr__(&self) -> String {
        format!("ObjectMeta(path={:?}, size={})", self.path, self.size)
    }
}
```

## Signature Macros

Use `#[pyo3(signature = (...))]` for keyword-only args and defaults:

```rust
#[pymethods]
impl PyRequest {
    #[new]
    #[pyo3(signature = (method, path, query, headers, body, has_body, route_id=None, path_params=None))]
    fn new(
        py: Python<'_>,
        method: String,
        path: String,
        query: String,
        headers: Vec<(String, String)>,
        body: &[u8],
        has_body: bool,
        route_id: Option<u32>,
        path_params: Option<Py<PyDict>>,
    ) -> Self {
        Self {
            method, path, query,
            body: PyBytes::new(py, body).unbind(),
            has_body, route_id, path_params, headers,
        }
    }
}
```

For functions with many keyword-only args:

```rust
#[pyfunction]
#[pyo3(signature = (store, path, data, *, content_type=None))]
pub fn put_object(
    py: Python<'_>,
    store: &StorageStore,
    path: &str,
    data: &[u8],
    content_type: Option<&str>,
) -> PyResult<PutResult> { /* ... */ }
```

## Zero-Copy Batch Access with Arc

Wrap shared data in `Arc<T>` so Python proxies share the underlying data without copying:

```rust
use std::sync::Arc;

/// Vectorized container for a sealed request batch.
/// O(1) GIL time instead of O(N) for building a Python list.
#[pyclass]
pub struct RequestBatch {
    pub(crate) snapshot: Arc<BatchSnapshot>,
}

#[pymethods]
impl RequestBatch {
    pub fn __len__(&self) -> usize {
        self.snapshot.len()
    }

    pub fn __getitem__(&self, index: usize) -> PyResult<RequestProxy> {
        if index >= self.snapshot.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err(
                "batch index out of range",
            ));
        }
        Ok(RequestProxy::new(Arc::clone(&self.snapshot), index))
    }

    pub fn __iter__(slf: PyRef<'_, Self>) -> PyResult<Py<RequestBatchIter>> {
        let iter = RequestBatchIter {
            snapshot: Arc::clone(&slf.snapshot),
            index: 0,
        };
        Py::new(slf.py(), iter)
    }
}
```

## Free-Threaded Python Detection

Detect free-threaded Python (3.14t+) at compile time via `Py_GIL_DISABLED`:

```rust
#[cfg(Py_GIL_DISABLED)]
pub(crate) const FREE_THREADED: bool = true;
#[cfg(not(Py_GIL_DISABLED))]
pub(crate) const FREE_THREADED: bool = false;
```

Allow the cfg in workspace lints:

```toml
[workspace.lints.rust]
unexpected_cfgs = { level = "allow", check-cfg = ['cfg(Py_GIL_DISABLED)'] }
```

Use conditional logic based on GIL status:

```rust
#[cfg(Py_GIL_DISABLED)]
{
    // Free-threaded path: multiple event loops, no GIL contention
}
#[cfg(not(Py_GIL_DISABLED))]
{
    // GIL path: single event loop, use py.detach() for I/O
}
```

## build.rs with pyo3_build_config

The binding crate needs `pyo3-build-config` to detect Python configuration at build time:

```toml
# crates/py/Cargo.toml
[build-dependencies]
pyo3-build-config = { version = "0.28.2", features = ["resolve-config"] }
```

```rust
// build.rs
fn main() {
    pyo3_build_config::use_pyo3_cfgs();
}
```

## Binding Crate Cargo.toml

The binding crate produces both cdylib (for maturin) and rlib (for embedding):

```toml
[package]
name = "project-py"
version.workspace = true
edition.workspace = true

[dependencies]
project-core = { path = "../core" }
pyo3 = { workspace = true }

[build-dependencies]
pyo3-build-config = { version = "0.28.2", features = ["resolve-config"] }

[features]
default = []
extension-module = ["pyo3/extension-module"]

[lib]
name = "_project"
crate-type = ["cdylib", "rlib"]
```

## Maturin pyproject.toml Config

```toml
[build-system]
requires = ["maturin>=1.5,<2"]
build-backend = "maturin"

[tool.maturin]
python-source = "src/py"
module-name = "mypackage._native"
manifest-path = "src/rs/project-py/Cargo.toml"
```

For standalone crates with `package.metadata.maturin`:

```toml
# Inside Cargo.toml
[package.metadata.maturin]
python-source = "../../../src/py"
module-name = "mypackage._http"
bindings = "pyo3"
```

## GIL Management

### Release GIL for CPU Work

Always release the GIL when doing CPU-bound Rust work:

```rust
#[pymethods]
impl MyClass {
    fn compute(&self, py: Python<'_>) -> PyResult<Vec<u8>> {
        let data = self.inner.clone();
        py.allow_threads(move || {
            // GIL released — Python threads can run
            Ok(data.process())
        })
    }
}
```

### When to Hold the GIL

- Calling Python objects or APIs (`PyDict`, `PyList`, callbacks).
- Accessing `Python<'_>` token for type conversions.
- Creating new Python objects.

## Buffer Protocol & Zero-Copy

### Exposing Rust Data to Python

Use `PyBuffer` for zero-copy access to contiguous Rust data:

```rust
#[pymethods]
impl RingBuffer {
    fn read_into<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let data = self.inner.read()?;
        // Zero-copy: creates PyBytes pointing to Rust data
        Ok(PyBytes::new(py, &data))
    }
}
```

### Accepting Python Buffers

```rust
#[pyfunction]
fn process_buffer(py: Python<'_>, buf: PyBuffer<u8>) -> PyResult<usize> {
    // Access contiguous memory without copying
    let slice = buf.as_slice(py)?;
    py.allow_threads(|| Ok(compute_on_slice(slice)))
}
```

### memoryview for Large Data

```rust
#[pymethods]
impl SharedMemoryRegion {
    fn as_memoryview<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyMemoryView>> {
        // SAFETY: Region outlives the memoryview (enforced by Python ref to self)
        unsafe {
            let ptr = self.inner.as_ptr();
            let len = self.inner.len();
            PyMemoryView::from_raw_parts(py, ptr, len)
        }
    }
}
```

### Zero-Copy Strategies (Python)

| Mechanism | When |
|-----------|------|
| `PyBuffer` / `memoryview` | Large contiguous data |
| `PyBytes::new(py, &data)` | Immutable byte data |

**Rule:** Avoid copying large buffers across FFI. Use views/slices when lifetime is clear; copy small data (<4KB) for simplicity.

## Error Mapping

Map Rust errors to Python exceptions deterministically:

```rust
use pyo3::exceptions::{PyValueError, PyRuntimeError, PyIOError};

impl From<CoreError> for PyErr {
    fn from(err: CoreError) -> PyErr {
        match err {
            CoreError::Config(msg) => PyValueError::new_err(msg),
            CoreError::Io(e) => PyIOError::new_err(e.to_string()),
            CoreError::Timeout(d) => PyRuntimeError::new_err(
                format!("operation timed out after {d:?}")
            ),
        }
    }
}
```

## Async Bridging

Bridge Tokio futures to Python async:

```rust
use pyo3_async_runtimes::tokio::future_into_py;

#[pymethods]
impl AsyncClient {
    fn fetch<'py>(&self, py: Python<'py>, url: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        future_into_py(py, async move {
            let resp = client.get(&url).await.map_err(CoreError::from)?;
            Ok(resp.body().to_vec())
        })
    }
}
```

## Type Stubs (.pyi)

Provide `.pyi` files for IDE autocompletion and mypy:

```python
# my_package/_core.pyi
from typing import Optional

__version__: str

class MyClass:
    def __init__(self, capacity: int) -> None: ...
    def compute(self) -> bytes: ...
    async def fetch(self, url: str) -> bytes: ...

def process_buffer(buf: bytes | bytearray | memoryview) -> int: ...
```

## Cross-Platform Wheels (cibuildwheel)

```toml
# pyproject.toml
[tool.cibuildwheel]
before-all = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
environment = { PATH = "$HOME/.cargo/bin:$PATH" }
skip = ["pp*", "*-musllinux_i686"]
```

## Project Layout

```text
project/
├── Cargo.toml
├── pyproject.toml
├── src/lib.rs              # Rust source
├── python/
│   └── my_package/
│       ├── __init__.py     # Re-exports from _core
│       ├── _core.pyi       # Type stubs
│       └── py.typed        # PEP 561 marker
└── tests/
    └── test_bindings.py    # Python-side tests
```

## Testing

- **Rust side:** `cargo test` with `rlib` crate type.
- **Python side:** `pytest` with `maturin develop` for dev builds.
- **Integration:** Test GIL release under threading (`concurrent.futures.ThreadPoolExecutor`).
- **Memory:** Use `tracemalloc` to verify zero-copy patterns aren't leaking.

## Conventions

- Name Rust modules with `_` prefix: `_core`, `_engine`.
- Always add `__version__` from `CARGO_PKG_VERSION`.
- Use `Bound<'py, T>` (not `&T`) for PyO3 0.22+ API.
- Prefer `abi3` when targeting multiple Python versions without recompilation.
- Document Python-visible APIs in both docstrings and `.pyi` stubs.
- Use `extension-module` feature only in cdylib crates, never in the core.

## Official References

- <https://pyo3.rs/main/>
- <https://pyo3.rs/main/changelog.html>
- <https://pyo3.rs/latest/migration.html>
- <https://pyo3.rs/main/free-threading>
- <https://pyo3.rs/main/doc/pyo3/types/struct.pybytes>
- <https://www.maturin.rs/>
