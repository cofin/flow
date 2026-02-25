---
name: pyo3
description: "PyO3 patterns for Rust-Python bindings: module setup, GIL management, free-threading, buffer protocol, async bridging, maturin builds, and type stubs. Use when exposing Rust to Python."
---

# PyO3 (Rust-Python Bindings)

## Scope

- Module initialization and class export.
- GIL management, free-threading (Python 3.13+), and `allow_threads`.
- Buffer protocol and zero-copy data transfer.
- Async bridging with `pyo3-async-runtimes`.
- Maturin build configuration and wheel distribution.
- Type stubs (`.pyi`) for IDE support.

## Module Setup

### Cargo.toml

```toml
[lib]
name = "_core"
crate-type = ["cdylib", "rlib"]  # cdylib for Python, rlib for Rust tests

[dependencies]
pyo3 = { version = "0.24", features = ["extension-module"] }

[features]
extension-module = ["pyo3/extension-module"]
```

**Why `cdylib` + `rlib`:** `cdylib` produces the `.so`/`.pyd` for Python. `rlib` lets you `cargo test` the crate without linking Python.

### Module Init

```rust
use pyo3::prelude::*;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<MyClass>()?;
    m.add_function(wrap_pyfunction!(my_function, m)?)?;
    Ok(())
}
```

**Convention:** Name the Rust module with a `_` prefix (e.g., `_core`). The Python package re-exports from it:

```python
# my_package/__init__.py
from my_package._core import MyClass, my_function
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

### Free-Threading (Python 3.13+)

Detect and handle free-threaded builds:

```rust
#[pymethods]
impl SharedState {
    fn update(&self, py: Python<'_>, value: i64) -> PyResult<()> {
        if py.version_info() >= (3, 13) {
            // Free-threaded: use atomic operations
            self.value.store(value, Ordering::Release);
        } else {
            // GIL-protected: direct mutation safe
            self.value_non_atomic = value;
        }
        Ok(())
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

## Maturin Build

### pyproject.toml

```toml
[build-system]
requires = ["maturin>=1.8"]
build-backend = "maturin"

[project]
name = "my-package"
requires-python = ">=3.10"

[tool.maturin]
features = ["pyo3/extension-module"]
module-name = "my_package._core"
python-source = "python"
```

### Project Layout

```
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

### Cross-Platform Wheels (cibuildwheel)

```toml
# pyproject.toml
[tool.cibuildwheel]
before-all = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
environment = { PATH = "$HOME/.cargo/bin:$PATH" }
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
