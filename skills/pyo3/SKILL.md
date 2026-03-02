---
name: pyo3
description: "Current PyO3 patterns for Rust-Python bindings: module setup, attach/detach threading model, free-threading, buffer-safe data exchange, async bridging, maturin packaging, and stubs. Use when exposing Rust to Python."
---

# PyO3 (Rust-Python Bindings)

## Scope

- Module initialization and class export.
- Thread attach/detach model and free-threading (Python 3.13+ / 3.14+).
- Buffer protocol and memoryview-safe data exchange.
- Async bridging with `pyo3-async-runtimes`.
- Maturin build configuration and wheel distribution.
- Type stubs (`.pyi`) for IDE support.

## Current Baseline (2026)

- Prefer PyO3 `0.28.x` APIs and naming.
- Use `Python::attach` / `Python::detach` terminology (not `with_gil` / `allow_threads`).
- Free-threaded support defaults changed in recent PyO3:
  - `0.23` to `0.27`: opt-in via `#[pymodule(gil_used = false)]`
  - `0.28+`: default assumes thread-safe module; opt out with `#[pymodule(gil_used = true)]`

## Module Setup

### Cargo.toml

```toml
[lib]
name = "_core"
crate-type = ["cdylib", "rlib"]  # cdylib for Python, rlib for Rust tests

[dependencies]
pyo3 = { version = "0.28", features = ["extension-module"] }

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

## Threading Model (Attach / Detach)

### Detach for long CPU / blocking work

Use `detach` when Python runtime access is not needed:

```rust
#[pymethods]
impl MyClass {
    fn compute(&self, py: Python<'_>) -> PyResult<Vec<u8>> {
        let data = self.inner.clone();
        py.detach(move || {
            // Interpreter detached; Rust can run without blocking Python runtime access.
            Ok(data.process())
        })
    }
}
```

### Free-Threading (Python 3.13+)

- Avoid assuming `Python<'py>` implies global exclusivity.
- Audit `unsafe` and interior mutability paths for true thread safety.
- If your module still requires GIL-based assumptions, mark it explicitly:

```rust
#[pymodule(gil_used = true)]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    Ok(())
}
```

### When attachment is required

- Calling Python APIs or methods.
- Converting to/from Python objects.
- Allocating Python-owned objects.

## Buffer Protocol & Data Transfer

### Important correctness note

- `PyBytes::new` copies input bytes into a Python `bytes` object.
- Do not describe `PyBytes::new` as zero-copy.

### Accepting Python buffers (borrowed view, no extra Rust allocation)

Use `PyBuffer<T>` for typed access to buffer-protocol objects:

```rust
#[pyfunction]
fn process_buffer(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<usize> {
    let buf = PyBuffer::<u8>::get(obj)?;
    let slice = buf.as_slice(py)?;
    py.detach(|| Ok(compute_on_slice(slice)))
}
```

### Returning memoryview from Python-owned buffer objects

Use `PyMemoryView::from(&py_obj)` from a Python object that implements buffer protocol. Avoid ad-hoc raw-pointer memoryview construction patterns in skill docs.

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

Bridge Rust futures to Python awaitables with `pyo3-async-runtimes`:

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

Use crate/runtime versions compatible with your PyO3 major version.

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
- Use modern `Bound<'py, T>` APIs.
- Treat `abi3` and free-threaded builds as separate packaging concerns.
- Document Python-visible APIs in both docstrings and `.pyi` stubs.

## Learn More (Official)

- PyO3 user guide: https://pyo3.rs/main/
- PyO3 migration guide (versioned): https://pyo3.rs/latest/migration.html
- PyO3 changelog: https://pyo3.rs/latest/changelog
- PyO3 free-threading guide: https://pyo3.rs/main/free-threading
- PyBytes docs (`new` copies): https://pyo3.rs/main/doc/pyo3/types/struct.pybytes
- PyBuffer docs: https://pyo3.rs/main/doc/pyo3/buffer/struct.pybuffer
- PyMemoryView docs: https://pyo3.rs/main/doc/pyo3/types/struct.PyMemoryView
- `pyo3-async-runtimes` docs: https://docs.rs/pyo3-async-runtimes/latest/pyo3_async_runtimes/
- Maturin user guide: https://www.maturin.rs/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
