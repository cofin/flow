---
name: performance-patterns
description: "Practical performance patterns for Rust, Python, and polyglot systems: benchmark design, PGO, batching across boundaries, serialization choices, profiling, and cache-aware data layout."
---

# Performance Patterns

## Scope

- Benchmark methodology for Rust and Python.
- Profile-Guided Optimization (PGO) for Rust binaries.
- Batch dispatch across FFI/process boundaries.
- Serialization strategy selection (msgspec, Arrow IPC, serde).
- Cache/memory-aware data layout.
- Profiling workflow and anti-patterns.

## Measure First

- Optimize only verified hot paths.
- Track at least `p50`, `p99`, throughput, and peak memory.
- Compare against a saved baseline, not memory.

## Benchmarking

### Rust: criterion

```rust
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};

fn bench_ring_buffer(c: &mut Criterion) {
    let mut group = c.benchmark_group("ring_buffer");

    for size in [64, 256, 1024, 4096] {
        group.bench_with_input(BenchmarkId::new("push", size), &size, |b, &size| {
            let ring = SpscRing::new(65536);
            let data = vec![0u8; size];
            b.iter(|| ring.push(&data).unwrap());
        });
    }

    group.finish();
}

criterion_group!(benches, bench_ring_buffer);
criterion_main!(benches);
```

Rules:
- Use `BenchmarkId` for parameterized benchmarks.
- Use release builds with symbols when profiling (`[profile.bench] debug = true`).
- Save and compare baselines:
  - `cargo bench -- --save-baseline before`
  - `cargo bench -- --baseline before`

### Python: `perf_counter_ns` for custom loops

```python
import time


def benchmark(fn, iterations=1000, warmup=100):
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        fn()
        times.append(time.perf_counter_ns() - start)

    times.sort()
    return {
        "p50_ns": times[len(times) // 2],
        "p99_ns": times[int(len(times) * 0.99)],
    }
```

For microbenchmarks, prefer `python -m timeit` for a repeatable harness.

## Profile-Guided Optimization (PGO)

Three-step flow for Rust binaries:

```bash
# 1) Instrumented build
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" \
  cargo build --release --target x86_64-unknown-linux-gnu

# 2) Run representative training workload
./target/x86_64-unknown-linux-gnu/release/my-server \
  --benchmark --duration 60

# 3) Merge + optimized rebuild
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/
RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" \
  cargo build --release --target x86_64-unknown-linux-gnu
```

Use when:
- Workload is stable and representative.
- CPU hot paths are confirmed by profiling.

Avoid fixed speedup promises; gains are workload-dependent.

## Batch Dispatch

Amortize boundary overhead by batching work:

```rust
// Bad: one Python→Rust crossing per item
for item in items:
    result = engine.process(item)

// Good: one crossing, native side loops
results = engine.process_batch(items)
```

PyO3 note: newer versions renamed `allow_threads` to `detach`; align examples with your pinned PyO3 version.

## Serialization Strategies

| Format | Best for |
|--------|----------|
| Shared memory / zero-copy views | Same-machine large buffers |
| Arrow IPC | Columnar cross-language transfer |
| msgspec (JSON/MessagePack) | High-throughput Python APIs/messages |
| serde + bincode/postcard | Rust-to-Rust compact payloads |
| JSON | Interop and debuggability |
| Protobuf | Cross-language schema evolution |

### msgspec (Python)

```python
import msgspec

class Event(msgspec.Struct):
    timestamp: float
    kind: str
    data: bytes

encoder = msgspec.json.Encoder()
decoder = msgspec.json.Decoder(Event)

encoded = encoder.encode(event)
decoded = decoder.decode(encoded)
```

### Arrow IPC (cross-language)

```python
import pyarrow as pa

batch = pa.RecordBatch.from_pydict({
    "id": pa.array([1, 2, 3]),
    "value": pa.array([1.0, 2.0, 3.0]),
})

buf = batch.serialize()
```

For streams/files, prefer Arrow IPC readers/writers (`new_stream` / `new_file`).

## Cache Optimization

### Cache-Line Alignment

```rust
#[repr(C, align(64))]
struct HotData {
    counter: AtomicU64,
    _pad: [u8; 56],
}
```

### Data Layout

- AoS vs SoA: favor SoA for scan-heavy/vectorized paths.
- Hot/cold split: isolate rarely-used metadata from hot structs.

## Profiling

### Rust

| Tool | Purpose |
|------|---------|
| `cargo flamegraph` | CPU flame graphs |
| `perf stat` | Hardware counters |
| `heaptrack` | Allocation profiling |
| DHAT (`valgrind --tool=dhat`) | Heap analysis |

### Python

| Tool | Purpose |
|------|---------|
| `py-spy` | Sampling profiler |
| `tracemalloc` | Allocation tracking |
| `scalene` | CPU + memory + GPU profiler |
| `line_profiler` | Line-level hotspots |

### System

| Tool | Purpose |
|------|---------|
| `perf record` + `perf report` | System-wide profiling |
| `strace -c` | Syscall frequency analysis |
| `bpftrace` | Dynamic kernel tracing |

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Optimizing without measuring | Wasted effort on cold paths | Profile first, optimize hot paths |
| Per-item FFI/process crossing | Excess boundary overhead | Batch dispatch |
| `SeqCst` everywhere | Unnecessary memory barriers | Use weakest sufficient ordering |
| Allocating in hot loops | GC/allocator pressure | Pre-allocate, reuse buffers |
| Mean-only benchmarks | Hides tail latency | Report p99 |

## Conventions

- Establish baselines before optimization and record them.
- Prefer Criterion on stable Rust; `#[bench]` is nightly-only.
- Profile in release mode with symbols.
- Document targets in specs (latency, throughput, memory).
- Re-benchmark after dependency/runtime upgrades.

## Learn More (Official)

- Criterion.rs command-line + baselines:
  - https://bheisler.github.io/criterion.rs/book/user_guide/command_line_options.html
- Rust PGO (`rustc` book):
  - https://doc.rust-lang.org/rustc/profile-guided-optimization.html
- Cargo benchmarks (`#[bench]` nightly note):
  - https://doc.rust-lang.org/cargo/commands/cargo-bench.html
- Python timing (`perf_counter_ns`, `timeit`):
  - https://docs.python.org/3/library/time.html#time.perf_counter_ns
  - https://docs.python.org/3/library/timeit.html
- PyO3 migration guide:
  - https://pyo3.rs/latest/migration.html
- Arrow IPC + RecordBatch API:
  - https://arrow.apache.org/docs/python/ipc.html
  - https://arrow.apache.org/docs/python/generated/pyarrow.RecordBatch.html
- msgspec docs:
  - https://jcristharif.com/msgspec/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
