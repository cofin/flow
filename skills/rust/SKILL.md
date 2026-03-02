---
name: rust
description: "Rust development patterns for high-performance systems: workspace architecture, async runtimes, platform abstraction, unsafe discipline, FFI surfaces, and testing. Use when writing Rust in any workspace or designing cross-platform systems."
---

# Rust (Systems & Performance)

## Scope

- Multi-crate workspace architecture and dependency management.
- Async runtimes (Tokio), HTTP stacks (Hyper), and embedding engines (deno_core).
- Cross-platform abstraction (Linux/macOS/Windows backends).
- FFI surfaces: PyO3, napi-rs, C ABI.
- Performance-critical code: lock-free structures, shared memory, SIMD.

## Workspace Architecture

Structure workspaces by concern with a pure-logic core:

```
project/
├── Cargo.toml              # [workspace] members
├── crates/
│   ├── core/               # Pure logic, no FFI deps
│   │   ├── src/lib.rs
│   │   └── Cargo.toml
│   ├── server/             # Runtime + networking
│   │   └── Cargo.toml      # depends on core
│   ├── py/                 # PyO3 bindings
│   │   └── Cargo.toml      # cdylib, depends on core
│   └── js/                 # napi-rs bindings
│       └── Cargo.toml      # cdylib, depends on core
└── rust-toolchain.toml
```

**Key rules:**
- Core crate has zero FFI dependencies — bindings wrap it.
- Use `[workspace.dependencies]` to pin shared dependency versions once.
- For Rust 2024 workspaces, prefer `resolver = "3"` (set it explicitly for virtual workspaces).
- Separate `cdylib` crates for each binding target (Python, Node, C).

```toml
# Root Cargo.toml
[workspace]
resolver = "3"
members = ["crates/*"]

[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
thiserror = "1"
```

## Core Rules

### Error Handling

- Use `thiserror` for library errors; `anyhow`/`eyre` only in binaries.
- Never panic across FFI boundaries — catch and convert.
- Define domain-specific error enums per crate:

```rust
#[derive(Debug, thiserror::Error)]
pub enum CoreError {
    #[error("invalid configuration: {0}")]
    Config(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("timeout after {0:?}")]
    Timeout(std::time::Duration),
}
```

### Unsafe Discipline

- Document every `unsafe` block with a `// SAFETY:` comment.
- Enforce safety docs in CI with Clippy (`clippy::undocumented_unsafe_blocks`).
- Isolate platform-specific unsafe in `platform/` modules behind safe traits.
- Prefer `rustix` over raw `libc` for POSIX syscalls.
- Specify atomic `Ordering` explicitly — never default to `SeqCst` without justification.
- Use RAII wrappers for OS handles (fd, mmap, socket, pipe):

```rust
pub struct OwnedFd(RawFd);

impl Drop for OwnedFd {
    fn drop(&mut self) {
        // SAFETY: We own this fd exclusively and close it exactly once.
        unsafe { libc::close(self.0) };
    }
}
```

### Platform Abstraction

Implement OS-specific backends behind a trait:

```rust
// platform/mod.rs
pub trait Notifier: Send + Sync {
    fn notify(&self) -> Result<(), CoreError>;
    fn wait(&self, timeout: Option<Duration>) -> Result<(), CoreError>;
}

// platform/linux.rs — eventfd
// platform/macos.rs — kqueue/ulock
// platform/windows.rs — Win32 Event
```

Use `cfg` for compile-time selection:

```rust
#[cfg(target_os = "linux")]
mod linux;
#[cfg(target_os = "macos")]
mod macos;
#[cfg(target_os = "windows")]
mod windows;
```

## Async Patterns

### Tokio Runtime

- Use `#[tokio::main]` for binaries; pass runtime handle to libraries.
- Prefer `tokio::spawn` over `std::thread::spawn` for I/O-bound work.
- Use `tokio::task::spawn_blocking` for CPU-heavy or blocking FFI calls.
- Graceful shutdown with `CancellationToken`:

