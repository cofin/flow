---
name: bun
description: "Bun runtime development for Vertebra: HTTP server, MCP server, IPC bridge, and Bun-only drivers. Use when writing TypeScript for Bun server components or runtime integration."
---

# Bun (Vertebra)

## Scope
- `src/js/src/server` (HTTP/WS), `src/js/src/mcp`, IPC client/bridge.

## Core Rules
- Use `Bun.serve()` and `ServerWebSocket` APIs.
- Prefer Bun-native APIs; avoid Node-only globals unless gated.
- Implement IPC transport abstraction (UDS on Unix, named pipes/TCP on Windows).
- Keep drivers **Bun-only**; raise explicit errors under Node.

## Performance
- Stream large payloads; avoid buffering whole responses.
- Reuse IPC connections; avoid per-request connects.

## Error Handling
- Normalize errors from Rust bindings into structured JS errors.
- Fail fast when Bun runtime is unavailable.
