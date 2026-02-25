---
name: performance-patterns
description: "High-performance patterns for Rust, Python, and polyglot systems: benchmarking with criterion, PGO, batch dispatch, serialization strategies, profiling, and cache optimization. Use when optimizing critical paths or establishing performance baselines."
---

# Performance Patterns

## Scope

- Benchmarking methodology (criterion, perf_counter, Benchmark.js).
- Profile-Guided Optimization (PGO) for Rust binaries.
- Batch dispatch and amortized overhead patterns.
- Serialization strategies (msgspec, Arrow, serde).
- Memory and cache optimization.
- Profiling and instrumentation.

## Benchmarking

### Rust: criterion

```rust
use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};

fn bench_ring_buffer(c: &mut Criterion) {
    let mut group = c.benchmark_group("ring_buffer");

    for size in [64, 256, 1024, 4096] {
        group.bench_with_input(
            BenchmarkId::new("push", size),
            &size,
            |b, &size| {
                let ring = SpscRing::new(65536);
                let data = vec![0u8; size];
                b.iter(|| ring.push(&data).unwrap());
            },
        );
    }
    group.finish();
}

criterion_group!(benches, bench_ring_buffer);
criterion_main!(benches);
```

**Rules:**
- Always use `BenchmarkId` for parameterized benchmarks.
- Enable `debug = true` in the bench profile for flamegraph symbols.
- Run `cargo bench -- --save-baseline before` before changes, then compare with `--baseline before`.

### Python: time.perf_counter

```python
import time
from statistics import median

def benchmark(fn, iterations=1000, warmup=100):
    # Warmup — stabilize JIT/caches
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        fn()
        times.append(time.perf_counter_ns() - start)

    times.sort()
    return {
        "p50": times[len(times) // 2],
        "p99": times[int(len(times) * 0.99)],
        "median": median(times),
    }
```

### Key Metrics

| Metric | Why |
|--------|-----|
| p50 latency | Typical user experience |
| p99 latency | Tail latency — where problems hide |
| Throughput (ops/sec) | Capacity planning |
| Memory high-water mark | Resource budgeting |

**Always measure p99, not just mean.** Mean hides outliers.

## Profile-Guided Optimization (PGO)

Three-step process for Rust binaries:

```bash
# 1. Instrument: build with profiling enabled
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" \
    cargo build --release --target x86_64-unknown-linux-gnu

# 2. Train: run representative workload
./target/x86_64-unknown-linux-gnu/release/my-server \
    --benchmark --duration 60

# 3. Optimize: rebuild with collected profiles
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/
RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" \
    cargo build --release --target x86_64-unknown-linux-gnu
```

**When to use PGO:**
- Server binaries with stable workload patterns.
- Expect 10-20% throughput improvement on hot paths.
- Not useful for libraries (the consumer's workload determines hot paths).

## Batch Dispatch

Amortize per-call overhead by batching operations:

```rust
// Bad: one Python→Rust crossing per item
for item in items:
    result = engine.process(item)

// Good: single crossing, Rust loops internally
results = engine.process_batch(items)
```

### Rust Implementation

```rust
#[pymethods]
impl Engine {
    fn process_batch(&self, py: Python<'_>, items: Vec<Vec<u8>>) -> PyResult<Vec<Vec<u8>>> {
        py.allow_threads(|| {
            items.into_par_iter()  // Rayon for parallel processing
                .map(|item| self.inner.process(&item))
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))
        })
    }
}
```

**Impact:** Reduces FFI overhead from O(n) to O(1). Critical when processing >1000 items.

## Serialization Strategies

| Format | Latency | Use Case |
|--------|---------|----------|
| Zero-copy (shared memory) | ~0 | Same-machine IPC, large buffers |
| Apache Arrow | < 1 us | Columnar data, cross-language |
| msgspec (Python) | 5-10x faster than json | API payloads, structs |
| serde + bincode (Rust) | ~ 100 ns | Rust-to-Rust, compact binary |
| serde + JSON | ~ 1 us | Debug, HTTP APIs |
| protobuf | ~ 500 ns | Cross-language RPC, schema evolution |

### msgspec (Python)

```python
import msgspec

class Event(msgspec.Struct):
    timestamp: float
    kind: str
    data: bytes

encoder = msgspec.json.Encoder()
decoder = msgspec.json.Decoder(Event)

# 5-10x faster than json.dumps/loads
encoded = encoder.encode(event)
decoded = decoder.decode(encoded)
```

### Arrow (Cross-Language Zero-Copy)

```python
import pyarrow as pa

# Convert to RecordBatch ONCE, outside the hot loop
batch = pa.RecordBatch.from_pydict({
    "id": pa.array([1, 2, 3]),
    "value": pa.array([1.0, 2.0, 3.0]),
})

# IPC: shared memory transfer with zero serialization cost
buf = batch.serialize()  # Contiguous memory
```

## Cache Optimization

### Cache-Line Alignment

```rust
#[repr(C, align(64))]
struct HotData {
    counter: AtomicU64,
    // Pad to fill cache line — prevents false sharing
    _pad: [u8; 56],
}
```

### Data Layout

- **AoS vs SoA:** Use Struct-of-Arrays for batch processing (better cache utilization).
- **Hot/cold split:** Separate frequently-accessed fields from rarely-used metadata.

```rust
// Hot path: packed, cache-friendly
struct PacketHeader {
    seq: u64,
    len: u32,
    flags: u16,
}

// Cold path: separate allocation
struct PacketMetadata {
    source: String,
    timestamp: Instant,
    tags: Vec<String>,
}
```

## Profiling

### Rust

| Tool | Purpose |
|------|---------|
| `cargo flamegraph` | CPU flame graphs |
| `perf stat` | Hardware counters (cache misses, branch mispredictions) |
| `cargo-llvm-cov` | Code coverage |
| `heaptrack` | Allocation profiling |
| DHAT (`valgrind --tool=dhat`) | Heap analysis |

### Python

| Tool | Purpose |
|------|---------|
| `py-spy` | Sampling profiler (no instrumentation overhead) |
| `tracemalloc` | Memory allocation tracking |
| `scalene` | CPU + memory + GPU profiler |
| `line_profiler` | Line-by-line timing |

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
| Copying across FFI per-item | O(n) crossing overhead | Batch dispatch |
| `SeqCst` everywhere | Unnecessary memory barriers | Use weakest sufficient ordering |
| Allocating in hot loops | GC/allocator pressure | Pre-allocate, reuse buffers |
| Mean-only benchmarks | Hides tail latency | Always report p99 |

## Conventions

- Establish baselines before optimizing — record in project docs.
- Use `#[bench]` or criterion, never `Instant::now()` in production benchmarks.
- Profile in release mode (`--release`) with debug symbols (`debug = true`).
- Document performance targets in specs (latency, throughput, memory).
- Re-benchmark after dependency updates — regressions hide in minor versions.
