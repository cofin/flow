---
name: bun
description: Usage of Bun as a high-performance JavaScript runtime, bundler, and test runner, with specific focus on native integration and low-latency patterns.
---

# Bun Skill

## Core Capabilities

### 1. Runtime

Bun is a fast JavaScript/TypeScript runtime designed to be largely drop-in for Node.js projects, with compatibility still actively improving.

- **HTTP Server**: `Bun.serve()` is a built-in server API for high-throughput services.
- **File I/O**: `Bun.file()` and `Bun.write()` are optimized and recommended for common file operations.
- **TypeScript**: Native support (no transpilation step needed for dev).

### 2. Task & Test Runner

- **Run Scripts**: `bun run script.ts` replaces `ts-node`.
- **Test**: `bun test` is a Jest-compatible, TypeScript-first test runner.

    ```bash
    bun test --watch
    ```

- **Package Manager**: `bun install` is Bun’s npm-compatible package manager with workspaces and lockfile support.

## High Performance & Integration Patterns (Vertebra)

This section details how to integrate Bun into high-performance, polyglot systems.

### 1. Inter-Process Communication (IPC)

When integrating with Rust/Python backends:

- **Shared Memory (ShmRing)**: Prefer shared memory ring buffers for high-throughput/low-latency local IPC instead of JSON over stdio on hot paths.
  - *Pattern*: Pointers/offsets only passed over socket; data stays in shared memory.
- **Sockets**: Use `Bun.connect()` / `Bun.listen()` (TCP) and Unix sockets where appropriate if shared memory is not available.
- **Serialization**:
  - Avoid `JSON.stringify` on hot paths.
  - Prefer binary formats and typed arrays for predictable allocations and lower overhead.

### 2. Native Bindings (FFI vs N-API)

- **N-API (`napi-rs`)**: Preferred for stability and complex logic. It maps Rust Structs to JS Classes easily.
- **Bun FFI (`bun:ffi`)**: Useful for direct C ABI calls, but Bun marks it as experimental.
  - *Recommendation*: Default to N-API for production/stable native modules; use `bun:ffi` for narrow, carefully scoped interop.

### 3. Performance Gotchas

- **Buffer Copying**: Be careful with `Buffer` vs `Uint8Array`. Node compatibility layers might copy. Use `Uint8Array` natively where possible.
- **Streams**: `Bun.serve()` relies on `ReadableStream`. Buffering the entire request body (`await req.text()`) defeats the purpose of streaming; process chunks if possible.
- **Garbage Collection**: In tight loops, avoid allocating objects. Re-use objects or use typed arrays to keep pressure off the GC.

## Best Practices

- **Linting**: Use **Biome** (`bunx @biomejs/biome`) for instant linting/formatting.
- **Globals**: Use `Bun.env`, `Bun.sleep`, but generally avoid Node.js globals unless necessary for library compatibility.
- **Lockfile**: Commit `bun.lock` for deterministic builds.

## Where to Find More Information (Official)

- Start here: https://bun.sh/docs
- Runtime overview (`bun run`, watch/hot mode): https://bun.sh/docs/cli/run
- Test runner (`bun test`): https://bun.sh/docs/cli/test
- Package manager + lockfiles (`bun.lock`): https://bun.sh/docs/install/lockfile
- Node compatibility status: https://bun.sh/docs/runtime/nodejs-apis
- Native modules (Node-API): https://bun.sh/docs/api/node-api
- FFI (`bun:ffi`, experimental): https://bun.sh/docs/runtime/ffi
- TCP sockets (`Bun.listen`, `Bun.connect`): https://bun.sh/docs/api/tcp
- Releases/changelog: https://github.com/oven-sh/bun/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
