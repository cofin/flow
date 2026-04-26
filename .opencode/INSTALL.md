# Installing Flow for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation

Flow should be installed as a local plugin file, not as a git URL in `opencode.json`.

### Global install

1. Clone Flow somewhere stable:

```bash
git clone https://github.com/cofin/flow.git ~/.config/opencode/flow
```

2. Link the plugin entrypoint into OpenCode's global plugin directory:

```bash
mkdir -p ~/.config/opencode/plugins
ln -sf ~/.config/opencode/flow/.opencode/plugins/flow.js ~/.config/opencode/plugins/flow.js
```

### Project-local skills

OpenCode also discovers skills from `.agents/skills/`, `.claude/skills/`, and `.opencode/skills/`.
Use those project-local paths when you want Flow-related skills without a global plugin install.

### Restart

Restart OpenCode after installing or updating plugin files.

Verify by asking: `What is your Flow configuration?`

## Migrating from Legacy Install

If you previously installed Flow with older single-agent command files, remove them:

```bash
rm -f ~/.config/opencode/agents/flow.md
rm -f ~/.config/opencode/commands/flow-*.md
```

The plugin handles context injection. Flow's repo-local `.opencode/agents/*.md` files provide optional native subagents for hosts that read project agent files.

## Updating

Update the cloned repo, then restart OpenCode:

```bash
git -C ~/.config/opencode/flow pull --ff-only
```

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
