# Rust Style Guide

Performance-critical Rust with safe abstractions and FFI support.

## Core Rules

### Unsafe Code
```rust
// Document every unsafe block with a Safety section
unsafe {
    // SAFETY: The pointer is valid because:
    // 1. It was just allocated above
    // 2. No other references exist
    // 3. The lifetime is bounded by this scope
    ptr::write(dest, value);
}
```

### Atomic Ordering
```rust
// Always specify ordering explicitly - never default to SeqCst
use std::sync::atomic::{AtomicUsize, Ordering};

let counter = AtomicUsize::new(0);

// Use appropriate ordering for your use case
counter.fetch_add(1, Ordering::Relaxed);      // No synchronization needed
counter.load(Ordering::Acquire);               // Synchronize with Release
counter.store(value, Ordering::Release);       // Pair with Acquire
counter.compare_exchange(                      // For lock-free algorithms
    old, new,
    Ordering::AcqRel,
    Ordering::Acquire,
);
```

### RAII for Resources
```rust
// Wrap OS handles in types that implement Drop
pub struct FileMapping {
    ptr: *mut u8,
    len: usize,
}

impl Drop for FileMapping {
    fn drop(&mut self) {
        // SAFETY: ptr was allocated by mmap and is valid
        unsafe { munmap(self.ptr as *mut _, self.len) };
    }
}
```

## Naming Conventions

| Concept | Convention | Example |
|---------|------------|---------|
| Types/Traits | `PascalCase` | `ConnectionPool` |
| Functions | `snake_case` | `create_connection` |
| Variables | `snake_case` | `current_buffer` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_BUFFER_SIZE` |
| Modules | `snake_case` | `connection_pool` |
| Lifetimes | Short lowercase | `'a`, `'buf` |
| Type parameters | Short or descriptive | `T`, `K`, `V`, `Item` |

## Error Handling

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum TransportError {
    #[error("connection failed: {0}")]
    Connection(#[from] std::io::Error),

    #[error("invalid message format")]
    InvalidFormat,

    #[error("buffer overflow: {size} exceeds {max}")]
    BufferOverflow { size: usize, max: usize },
}

// Use Result for fallible operations
pub fn send_message(msg: &[u8]) -> Result<(), TransportError> {
    if msg.len() > MAX_MESSAGE_SIZE {
        return Err(TransportError::BufferOverflow {
            size: msg.len(),
            max: MAX_MESSAGE_SIZE,
        });
    }
    // ...
    Ok(())
}
```

## Zero-Copy Patterns

```rust
// Return slices/views for zero-copy when safe
impl Buffer {
    /// Returns a view into the buffer's data.
    ///
    /// The returned slice is valid for the lifetime of the buffer.
    pub fn as_slice(&self) -> &[u8] {
        // SAFETY: data is valid and properly aligned
        unsafe { std::slice::from_raw_parts(self.ptr, self.len) }
    }
}

// Avoid hidden copies
// Bad: Unnecessary allocation
fn process_bad(data: &[u8]) -> Vec<u8> {
    data.to_vec()  // Copies!
}

// Good: Work with borrowed data
fn process_good(data: &[u8]) -> &[u8] {
    &data[..data.len().min(1024)]
}
```

## Platform Abstraction

```rust
// Isolate OS-specific code in platform modules
#[cfg(unix)]
mod unix {
    pub fn create_socket() -> io::Result<RawFd> { ... }
}

#[cfg(windows)]
mod windows {
    pub fn create_socket() -> io::Result<SOCKET> { ... }
}

// Prefer rustix for POSIX APIs
use rustix::fs::{open, Mode, OFlags};
```

## FFI Guidelines

### PyO3 (Python)
```rust
use pyo3::prelude::*;

#[pymodule]
fn _mymodule(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<MyClass>()?;
    Ok(())
}

#[pyclass]
struct MyClass {
    inner: InnerType,
}

#[pymethods]
impl MyClass {
    #[new]
    fn new() -> Self { ... }

    // Release GIL for CPU-bound work
    fn compute(&self, py: Python<'_>) -> PyResult<i64> {
        py.allow_threads(|| {
            self.inner.heavy_computation()
        })
    }
}
```

### napi-rs (JavaScript)
```rust
use napi::bindgen_prelude::*;

#[napi]
pub struct Connection {
    inner: InnerConnection,
}

#[napi]
impl Connection {
    #[napi(constructor)]
    pub fn new() -> Result<Self> { ... }

    #[napi]
    pub async fn query(&self, sql: String) -> Result<Vec<Row>> {
        // Async work runs off the JS thread
        self.inner.query(&sql).await
    }
}
```

### FFI Rules
- Map errors deterministically to language exceptions
- Never panic across FFI boundaries
- Use zero-copy buffers only with safe lifetime management
- Prefer language-specific bindings (PyO3, napi-rs) over raw C ABI

## Performance Patterns

```rust
// Align shared memory to cache lines
#[repr(C, align(64))]
struct CacheAligned {
    data: [u8; 64],
}

// Use power-of-two sizes for ring buffers
const BUFFER_SIZE: usize = 1 << 16;  // 65536

// Prefer stack allocation for small, fixed-size data
let mut buffer = [0u8; 1024];

// Use Vec::with_capacity to avoid reallocations
let mut items = Vec::with_capacity(expected_count);
```

## Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_buffer_operations() {
        let buf = Buffer::new(1024);
        assert_eq!(buf.len(), 1024);
    }

    // Use proptest for property-based testing
    proptest! {
        #[test]
        fn test_roundtrip(data: Vec<u8>) {
            let encoded = encode(&data);
            let decoded = decode(&encoded).unwrap();
            prop_assert_eq!(data, decoded);
        }
    }
}

// Run Miri on unsafe code
// cargo +nightly miri test
```

## Tooling

- **Formatter**: `rustfmt`
- **Linter**: `clippy`
- **Build**: `cargo`
- **Unsafe checker**: `miri`
- **Memory checker**: `valgrind`, `AddressSanitizer`

## Anti-Patterns

```rust
// Bad: Defaulting to SeqCst
counter.fetch_add(1, Ordering::SeqCst);  // Too strong

// Bad: Undocumented unsafe
unsafe { ptr::read(p) }  // Why is this safe?

// Bad: Panicking in library code
pub fn parse(input: &str) -> Value {
    input.parse().unwrap()  // Don't panic!
}

// Good: Return Result
pub fn parse(input: &str) -> Result<Value, ParseError> {
    input.parse()
}

// Bad: Hidden allocations
fn get_data(&self) -> Vec<u8> {
    self.data.clone()  // Caller might not need ownership
}

// Good: Return reference when possible
fn get_data(&self) -> &[u8] {
    &self.data
}
```
