# Installing Flow for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation Status

Flow ships OpenCode-compatible project files and Agent Skills. It does not advertise a global OpenCode install until Flow is published through OpenCode's npm plugin path.

### Project-local skills

OpenCode also discovers skills from `.agents/skills/`, `.claude/skills/`, and `.opencode/skills/`.
Flow consumer projects use `.agents/skills/` as the sole operational
project-skill authority; the other roots are harness discovery locations, not
Flow's project-state authority.

### Project commands

The `/flow-*` commands require project command files generated from
`templates/opencode/commands/`. Install those templates through a supported
OpenCode project configuration. Without them, use the discovered Flow skill or
plugin context in natural language.

### Restart

Restart OpenCode after updating project plugin files.

Verify by asking: `What is your Flow configuration?`

The plugin handles context injection. Flow's repo-local `.opencode/agents/*.md` files provide optional native subagents for harnesses that read project agent files.

## Usage

Use OpenCode's native skill system:

```
/flow-setup     — Initialize project
/flow-prd       — Create feature roadmap
/flow-plan      — Plan single flow
/flow-implement — Execute tasks
/flow-sync      — Reconcile spec checklist with task files
/flow-status    — Show progress
/flow-refresh   — Refresh context from codebase
```

OpenCode's verified `question` tool supports Flow binary, single-select, and
multi-select decisions with 2-4 domain choices. Flow uses it only when declared,
allowed, and compatible; otherwise it renders the same request sequentially in
text. State and recovery always use direct Markdown reads plus ordinary file
tools, with no consumer state runtime.

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
