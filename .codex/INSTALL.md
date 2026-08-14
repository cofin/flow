# Installing Flow for Codex

Flow ships as a native Codex plugin via marketplace.

## Prerequisites

- Codex CLI 0.117.0+ (with marketplace support; verify with `codex --version`)

## Install

```bash
codex plugin marketplace add cofin/flow
```

In a Codex session, run `/plugins` and enable Flow.

## Update

```bash
codex plugin marketplace upgrade flow-marketplace
```

The marketplace catalog and the installed plugin cache are distinct. Restart
the Codex session after upgrading so the refreshed package is loaded.

## Uninstall

```bash
codex plugin marketplace remove flow-marketplace
```

## Usage

Codex plugins do not currently expose plugin-defined `/flow:*` slash commands. Use Flow through natural-language requests:

```
Use Flow to set up this project
Use Flow to create a PRD for user authentication
Use Flow to implement the current flow with TDD
```

The Flow skill routes the equivalent setup, planning, implementation, sync,
status, completion, and archive intents without advertising unavailable plugin
slash commands.

Repo-local subagents live in `.codex/agents/*.toml`. They are pure TOML, inherit tools from the active Codex session, and do not define a per-agent `tools` allowlist.

Codex's verified `request_user_input` transport supports binary and
single-select requests with 2-3 domain choices. Flow uses it only while the
tool is declared, allowed, and compatible; four-choice, multi-select, open, or
otherwise incompatible decisions use the equivalent sequential-text request.

Consumer operational skills resolve only from `.agents/skills/`. Continuity is
recovered by reading tracked Markdown, and the `flow-reconciler` applies state
transactions through ordinary file tools. The plugin installs no state runtime
service or Flow executable.

## Recommended Codex settings

In `~/.codex/config.toml`, set plan-mode reasoning effort high:

```toml
plan_mode_reasoning_effort = "high"
```
