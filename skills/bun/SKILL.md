---
name: bun
description: "Usage of Bun as a high-performance JavaScript runtime, bundler, and test runner. Use when: running JS/TS code with Bun, using bun install, configuring Bun workspaces, or fixing low-latency node runtimes."
---

# Bun Skill

## Core Capabilities

### 1. Runtime

Bun is a drop-in replacement for Node.js, focused on speed.

- **HTTP Server**: `Bun.serve()` is faster than Node's `http` module.
- **File I/O**: `Bun.file()` and `Bun.write()` are optimized.
- **TypeScript**: Native support (no transpilation step needed for dev).

### 2. Task & Test Runner

- **Run Scripts**: `bun run script.ts` replaces `ts-node`.
- **Test**: `bun test` is a Jest-compatible, ultra-fast test runner.

    ```bash
    bun test --watch
    ```

- **Package Manager**: `bun install` is significantly faster than npm/yarn.

## High Performance & Integration Patterns (Vertebra)

This section details how to integrate Bun into high-performance, polyglot systems.

### 1. Inter-Process Communication (IPC)

When integrating with Rust/Python backends:

- **Shared Memory (ShmRing)**: For latency < 10µs, avoid piping JSON over stdout/stdin. Use shared memory ring buffers.
  - *Pattern*: Pointers/offsets only passed over socket; data stays in shared memory.
- **Unix Domain Sockets (UDS)**: Use `Bun.connect()` and `Bun.listen()` with abstract namespaces (Linux) or file paths (macOS) if Shm not available.
- **Serialization**:
  - Avoid `JSON.stringify` on hot paths.
  - Use **Msgspec** (via bindings) or **Apache Arrow** (via `apache-arrow` js package) for zero-copy structure sharing.

### 2. Native Bindings (FFI vs N-API)

- **N-API (`napi-rs`)**: Preferred for stability and complex logic. It maps Rust Structs to JS Classes easily.
- **Bun FFI (`bun:ffi`)**: faster for simple C function calls but harder to maintain for complex objects.
  - *Recommendation*: Use `napi-rs` for business logic, `bun:ffi` only for ultra-thin C wrappers.

### 3. Performance Gotchas

- **Buffer Copying**: Be careful with `Buffer` vs `Uint8Array`. Node compatibility layers might copy. Use `Uint8Array` natively where possible.
- **Streams**: `Bun.serve()` relies on `ReadableStream`. Buffering the entire request body (`await req.text()`) defeats the purpose of streaming; process chunks if possible.
- **Garbage Collection**: In tight loops, avoid allocating objects. Re-use objects or use typed arrays to keep pressure off the GC.

## Best Practices

- **Linting**: Use **Biome** (`bunx @biomejs/biome`) for instant linting/formatting.
- **Globals**: Use `Bun.env`, `Bun.sleep`, but generally avoid Node.js globals unless necessary for library compatibility.
- **Lockfile**: Commit `bun.lockb` for deterministic builds.

## Official References

- https://bun.sh/docs
- https://bun.sh/docs/test
- https://bun.sh/docs/install/lockfile
- https://bun.sh/docs/runtime/ffi
- https://bun.sh/docs/runtime/node-api
- https://github.com/oven-sh/bun/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
