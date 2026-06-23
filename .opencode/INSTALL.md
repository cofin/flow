# Installing Flow for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation Status

Flow ships OpenCode-compatible project files and Agent Skills. It does not advertise a global OpenCode install until Flow is published through OpenCode's npm plugin path.

### Project-local skills

OpenCode also discovers skills from `.agents/skills/`, `.claude/skills/`, and `.opencode/skills/`.
Use those project-local paths when you want Flow-related skills without a global plugin install.

### Restart

Restart OpenCode after updating project plugin files.

Verify by asking: `What is your Flow configuration?`

## Migrating from Legacy Install

If you previously installed Flow with older single-agent command files, remove them:

```bash
rm -f ~/.config/opencode/agents/flow.md
rm -f ~/.config/opencode/commands/flow-*.md
```

The plugin handles context injection. Flow's repo-local `.opencode/agents/*.md` files provide optional native subagents for harnesses that read project agent files.

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
