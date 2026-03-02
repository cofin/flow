---
name: rust-bindings
description: "Concise patterns for polyglot Rust extensions: core/bindings workspace layout, PyO3 + maturin (Python), napi-rs (Node/Bun via Node-API), optional C ABI, packaging, and cross-language testing."
---

# Rust Bindings (Polyglot Extensions)

Use this skill when you need stable, maintainable Rust bindings for Python, Node/Bun, or C consumers.

## Core Architecture (recommended)

Keep business logic isolated from FFI layers:

```
project/
├── Cargo.toml                # [workspace]
├── crates/
│   ├── core/                 # Pure Rust — no FFI deps
│   ├── py/                   # Python bindings
│   └── js/                   # Node/Bun bindings
├── python/                   # Python package source
│   └── my_package/
└── rust-toolchain.toml
```

Rules:
- `core` crate: no PyO3/napi dependencies.
- Binding crates: thin conversion/error-mapping only.
- Prefer shared dependency pinning in `[workspace.dependencies]`.

## Python: PyO3 + maturin

### Cargo.toml

```toml
[package]
name = "my-package-py"

[lib]
name = "_core"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { version = "0.26", features = ["extension-module"] } # check latest compatibility
my-core = { path = "../core" }
```

Use modern `Bound<'_, PyModule>` API and keep bindings minimal.

`pyproject.toml` baseline:

```toml
[build-system]
requires = ["maturin>=1.8,<2"]
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

For wheel CI, prefer official `maturin-action` and/or `cibuildwheel` guidance over custom scripts.

## Node/Bun: napi-rs

### Cargo.toml

```toml
[package]
name = "my-package-js"

[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "3", features = ["tokio_rt"] } # verify against docs/changelog
napi-derive = "3"
my-core = { path = "../core" }
```

Package metadata example:

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

Note:
- napi-rs targets Node-API; Bun runs many Node-API addons, but compatibility is not complete.
- Validate on both Node and Bun in CI if Bun support is promised.

## Error Mapping

Define one core error enum, then map:
- Python: `PyValueError`, `PyRuntimeError`, `PyIOError`, etc.
- Node/Bun: `napi::Error::from_reason(...)`.
- C ABI: explicit integer error codes + message retrieval function.

## C ABI (optional but useful for long-lived integrations)

- Use `extern "C"` explicitly.
- Prefer opaque handles over exposing Rust structs.
- Never unwind across FFI boundaries.
- Generate headers with `cbindgen` when exporting C API.

## Performance / Safety Checklist

- Avoid unnecessary copies for large buffers.
- Keep `unsafe` localized and documented.
- Benchmark cross-boundary calls (batching often beats per-item FFI).
- Provide `.pyi` for Python and `.d.ts` for JS/TS users.

## Testing Matrix (minimum)

- Rust core: `cargo test` (+ `proptest` for invariants).
- Python package: `pytest` for API, exceptions, and concurrency behavior.
- Node package: `vitest`/`bun test` for API and async behavior.
- Safety checks: `cargo miri test` where applicable.

## Official Learn More

- PyO3 guide: https://pyo3.rs/latest/
- PyO3 migration guide: https://pyo3.rs/latest/migration.html
- PyO3 changelog: https://pyo3.rs/latest/changelog
- maturin user guide: https://www.maturin.rs/
- maturin `pyproject.toml` config: https://docs.rs/maturin/latest/maturin/pyproject_toml/index.html
- maturin GitHub Action: https://github.com/PyO3/maturin-action
- cibuildwheel options: https://cibuildwheel.pypa.io/en/stable/options/
- napi-rs docs: https://napi.rs/
- napi-rs changelog: https://napi.rs/changelog/napi
- napi-rs v3 announcement: https://napi.rs/blog/announce-v3
- Node-API (official Node.js): https://nodejs.org/api/n-api.html
- Node ABI stability guide: https://nodejs.org/en/docs/guides/abi-stability/
- Bun Node-API support: https://bun.sh/docs/api/node-api
- Rust ABI reference: https://doc.rust-lang.org/reference/abi.html
- Rust Nomicon FFI: https://doc.rust-lang.org/nomicon/ffi.html
- cbindgen: https://github.com/mozilla/cbindgen

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
