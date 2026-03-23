# Installing Flow for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation

Add flow to the `plugin` array in your `opencode.json` (global or project-level):

```json
{
  "plugin": ["flow@git+https://github.com/cofin/flow.git"]
}
```

Restart OpenCode. That's it — the plugin auto-installs and registers all Flow skills and commands.

Verify by asking: "What is your Flow configuration?"

## Usage

Use OpenCode's native `skill` tool:

```
use skill tool to list skills
use skill tool to load flow/prd
```

## Updating

Flow updates automatically when you restart OpenCode.

## Tool Mapping

When skills reference Claude Code tools:
- `TodoWrite` → `todowrite`
- `Task` with subagents → Use OpenCode's subagent system (@mention)
- `Skill` tool → OpenCode's native `skill` tool
- File operations → your native tools
