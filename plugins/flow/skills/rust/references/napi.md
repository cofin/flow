# napi-rs (Node/Bun Bindings)

## Module Setup

### Cargo.toml

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "2", features = ["tokio_rt", "serde-json"] }
napi-derive = "2"
my-core = { path = "../core" }

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

### With Tokio Runtime

Enable `tokio_rt` feature for built-in Tokio integration:

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

### Manual Async Task

For fine-grained control over task execution:

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

Call JavaScript callbacks from any Rust thread:

```rust
use napi::threadsafe_function::{ThreadsafeFunction, ThreadSafeCallContext};

#[napi]
pub fn start_worker(callback: ThreadsafeFunction<String>) {
    std::thread::spawn(move || {
        loop {
            let message = receive_message();
            callback.call(Ok(message), napi::threadsafe_function::ThreadsafeFunctionCallMode::NonBlocking);
        }
    });
}
```

**Rules:**

- Always use `NonBlocking` unless you need backpressure.
- TSFN prevents Node from exiting -- call `unref()` if the callback is optional.
- Clone TSFN to share across threads (it's `Send + Sync`).

## Buffer Handling

### Zero-Copy Input

```rust
#[napi]
pub fn process(data: Buffer) -> napi::Result<Buffer> {
    // Buffer provides &[u8] access without copying
    let slice: &[u8] = &data;
    let result = transform(slice);
    Ok(result.into())
}
```

### Typed Arrays

```rust
#[napi]
pub fn sum_float64(arr: Float64Array) -> f64 {
    arr.iter().sum()
}
```

### Large Data -- External Buffer

For data owned by Rust that JS needs to read:

```rust
#[napi]
pub fn create_large_buffer(env: Env) -> napi::Result<JsBuffer> {
    let data: Vec<u8> = generate_large_data();
    // JS gets a view; Rust owns the memory
    unsafe {
        env.create_buffer_with_borrowed_data(
            data.as_ptr(),
            data.len(),
            data,
            |data, _hint| drop(data),
        )
    }
}
```

### Zero-Copy Strategies (Node)

| Mechanism | When |
|-----------|------|
| `napi::Buffer` | Binary data transfer |
| `SharedArrayBuffer` | Web workers / threads |

**Rule:** Avoid copying large buffers across FFI. Use views/slices when lifetime is clear; copy small data (<4KB) for simplicity.

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

### Cross-Language Error Mapping (Core to Node)

Map core errors to JavaScript Error objects:

```rust
impl From<CoreError> for napi::Error {
    fn from(e: CoreError) -> napi::Error {
        napi::Error::from_reason(e.to_string())
    }
}
```

## deno_core Embedding

For embedding V8/TypeScript execution in Rust:

```rust
use deno_core::{JsRuntime, RuntimeOptions, op2};

#[op2]
#[string]
fn op_greet(#[string] name: String) -> String {
    format!("Hello, {name}!")
}

deno_core::extension!(
    my_ext,
    ops = [op_greet],
);

fn create_runtime() -> JsRuntime {
    JsRuntime::new(RuntimeOptions {
        extensions: vec![my_ext::init_ops()],
        ..Default::default()
    })
}
```

### Key deno_core Patterns

- Use `#[op2]` (v2 op macro) for type-safe op registration.
- Use `extension!` macro to bundle ops into loadable extensions.
- `#[serde]` parameter attribute for complex types via serde.
- `OpState` for shared mutable state across ops.
- Prefer `#[string]` over manual v8 string conversion.

## Bun Compatibility

- Target **Node-API** (not Node.js-specific APIs) for Bun support.
- Avoid `node:` built-in imports in JavaScript wrapper code.
- Keep the native surface minimal -- complex logic in Rust, thin JS wrapper.
- Test with both `node` and `bun` in CI.

## Package Distribution

### package.json

```json
{
  "name": "@scope/my-package",
  "main": "index.js",
  "types": "index.d.ts",
  "napi": {
    "name": "my-package",
    "triples": {
      "defaults": true,
      "additional": [
        "aarch64-apple-darwin",
        "aarch64-unknown-linux-gnu",
        "aarch64-unknown-linux-musl"
      ]
    }
  },
  "scripts": {
    "build": "napi build --release --platform",
    "prepublishOnly": "napi prepublish -t npm"
  }
}
```

### TypeScript Definitions

napi-rs auto-generates `.d.ts` files. Verify they're included in the package.

## Testing

- **Rust:** `cargo test` for core logic.
- **Node:** `vitest` or `jest` for JS API surface.
- **Bun:** `bun test` for Bun compatibility.
- **Async:** Test that async operations don't block the event loop.
- **TSFN:** Test callback invocation from background threads.
- **Memory:** Use `--expose-gc` + `process.memoryUsage()` for leak detection.

## Conventions

- Use `#[napi]` macro -- avoid manual `napi::Env` calls when possible.
- Map Rust errors to JS errors consistently via `From` impl.
- Never block the JS event loop -- use async tasks or spawn threads.
- Provide `.d.ts` type definitions for all exports.
- Use `Buffer` for binary data, not `Vec<u8>` (avoids copy).
- Thin bindings: binding crates only do type conversion and API surface shaping.

## Official References

- <https://napi.rs/>
- <https://github.com/napi-rs/napi-rs>
- <https://napi.rs/changelog/napi>
- <https://napi.rs/blog/announce-v3>
- <https://bun.sh/docs/runtime/node-api>
- <https://nodejs.org/api/n-api.html>
