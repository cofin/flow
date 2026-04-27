# Testing & Benchmarking

## Integration Tests

Place integration tests in `tests/` directory. Use environment variables for multi-process test coordination:

```rust
// tests/test_shm.rs
use project_core::shm::{ShmError, ShmRegion};
use std::io;
use std::process::Command;

#[test]
fn shm_multi_process_roundtrip() {
    // Child process path
    if std::env::var("TEST_SHM_CHILD").is_ok() {
        let name = std::env::var("TEST_SHM_NAME").unwrap();
        let size: usize = std::env::var("TEST_SHM_SIZE").unwrap().parse().unwrap();
        let region = ShmRegion::open_named(&name, size).unwrap();
        unsafe { assert_eq!(region.as_slice()[0], 42); }
        return;
    }

    // Parent process
    let name = format!("/test-shm-{}", std::process::id());
    let mut region = match ShmRegion::create_named(&name, 4096) {
        Ok(region) => region,
        Err(ShmError::Sys(err)) if err.kind() == io::ErrorKind::PermissionDenied => return,
        Err(err) => panic!("create_named failed: {err:?}"),
    };
    unsafe { region.as_mut_slice()[0] = 42; }

    let exe = std::env::current_exe().unwrap();
    let status = Command::new(&exe)
        .env("TEST_SHM_CHILD", "1")
        .env("TEST_SHM_NAME", &name)
        .env("TEST_SHM_SIZE", "4096")
        .arg("--exact")
        .arg("shm_multi_process_roundtrip")
        .arg("--nocapture")
        .status()
        .unwrap();
    assert!(status.success());
}
```

## Property-Based Testing with proptest

Use `proptest` for invariant testing:

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn long_names_are_rejected(len in 256usize..512) {
        let name = format!("/{}", "a".repeat(len));
        let err = ShmRegion::create_named(&name, 1024).unwrap_err();
        prop_assert!(matches!(err, ShmError::InvalidName | ShmError::Name(_)));
    }
}
```

## Criterion 0.5 Benchmarks

Define benchmarks in `benches/` with `harness = false`:

```toml
# Cargo.toml
[dev-dependencies]
criterion = { workspace = true }

[[bench]]
name = "spsc"
harness = false

[[bench]]
name = "codec"
harness = false
required-features = ["compression"]
```

Basic benchmark:

```rust
// benches/spsc.rs
use criterion::{criterion_group, criterion_main, Criterion};
use std::sync::Arc;
use project_core::buffer::{ChannelMode, RingLayout};
use project_core::channel::SpscRing;
use project_core::shm::ShmRegion;

fn bench_spsc_ping_pong(c: &mut Criterion) {
    let layout = RingLayout::new(256, 1024, ChannelMode::Spsc);
    let alloc = std::alloc::Layout::from_size_align(
        layout.total_size, 64,
    ).unwrap();
    let ptr = unsafe { std::alloc::alloc(alloc) };
    let region = Arc::new(unsafe { ShmRegion::from_raw(ptr, layout.total_size) });
    let ring = unsafe { SpscRing::initialize(Arc::clone(&region), layout, 0, 0).unwrap() };

    let payload = [7u8; 8];
    let mut out = [0u8; 8];

    c.bench_function("spsc_ping_pong", |b| {
        b.iter(|| {
            ring.send(&payload, 0).unwrap();
            let _ = ring.recv(&mut out).unwrap();
        })
    });

    unsafe { std::alloc::dealloc(ptr, alloc); }
}

criterion_group!(benches, bench_spsc_ping_pong);
criterion_main!(benches);
```

Parameterized benchmarks with `BenchmarkId`:

```rust
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};

fn bench_wakeup_latency(c: &mut Criterion) {
    let mut group = c.benchmark_group("recv_hybrid_wakeup");

    for delay_us in [10, 50, 100] {
        group.bench_with_input(
            BenchmarkId::from_parameter(delay_us),
            &delay_us,
            |b, &delay_us| {
                // setup ring, spawn sender with delay, measure recv latency
                b.iter(|| { /* ... */ });
            },
        );
    }
    group.finish();
}
```

## CI Matrix

Test across Python versions and platform features:

```yaml
# CI considerations
# - Python 3.12, 3.13, 3.14t (free-threaded)
# - Cross-platform: linux, macos, windows
# - Feature combinations: default, compression, free-threading
```

Build for testing with maturin:

```bash
# Development build (fast iteration)
maturin develop --uv --release

# With specific features
maturin develop --uv --release --features compression

# Run Rust tests
cargo test --workspace

# Run benchmarks
cargo bench --bench spsc
cargo bench --bench codec --features compression
```

## Additional Tools

- `cargo nextest run` for parallel test execution.
- `cargo +nightly miri test` for unsafe code verification.
- `cargo-llvm-cov` for coverage.
- Address sanitizer for binding layers:

```bash
RUSTFLAGS="-Zsanitizer=address" cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu
```
