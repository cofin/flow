# Installing Flow for Codex

Flow ships as a native Codex plugin via marketplace.

## Prerequisites

- Codex CLI 0.117.0+ (with marketplace support; verify with `codex --version`)
- [Beads CLI](https://github.com/gastownhall/beads)

## Install

```bash
codex plugin marketplace add cofin/flow
```

In a Codex session, run `/plugins` and enable Flow.

## Update

```bash
codex plugin marketplace upgrade flow-marketplace
```

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

The Flow skill responds to all `/flow:*` intents (`setup`, `prd`, `plan`, `implement`, `sync`, `status`, `refresh`, `research`, `docs`, etc.).

Repo-local subagents live in `.codex/agents/*.toml`. They are pure TOML, inherit tools from the active Codex session, and do not define a per-agent `tools` allowlist.

## Recommended Codex settings

In `~/.codex/config.toml`, set plan-mode reasoning effort high:

```toml
plan_mode_reasoning_effort = "high"
```

## Migrating from older pre-marketplace installs

If you previously installed Flow via symlinks under `~/.codex/prompts/` or `~/.codex/skills/`, remove the old artifacts before running the marketplace install:

```bash
rm -f ~/.codex/prompts/flow-*.md
rm -rf ~/.codex/skills/flow ~/.codex/skills/beads
sed -i '/^# Flow Framework/,$d' ~/.codex/AGENTS.md 2>/dev/null
```
