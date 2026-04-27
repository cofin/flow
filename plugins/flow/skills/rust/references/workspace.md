# Workspace Architecture

## Directory Layout

Structure workspaces by concern with a pure-logic core crate and separate binding crates:

```text
project/
├── Cargo.toml              # [workspace] root
├── crates/
│   ├── core/               # Pure logic, no FFI deps
│   │   ├── src/lib.rs
│   │   └── Cargo.toml
│   ├── http/               # Runtime + networking (binary or cdylib)
│   │   └── Cargo.toml      # depends on core
│   ├── py/                 # PyO3 bindings
│   │   └── Cargo.toml      # cdylib + rlib, depends on core
│   └── bundler/            # Optional tool crate
│       └── Cargo.toml
└── rust-toolchain.toml
```

Core crate has zero FFI dependencies. Binding crates wrap it.

## Centralized Dependencies

Pin shared dependency versions once in the workspace root. Crates reference with `{ workspace = true }`:

```toml
# Root Cargo.toml
[workspace]
resolver = "2"
members = ["crates/*"]

[workspace.package]
version = "0.1.0"
edition = "2021"
authors = ["Project Contributors"]
license = "MIT"

[workspace.dependencies]
arrow = "53.0"
criterion = { version = "0.5", features = ["async_tokio"] }
crossbeam-channel = "0.5"
crossbeam-utils = "0.8"
libc = "0.2"
proptest = "1.6"
rustix = "0.38"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
thiserror = "2.0"
tokio = { version = "1.35", features = ["full"] }
pyo3 = { version = "0.28.2" }
windows-sys = { version = "0.52", features = ["Win32_System_Memory", "Win32_System_Threading"] }
```

Individual crates reference workspace deps:

```toml
# crates/core/Cargo.toml
[package]
name = "project-core"
version.workspace = true
edition.workspace = true

[dependencies]
crossbeam-channel = { workspace = true }
serde = { workspace = true }
thiserror = { workspace = true }
tokio = { workspace = true }
lz4_flex = { workspace = true, optional = true }
zstd = { workspace = true, optional = true }

[target.'cfg(unix)'.dependencies]
libc = { workspace = true }
rustix = { workspace = true, features = ["fs"] }

[target.'cfg(windows)'.dependencies]
windows-sys = { workspace = true }

[dev-dependencies]
criterion = { workspace = true }
proptest = { workspace = true }

[lints]
workspace = true
```

## Release Profile

Optimize for maximum performance in release builds:

```toml
[profile.release]
lto = true
codegen-units = 1
opt-level = 3
```

## Feature Flags

Use `dep:name` syntax for conditional dependencies. Group features logically:

```toml
[features]
default = ["compression"]
compression = ["dep:lz4_flex", "dep:zstd"]
dev-proxy = ["dep:reqwest"]
js-runtime = ["dep:project-js"]
grpc = ["dep:tonic", "dep:prost", "dep:tonic-health", "dep:tonic-reflection"]
free-threading = []
```

Benchmarks can require features:

```toml
[[bench]]
name = "codec"
harness = false
required-features = ["compression"]
```

## Module Hierarchy

Organize the core crate lib.rs with public re-exports for ergonomics:

```rust
//! Core IPC primitives and shared types.

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub mod async_ring;
pub mod batch;
pub mod buffer;
pub mod channel;
pub mod platform;
pub mod protocol;
pub mod shm;
pub mod sync;
pub mod transport;

// Re-exports for ergonomics
pub use batch::{BatchArena, BatchError, BatchNode};
pub use transport::{BatchSnapshot, TransportError, TransportNode};
```
