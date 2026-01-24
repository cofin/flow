---
name: napi-rs
description: "napi-rs bindings for Vertebra: Node/Bun native modules, async tasks, TSFN, buffer mapping, and error conversion. Use when exposing Rust IPC to JS."
---

# napi-rs (Vertebra)

## Core Rules
- Use `#[napi]` with `napi::bindgen_prelude` types.
- Map Rust errors to JS exceptions deterministically.
- Avoid blocking the JS thread; use async tasks or TSFN for callbacks.
- Use zero-copy buffers only with safe lifetime management.

## Bun Compatibility
- Target Node-API; avoid Node-only APIs.
- Keep surface small and stable to reduce ABI risk.
