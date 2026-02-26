---
name: rust-bindings
description: "Patterns for polyglot Rust extensions: workspace architecture, PyO3 + maturin for Python, napi-rs for Node/Bun, C ABI, cross-platform wheel distribution, and testing strategies. Use when creating Rust bindings for any target language."
---

# Rust Bindings (Polyglot Extensions)

## Scope

- Workspace architecture for multi-language bindings.
- Python bindings (PyO3 + maturin).
- Node/Bun bindings (napi-rs).
- Optional C ABI for stable distribution.
- Cross-platform wheel and npm package distribution.
- Testing across language boundaries.

## Workspace Architecture

Separate pure logic from binding layers:

```
project/
├── Cargo.toml                # [workspace]
├── crates/
│   ├── core/                 # Pure Rust — no FFI deps
│   │   ├── src/lib.rs
│   │   └── Cargo.toml
│   ├── py/                   # Python bindings
│   │   ├── src/lib.rs
│   │   ├── Cargo.toml        # cdylib + rlib
│   │   └── pyproject.toml    # maturin config
│   └── js/                   # Node/Bun bindings
│       ├── src/lib.rs
│       ├── Cargo.toml        # cdylib
│       └── package.json      # napi-rs config
├── python/                   # Python package source
│   └── my_package/
│       ├── __init__.py
│       ├── _core.pyi         # Type stubs
│       └── py.typed
└── rust-toolchain.toml
```

### Key Principles

- **Pure core:** All business logic in the core crate. Zero FFI dependencies.
- **Thin bindings:** Binding crates only do type conversion and API surface shaping.
- **Shared deps:** Use `[workspace.dependencies]` to pin versions once:

```toml
[workspace.dependencies]
tokio = { version = "1.49", features = ["full"] }
serde = { version = "1", features = ["derive"] }
thiserror = "2"
```

## Python Bindings (PyO3 + Maturin)

### Cargo.toml

```toml
[package]
name = "my-package-core"

[lib]
name = "_core"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { version = "0.24", features = ["extension-module"] }
my-core = { path = "../core" }
```

### Module Init

```rust
use pyo3::prelude::*;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<MyClass>()?;
    Ok(())
}

#[pyclass]
struct MyClass {
    inner: my_core::Engine,
}

#[pymethods]
impl MyClass {
    #[new]
    fn new(config: &str) -> PyResult<Self> {
        let inner = my_core::Engine::new(config)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        Ok(Self { inner })
    }

    fn process(&self, py: Python<'_>, data: &[u8]) -> PyResult<Vec<u8>> {
        let inner = self.inner.clone();
        let data = data.to_vec();
        py.allow_threads(move || {
            inner.process(&data)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
        })
    }
}
```

### Maturin Config

```toml
# pyproject.toml
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
manifest-path = "crates/py/Cargo.toml"
```

### Cross-Platform Wheels

```toml
# pyproject.toml
[tool.cibuildwheel]
before-all = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
environment = { PATH = "$HOME/.cargo/bin:$PATH" }
skip = ["pp*", "*-musllinux_i686"]
```

## Node/Bun Bindings (napi-rs)

### Cargo.toml

```toml
[package]
name = "my-package-js"

[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "2", features = ["tokio_rt", "serde-json"] }
napi-derive = "2"
my-core = { path = "../core" }
```

### Implementation

```rust
use napi_derive::napi;

#[napi]
pub struct MyClass {
    inner: my_core::Engine,
}

#[napi]
impl MyClass {
    #[napi(constructor)]
    pub fn new(config: String) -> napi::Result<Self> {
        let inner = my_core::Engine::new(&config)
            .map_err(|e| napi::Error::from_reason(e.to_string()))?;
        Ok(Self { inner })
    }

    #[napi]
    pub async fn process(&self, data: Buffer) -> napi::Result<Buffer> {
        let result = self.inner.process(&data)
            .map_err(|e| napi::Error::from_reason(e.to_string()))?;
        Ok(result.into())
    }
}
```

### package.json (napi-rs)

```json
{
  "name": "my-package",
  "napi": {
    "name": "my-package",
    "triples": {
      "defaults": true,
      "additional": ["aarch64-apple-darwin", "aarch64-unknown-linux-gnu"]
    }
  }
}
```

## Error Mapping

Map core errors to each language's idiom:

```rust
// Core error (shared)
#[derive(Debug, thiserror::Error)]
pub enum CoreError {
    #[error("invalid config: {0}")]
    Config(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

// Python: map to exceptions
impl From<CoreError> for PyErr {
    fn from(e: CoreError) -> PyErr {
        match e {
            CoreError::Config(m) => PyValueError::new_err(m),
            CoreError::Io(e) => PyIOError::new_err(e.to_string()),
        }
    }
}

// Node: map to Error objects
impl From<CoreError> for napi::Error {
    fn from(e: CoreError) -> napi::Error {
        napi::Error::from_reason(e.to_string())
    }
}
```

## Zero-Copy Strategies

| Language | Mechanism | When |
|----------|-----------|------|
| Python | `PyBuffer` / `memoryview` | Large contiguous data |
| Python | `PyBytes::new(py, &data)` | Immutable byte data |
| Node | `napi::Buffer` | Binary data transfer |
| Node | `SharedArrayBuffer` | Web workers / threads |
| C | Raw pointer + length | Stable ABI consumers |

**Rule:** Avoid copying large buffers across FFI. Use views/slices when lifetime is clear; copy small data (<4KB) for simplicity.

## Testing Strategy

| Layer | Tool | What to Test |
|-------|------|-------------|
| Core (Rust) | `cargo test` | Business logic, edge cases |
| Core (Rust) | `proptest` | Invariants, fuzz inputs |
| Python bindings | `pytest` | API surface, error mapping |
| Python bindings | `pytest` + threads | GIL release under concurrency |
| Node bindings | `vitest` / `bun test` | API surface, async behavior |
| Memory | `valgrind` / `tracemalloc` | Leak detection across FFI |
| Unsafe | `cargo miri test` | Undefined behavior in core |

## Conventions

- Core crate: no `unsafe` if possible, no FFI deps.
- Binding crates: thin wrappers, only type conversion.
- Always provide type stubs (`.pyi`) for Python and `.d.ts` for TypeScript.
- Test in the target language, not just Rust.
- Document public APIs in both Rust doc comments and target language docs.
- Use `extension-module` feature only in cdylib crates, never in the core.

## Official References

- https://pyo3.rs/
- https://pyo3.rs/latest/migration.html
- https://github.com/PyO3/pyo3/releases
- https://www.maturin.rs/
- https://napi.rs/
- https://github.com/napi-rs/napi-rs/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
