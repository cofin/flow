# Flow Multi-Harness Conformance Matrix

Authoritative per-harness contract for what Flow ships and how each harness consumes it.

## Contract Table

| Harness | Tier | Manifest / Entry Point | Hooks | Agents | Commands |
|---|---|---|---|---|---|
| **Antigravity** | first-class | `plugin.json` | root `hooks.json` with `ANTIGRAVITY_PLUGIN_ROOT` / `AGY_PLUGIN_ROOT` / `PLUGIN_ROOT` root resolution | `agents/*.md` | skill-derived slash commands from `skills/`; `commands/flow/*.toml` remains shared source material |
| **Codex CLI** | first-class | `.codex-plugin/plugin.json`, generated package `plugins/flow/`, marketplace `.agents/plugins/marketplace.json` | `.codex/hooks.json`; generated package `hooks/hooks.json` emitted from `hooks/hooks-codex.json` | `.codex/agents/*.toml` | natural-language Flow skill requests |
| **Claude Code** | first-class | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `hooks/hooks-claude.json` referenced by plugin manifest | `agents/*.md` | `/flow-*` |
| **OpenCode** | compatible bundle | `.opencode/plugins/flow.js`, `.opencode/agents/*.md`, Agent Skills discovery | no static SessionStart hook | `.opencode/agents/*.md` | project command templates under `templates/opencode/commands/`; plugin context otherwise |
| **Cursor** | compatible bundle | `.cursor/rules/flow.mdc`, `AGENTS.md` | no stable repo plugin hook API | rules-based | n/a |
| **VS Code / Copilot** | compatible bundle | `.github/agents/*.agent.md`, Agent Skills discovery | n/a | `.github/agents/*.agent.md` | n/a |
| **OpenClaw** | compatible bundle | Agent Skills discovery and runtime `sessions_spawn` | n/a | runtime subagents | n/a |

## Invariants

- **Antigravity root manifests:** `plugin.json` and root `hooks.json` exist and pass `make validate-antigravity-manifest`.
- **Codex hook commands:** every Codex-consumed hook manifest anchors to `$PLUGIN_ROOT` or `$CLAUDE_PLUGIN_ROOT` and contains no shell-unsafe extension template tokens.
- **Claude hooks:** `.claude-plugin/plugin.json` points at `hooks/hooks-claude.json`; Claude hooks do not use extension template tokens.
- **Generated Codex package:** `plugins/flow/` is regenerated from source by `tools/sync-codex-package.py`, contains real files only, and rewrites package `hooks/hooks.json` to the Codex-native manifest.
- **No manual installs:** public install docs do not advertise clone, copy, or symlink install paths for Flow.
- **Command names are harness-specific:** do not promise identical slash-command spelling across Claude Code, Antigravity, OpenCode, and Codex.

## Deferred Hardening

- **OpenCode global install:** document a global install only after Flow is published through OpenCode's npm plugin path.
- **OpenCode command registration:** keep templates in-repo until the OpenCode plugin wires command config or a published package exposes them.
- **Cursor hooks:** keep Cursor rules-only until Cursor documents a stable repository plugin hook root token for this use case.
