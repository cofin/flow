---
name: napi-rs
description: "napi-rs patterns for Rust-Node/Bun bindings: module setup, async tasks, ThreadsafeFunction (TSFN), typed arrays/buffers, error mapping, and packaging with @napi-rs/cli v3."
---

# napi-rs (Rust-JavaScript Bindings)

## Scope

- Module setup with `#[napi]` macros.
- Async execution via `async fn` and `AsyncTask`.
- ThreadsafeFunction (TSFN) for callbacks from Rust threads.
- Buffer and typed-array handling with v3 lifetime-safe types.
- Error mapping for stable JS-facing error contracts.
- Packaging/distribution with `@napi-rs/cli`.
- Bun compatibility via Node-API.

## Module Setup

### Cargo.toml

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "3", features = ["async"] }
napi-derive = "3"

[build-dependencies]
napi-build = "2"
```

### build.rs

```rust
fn main() {
    napi_build::setup();
}
```

### Basic Export

```rust
use napi::bindgen_prelude::*;
use napi_derive::napi;

#[napi]
pub fn add(a: u32, b: u32) -> u32 {
  a + b
}

#[napi]
pub struct Engine {
    inner: core::Engine,
}

#[napi]
impl Engine {
    #[napi(constructor)]
    pub fn new(config: String) -> napi::Result<Self> {
        let inner = core::Engine::new(&config)
            .map_err(|e| napi::Error::from_reason(e.to_string()))?;
        Ok(Self { inner })
    }

    #[napi]
    pub fn process_sync(&self, data: Buffer) -> napi::Result<Buffer> {
        let result = self.inner.process(&data)
            .map_err(|e| napi::Error::from_reason(e.to_string()))?;
        Ok(result.into())
    }
}
```

## Async Tasks

### `async fn` (preferred)

Enable `async` (or `tokio_rt`) on `napi` to export async functions:

```rust
#[napi]
impl Engine {
    #[napi]
    pub async fn fetch(&self, url: String) -> napi::Result<Buffer> {
        // Runs on Tokio runtime, doesn't block JS event loop
        let response = self.inner.fetch(&url).await
            .map_err(|e| napi::Error::from_reason(e.to_string()))?;
        Ok(response.body().into())
    }
}
```

### `AsyncTask` / `Task` (CPU-bound work)

Use `Task` when you want explicit `compute` + `resolve` separation:

```rust
use napi::{Task, Env, JsNumber};

struct ComputeTask {
    input: Vec<u8>,
}

impl Task for ComputeTask {
    type Output = usize;
    type JsValue = JsNumber;

    fn compute(&mut self) -> napi::Result<Self::Output> {
        // Runs on libuv thread pool — off the main JS thread
        Ok(heavy_computation(&self.input))
    }

    fn resolve(&mut self, env: Env, output: Self::Output) -> napi::Result<Self::JsValue> {
        env.create_uint32(output as u32)
    }
}
```

## ThreadsafeFunction (TSFN)

Use TSFN to invoke JS from non-main threads:

```rust
use std::sync::Arc;
use napi::threadsafe_function::{ThreadsafeFunction, ThreadsafeFunctionCallMode};

#[napi]
pub fn start_worker(tsfn: Arc<ThreadsafeFunction<String>>) {
    for _ in 0..2 {
        let tsfn = tsfn.clone();
        std::thread::spawn(move || {
            let _ = tsfn.call("tick".to_string(), ThreadsafeFunctionCallMode::NonBlocking);
        });
    }
}
```

Notes:
- In v3, TSFN was redesigned; prefer high-level ownership patterns over low-level lifecycle control.
- Use `Arc<ThreadsafeFunction<...>>` when shared across threads.
- Use `NonBlocking` unless blocking semantics are explicitly required.
- If you do not want TSFN to keep the loop alive, use the weak TSFN form documented by napi-rs.

## Typed Arrays and Buffers

Prefer the v3 typed-array model:
- `Buffer`, `Uint8Array`, etc. for owned values (safe across async boundaries).
- `BufferSlice<'env>`, `Uint8ArraySlice<'env>`, `&[u8]` for borrowed zero-copy sync access.

```rust
use napi::bindgen_prelude::*;
use napi_derive::napi;

#[napi]
pub async fn reverse(buf: Buffer) -> Buffer {
    let mut v: Vec<u8> = buf.into();
    v.reverse();
    v.into()
}
```

For external memory, use the v3 external/buffer APIs and keep ownership/finalization explicit.

## Error Mapping

```rust
use napi::Error;

#[derive(Debug, thiserror::Error)]
pub enum EngineError {
    #[error("config error: {0}")]
    Config(String),
    #[error("timeout: {0:?}")]
    Timeout(std::time::Duration),
}

impl From<EngineError> for napi::Error {
    fn from(e: EngineError) -> napi::Error {
        Error::from_reason(e.to_string())
    }
}
```

Guidelines:
- Map domain errors into stable, user-readable JS errors.
- Keep Rust-internal error detail out of public JS API unless intentionally exposed.

## Packaging and Distribution (`@napi-rs/cli`)

Use modern CLI/config naming (v3 migration):
- `napi.name` -> `napi.binaryName`
- `napi.triples` -> `napi.targets`
- `napi build --cargo-flags=...` -> `napi build -- ...`

Example `package.json` (modern keys):

```json
{
  "name": "@scope/my-package",
  "main": "index.js",
  "types": "index.d.ts",
  "napi": {
    "binaryName": "my-package",
    "targets": [
      "x86_64-unknown-linux-gnu",
      "x86_64-pc-windows-msvc",
      "x86_64-apple-darwin",
      "aarch64-apple-darwin",
      "aarch64-unknown-linux-gnu"
    ]
  },
  "scripts": {
    "build": "napi build --platform --release",
    "prepublishOnly": "napi pre-publish"
  }
}
```

## Bun Compatibility

- Bun supports Node-API broadly; keep addons Node-API-centric (avoid runtime-specific native assumptions).
- Validate loading and core API behavior on both `node` and `bun` for published addons.

## Conventions

- Use `#[napi]` exports and v3 value types by default.
- Prefer owned types (`Buffer`, `Uint8Array`) for async flows.
- Prefer borrowed slice types only within synchronous/lifetime-bounded scopes.
- Avoid legacy `compat-mode` APIs unless migration constraints require them.
- Keep JS wrapper thin; place heavy logic in Rust.

## Where to learn more (official)

- NAPI-RS docs: https://napi.rs/docs/introduction/getting-started
- NAPI-RS v2->v3 migration: https://napi.rs/docs/more/v2-v3-migration-guide
- NAPI-RS ThreadsafeFunction concept: https://napi.rs/docs/concepts/threadsafe-function
- NAPI-RS typed arrays/buffers: https://napi.rs/docs/concepts/typed-array
- NAPI-RS async fn: https://napi.rs/docs/concepts/async-fn
- NAPI-RS AsyncTask: https://napi.rs/docs/concepts/async-task
- NAPI-RS CLI build: https://napi.rs/docs/cli/build
- NAPI-RS CLI pre-publish: https://napi.rs/docs/cli/pre-publish
- NAPI-RS changelog: https://napi.rs/changelog/napi
- Rust crate docs (`napi`): https://docs.rs/napi/latest/napi/
- Node-API docs: https://nodejs.org/api/n-api.html
- Node-API thread-safe functions: https://nodejs.org/api/n-api.html#asynchronous-thread-safe-function-calls
- Bun Node-API docs: https://bun.sh/docs/api/node-api

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