```rust
use tokio_util::sync::CancellationToken;

let token = CancellationToken::new();
let child = token.child_token();

tokio::select! {
    _ = child.cancelled() => { /* cleanup */ }
    result = server.run() => { /* handle */ }
}
```

### Hyper HTTP

- Build servers on `hyper::service::service_fn` for control.
- Use `tower` middleware for shared concerns (tracing, auth, compression).
- For coordinated shutdown across connections in Hyper 1.x, use `hyper-util` graceful shutdown patterns.

## FFI Surface Rules

- Expose APIs via PyO3 + napi-rs first (see dedicated skills).
- Add optional C ABI only when stable ABI distribution is required.
- Map errors deterministically — never panic across FFI.
- Do not unwind across non-unwinding ABIs (`extern "C"`); use `extern "C-unwind"` only when explicitly required and validated.
- Return slices/views for zero-copy when lifetime is clear; copy otherwise.
- Use `#[repr(C)]` only for types crossing the C ABI boundary.

## Build & CI

### Maturin (Python extensions)

```toml
# pyproject.toml
[build-system]
requires = ["maturin>=1.8"]
build-backend = "maturin"

[tool.maturin]
features = ["pyo3/extension-module"]
module-name = "my_package._core"
```

### Profile-Guided Optimization (PGO)

```bash
# Install LLVM tools first
rustup component add llvm-tools-preview
# Build instrumented binary
RUSTFLAGS="-Cprofile-generate=/tmp/pgo" cargo build --release
# Run representative workload
./target/release/my_server --benchmark
# Merge profiles and rebuild
llvm-profdata merge -o /tmp/pgo/merged.profdata /tmp/pgo/*.profraw
RUSTFLAGS="-Cprofile-use=/tmp/pgo/merged.profdata" cargo build --release
```

### Cargo Configuration

```toml
# .cargo/config.toml
[profile.release]
lto = "fat"
codegen-units = 1
strip = true

[profile.dev]
opt-level = 0

[profile.bench]
inherits = "release"
debug = true  # flamegraph symbols
```

## Testing

- `cargo test` for unit + integration tests.
- `cargo nextest run` for parallel test execution.
- `proptest` for property-based testing of invariants.
- `criterion` for benchmarks — always compare against a baseline.
- Run Miri on unsafe code (nightly): `rustup +nightly component add miri && cargo +nightly miri test`.
- Use `cargo-llvm-cov` for coverage.
- Sanitizers for binding layers:

```bash
RUSTFLAGS="-Zsanitizer=address" cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu
```

## Conventions

- Format: `cargo fmt` (rustfmt).
- Lint: `cargo clippy -- -D warnings`.
- Document public APIs with `///` doc comments including examples.
- Use `tracing` (not `log`) for structured instrumentation.
- Prefer `Arc<T>` over `Rc<T>` in async contexts.
- Feature-gate optional functionality — don't force heavy deps on all consumers.

## Official References

- Rust Book: https://doc.rust-lang.org/book/
- Rust Reference: https://doc.rust-lang.org/reference/
- Rustonomicon (unsafe + FFI): https://doc.rust-lang.org/nomicon/
- Cargo Reference (workspaces/resolver/profiles): https://doc.rust-lang.org/cargo/reference/
- Rust 2024 resolver notes: https://doc.rust-lang.org/stable/edition-guide/rust-2024/cargo-resolver.html
- rustc PGO guide: https://doc.rust-lang.org/rustc/profile-guided-optimization.html
- Miri (`cargo miri`): https://doc.rust-lang.org/cargo/commands/cargo-miri.html
- Clippy docs + lints: https://doc.rust-lang.org/clippy/
- Tokio docs: https://docs.rs/tokio/latest/tokio/
- Hyper graceful shutdown (1.x): https://hyper.rs/guides/1/server/graceful-shutdown/
- PyO3 docs: https://pyo3.rs/
- napi-rs docs: https://napi.rs/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
