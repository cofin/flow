# Multi-Harness Plugin Patterns

Reference for Flow-family repositories that ship skills, commands, hooks, or agents across Antigravity, Codex CLI, Claude Code, OpenCode, Cursor, VS Code / Copilot, and OpenClaw.

## What To Ship

| File | Harness | Purpose |
|---|---|---|
| `plugin.json` | Antigravity | Plugin identity and metadata |
| `hooks.json` | Antigravity | Root hook manifest |
| `.claude-plugin/marketplace.json` | Claude Code | Marketplace catalog |
| `.claude-plugin/plugin.json` | Claude Code | Plugin manifest for skills, commands, hooks, and user config |
| `.agents/plugins/marketplace.json` | Codex CLI | Marketplace catalog |
| `.codex-plugin/plugin.json` | Codex CLI | Plugin manifest |
| `plugins/<name>/` | Codex CLI | Generated package payload with real files only |
| `.codex/agents/*.toml` | Codex CLI | TOML subagents that inherit session tools |
| `agents/*.md` | Antigravity / Claude Code | Shared Markdown subagents |
| `.opencode/plugins/<name>.js` | OpenCode | Project-compatible plugin entrypoint |
| `.opencode/agents/*.md` | OpenCode | Native subagents with `permission:` object |
| `.cursor/rules/*.mdc` | Cursor | Rules and project instructions |
| `.github/agents/*.agent.md` | VS Code / Copilot | Workspace custom agents |

## Install Pattern

Use the harness's primary mechanism:

- Antigravity: native Plugins & Skills installer for the repository.
- Claude Code: `claude plugin marketplace add <owner>/<repo>` followed by `claude plugin install <plugin>@<marketplace>`.
- Codex CLI: `codex plugin marketplace add <owner>/<repo>` and enable through `/plugins`.
- Cursor, VS Code / Copilot, and OpenClaw: supported rules, custom agents, and Agent Skills discovery.
- OpenCode: project-compatible files or npm plugin package. Do not document a symlink install as the primary path.

Do not ship a repository-specific multi-harness installer as the public installation path. Do not tell users to install shared plugin code by copying, cloning into a hidden directory, or creating symlinks.

## Hook Pattern

- Antigravity root `hooks.json` should resolve the plugin root from `ANTIGRAVITY_PLUGIN_ROOT`, `AGY_PLUGIN_ROOT`, or `PLUGIN_ROOT`.
- Codex package `hooks/hooks.json` must be generated from the Codex-native source manifest and use `$PLUGIN_ROOT`.
- Claude hooks should use `${CLAUDE_PLUGIN_ROOT}` and be referenced explicitly by `.claude-plugin/plugin.json`.
- Shell-unsafe extension template tokens are forbidden in Codex and Antigravity hook commands.

## Validation Pattern

Use separate validators for separate harness contracts:

- `tools/validate.py` (consolidated validator for all harness manifests, skills, commands, agents, and OKF bundles)

Keep generated package checks in the aggregate `make check` path so stale Codex payloads cannot be committed accidentally.
