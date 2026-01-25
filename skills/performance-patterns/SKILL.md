---
name: performance-patterns
description: General high-performance patterns for Python, generic IPC, and Serialization benchmarks.
---

# Performance Patterns Skill

## Benchmarking Methodology

- **Metrics**: Focus on p99 latency and throughput.
- **Warmup**: Always run warmup iterations before measurement to allow JIT/caching to stabilize.
- **Tools**:
  - **Python**: `time.perf_counter()` (high resolution), `rich` (for reporting).
  - **JS/TS**: `performance.now()`.
  - **Rust**: `criterion`.

## Serialization Strategies

### 1. Msgspec (Python)

- **Use Case**: General object serialization (structs, API payloads).
- **Why**: Significantly faster than standard `json` or `msgpack` libraries.
- **Pattern**: Define schemas using `msgspec.Struct` for maximum speed.

### 2. Apache Arrow

- **Use Case**: Large datasets, columnar data, zero-copy transport.
- **Why**: "Pure" serialization is effectively zero for IPC if using shared memory; fast batch processing.
- **Pattern**: Convert data to RecordBatches *before* the hot loop.

## IPC (Inter-Process Communication)

### 1. Shared Memory

- **Target**: < 10 µs latency.
- **Implementation**: Ring buffers in shared memory (e.g., `ShmRing`).
- **Advantage**: Avoids kernel context switches associated with pipes/sockets.

### 2. Zero-Copy

- **Concept**: Pass pointers/offsets to data in shared memory rather than copying bytes.
- **Requirement**: Data structures must be flat or serializable to contiguous memory (like Arrow).

## Profiling & Safety

- **Valgrind**: Use for memory leak detection in FFI/native extensions.
- **Sanitizers**: Use ThreadSanitizer (TSan) and AddressSanitizer (ASan) during development of native components.
