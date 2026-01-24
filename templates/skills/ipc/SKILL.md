---
name: ipc
description: Zero-copy IPC patterns for Vertebra (shared memory, ring buffers, buffer pools, cross-process sync, IPC transport abstraction). Use when implementing IPC primitives or cross-language message flow.
---

# IPC (Vertebra)

## Scope
- Shared memory regions, lock-free channels, buffer pools, sync primitives.
- Transport abstraction: UDS on Unix, named pipes (or TCP fallback) on Windows.

## Core Rules
- Keep data movement zero-copy where possible.
- Align headers and payloads; avoid false sharing.
- Separate control plane (small messages) from data plane (shared memory buffers).
- Use explicit versioning in shared memory headers.

## Safety + Correctness
- Validate bounds on every read/write.
- Enforce single-writer semantics where required (SPSC).
- Document ownership and lifecycle for all shared buffers.

## Portability
- Implement OS-specific backends behind a stable trait interface.
- Avoid Linux-only assumptions in public APIs.

## Testing
- Add multi-process tests (parent/child) for shared memory.
- Add property tests for FIFO/order and no-loss invariants.
