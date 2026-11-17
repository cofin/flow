# Dynamic Cross-Harness Orchestration

Flow delegates model selection, slice decomposition, and verification planning to a shared Node engine under `sidecars/studio/` (`flow-cli.mjs`) rather than duplicating quota cliffs or model name lists across prompts.

## Dynamic `(model, effort)` Routing & Upward Delegation

- **Zero-Regex Capability Discovery (`sidecars/studio/models/inventory.mjs`)**: Probes native harness inventories (`agy`, `codex`, `claude`, `opencode`, `cursor-agent`, `vscode`, `/v1/models`) and merges stale-while-revalidate metadata from `https://models.dev/api.json` plus optional calibration overrides in `~/.config/flow/models.json` or `.agents/setup-state.json` (`model_routing`).
- **System-One Decision Engine (`sidecars/studio/models/routing.mjs`)**: Evaluates continuous `(model, effort)` pairs against task complexity, risk, quota remaining, and cooldown state using pluggable evaluators (`builtin`, remote `/v1/systemone`, `gemini-decision-1`, or local `onnx`).
- **Upward Frontier Floor**: Heavy cognitive tasks (`planning`, `semantic_validation`, `spec_review`, `committee`, `adversarial`, `diagnosis`) enforce a high capability floor (`>= 0.80`) across any available harness (`flow-cli.mjs harness delegate` or `flow_plan_frontier` / `flow_verify_frontier` MCP tools). If quota constraints force a lower-capability model for planning, Flow stamps `planning_quality: degraded` and `planning_degraded_reason` on `spec.md`.
- **Execution & Light Inspection**: Implementation micro-slices (`< 4k` tokens per `ContextPack`) route to balanced high-throughput tiers; narrow `<= 3`-file read-only lookups and mechanical status updates route to lightweight tiers or zero-token scripts.

## Micro-Sliced Context Packs & Wave Execution

1. **Plan Disjoint Micro-Slices**: Size tasks around `<= 250` estimated LOC and `<= 3` target files whenever boundaries permit (`flow-cli.mjs slices compile --flow <id> --chapter <ch> --packs`).
2. **Pre-Extracted `< 4k`-Token Context Packs**: Compile exact bounded `<= 120`-line symbol/file windows plus compact `<= 15`-line upstream change receipts so workers start implementing immediately without broad repository searches.
3. **Disjoint Waves & Zero-Token Inter-Wave Sync**: Dispatch up to `4` non-overlapping workers per wave (`small_swarm` on Antigravity; isolated subagents/worktrees elsewhere). Synchronize checklists and progress between waves deterministically via `flow-cli.mjs spec sync` (`0` LLM tokens) before running consolidated closeout verification once.

## Cross-Harness Execution Surfaces

- **Google Antigravity**: `AntigravityBridge` discovers workspaces and models, `mcp-server.mjs` exposes compact MCP tools (`flow_status`, `flow_preflight`, `flow_slice_pack`, `flow_sync`, `flow_plan_frontier`, `flow_verify_frontier`) and `ui://flow/studio`, and `hooks.json` registers lifecycle telemetry (`session-start`, `pre-invocation`, `pre-tool-guard`, `post-tool-telemetry`, `post-invocation`, `stop-check`).
- **Claude Code**: `mods/claude-flow/` injects dynamic `AbovePrompt` banners, hosts a `SidePane`, and rewrites `Agent` tool dispatches to the resolved `(model, effort)` profile with Context Pack injection; `hooks/pre-tool-guard.{sh,ps1}` provides a Claude-only `Agent` `updatedInput` fallback when the Mod is inactive (`CODEX_*` excluded).
- **Codex CLI**: `CodexAppServerBridge` communicates over `codex app-server` JSON-RPC using an isolated `CODEX_HOME` (never reading global auth caches), streaming `model/list`, `thread/start`, `thread/fork`, and turn controls.
- **OpenCode & VS Code / Cursor**: `.opencode/plugins/flow.js` binds dynamic models/variants inside `ctx.agent.transform` and exposes live slice hints in `ctx.session.hook("context")`; `vscode-extension/extension.mjs` ingests live `vscode.lm.selectChatModels({})` entries and materializes `.github/agents/flow-tier-*.agent.md`.
