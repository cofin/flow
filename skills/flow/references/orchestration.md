# Model Routing and Parallel Workers

Flow delegates model selection, task planning, and verification planning to a shared Node engine under `sidecars/studio/` (`flow-cli.mjs`) instead of duplicating quota rules or model lists across prompts.

## Model Routing & Strongest-Model Floor

- **Capability Discovery (`sidecars/studio/models/inventory.mjs`)**: Probes native harness inventories (`agy`, `codex`, `claude`, `opencode`, `cursor-agent`, `vscode`, `/v1/models`) and merges metadata from `https://models.dev/api.json` plus optional overrides in `~/.config/flow/models.json` or `.agents/setup-state.json` (`model_routing`).
- **Model Picker (`sidecars/studio/models/routing.mjs`)**: Evaluates `(model, effort)` pairs against task complexity, risk, quota remaining, and cooldown state using the built-in evaluator (`builtin`) or a configurable `remote-http` `decision_endpoint`.
- **Planning and Review Use the Strongest Model**: Heavy tasks (`planning`, `semantic_validation`, `spec_review`, `committee`, `adversarial`, `diagnosis`) enforce a high capability floor (`>= 0.80`) via `flow-cli.mjs harness delegate` or the `flow_plan_strong` / `flow_verify_strong` MCP tools.
- **Degraded Planning Disclosure**: If quota constraints force a lower-capability model for planning, Flow stamps `planning_quality: degraded` and `planning_degraded_reason` on `spec.md`.
- **Model Roles**: Roles are `strong`, `standard`, `fast`, and `light`. Implementation tasks route to `standard` or `fast`; narrow `<= 3`-file read-only lookups and mechanical status updates route to `light` or CLI scripts.

## Task Briefs & Parallel Step Execution

1. **Plan Separate-File Tasks**: Size tasks around `<= 250` estimated LOC and `<= 3` target files whenever boundaries permit, using `flow-cli.mjs tasks plan --briefs --flow <id> --chapter <ch>`.
2. **Pre-Extracted `< 4k`-Token Briefs**: Build `<= 120`-line symbol/file excerpts plus `<= 15`-line upstream change summaries so workers start implementing without broad repository searches.
3. **Parallel Steps & CLI Sync**: Dispatch up to `4` workers (`workers`, `tasks_per_worker`, `parallel_tasks`) editing separate files in each step (`small_swarm` on Antigravity; isolated subagents or worktrees elsewhere).
4. **Sync Between Steps**: Run `flow-cli.mjs spec sync` to update checklists and progress between steps, then run consolidated closeout verification once.

## Cross-Harness Execution Surfaces

- **Google Antigravity**: `AntigravityBridge` discovers workspaces and models, `mcp-server.mjs` exposes MCP tools (`flow_status`, `flow_preflight`, `flow_tasks`, `flow_sync`, `flow_plan_strong`, `flow_verify_strong`) and `ui://flow/studio`, and `hooks.json` registers lifecycle hooks (`session-start`, `pre-invocation`, `pre-tool-guard`, `post-tool-telemetry`, `post-invocation`, `stop-check`, controlled by `stop_check` / `FLOW_STOP_CHECK`).
- **Claude Code**: `mods/claude-flow/` injects `AbovePrompt` banners, hosts a `SidePane`, and rewrites `Agent` tool dispatches to the resolved `(model, effort)` profile with brief injection; `hooks/pre-tool-guard.{sh,ps1}` provides a Claude-only `Agent` `updatedInput` fallback when the Mod is inactive (`CODEX_*` excluded).
- **Codex CLI**: `CodexAppServerBridge` communicates over `codex app-server` JSON-RPC using an isolated `CODEX_HOME` (never reading global auth caches), streaming `model/list`, `thread/start`, `thread/fork`, and turn controls.
- **OpenCode & VS Code / Cursor**: `.opencode/plugins/flow.js` binds models and variants inside `ctx.agent.transform` and exposes live task hints in `ctx.session.hook("context")`; `vscode-extension/extension.mjs` ingests `vscode.lm.selectChatModels({})` entries and writes `.github/agents/flow-model-*.agent.md`.
