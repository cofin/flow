# Installing Flow for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation

Add Flow to the `plugin` array in your `opencode.json` (global at `~/.config/opencode/opencode.json` or project-level):

```json
{
  "plugin": ["flow@git+https://github.com/cofin/flow.git"]
}
```

Restart OpenCode. The plugin auto-installs, registers all Flow skills and commands, and injects Flow context at session start.

Verify by asking: "What is your Flow configuration?"

## Migrating from Legacy Install

If you previously installed Flow with manual agent/command files, remove them:

```bash
rm -f ~/.config/opencode/agents/flow.md
rm -f ~/.config/opencode/commands/flow-*.md
```

The plugin handles everything — no separate agent or command files needed.

## Updating

Flow updates automatically when you restart OpenCode (fetches latest from git).

## Usage

Use OpenCode's native skill system:

```
/flow:setup    — Initialize project
/flow:prd      — Create feature roadmap
/flow:plan     — Plan single flow
/flow:implement — Execute tasks (TDD)
/flow:sync     — Sync Beads to spec
/flow:status   — Show progress
/flow:refresh  — Refresh context from codebase
```

## Tool Mapping

When Flow skills reference Claude Code tools:

| Claude Code | OpenCode |
|-------------|----------|
| `Skill` tool | Native `skill` tool |
| `Agent` with subagents | `@mention` subagent system |
| `TodoWrite` / `TaskCreate` | `todowrite` |
| `Read`, `Write`, `Edit` | Same names |
| `Bash` | `bash` |
| `Glob`, `Grep` | Same names |
