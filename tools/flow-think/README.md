# Flow Think MCP

A Model Context Protocol server providing structured thinking capabilities for the Flow Framework. Enables cascaded reasoning with step tracking, confidence scoring, revision support, and Beads integration.

## Features

- **Structured Reasoning Steps**: Track multi-step problem-solving with purpose, context, thought, outcome
- **Progress Tracking**: Step numbers with dynamic total estimates
- **Confidence Scoring**: 0-1 scale confidence with threshold warnings
- **Revision Support**: Mark steps as revising earlier steps with reasoning
- **Branching**: Explore alternative approaches from any step
- **Hypothesis Verification**: Track and verify hypotheses with status
- **Tool Integration**: Track tools used across reasoning chains
- **Multiple Output Formats**: Console (colored), JSON, and Markdown

## Installation

### Prerequisites

- [Bun](https://bun.sh) (recommended) or Node.js 18+
- Flow Framework (optional, for Beads integration)

### Quick Start

```bash
cd tools/flow-think
bun install
bun run start
```

### Build for Distribution

```bash
bun run build
```

This creates a `dist/` directory with compiled JavaScript.

## Usage

### MCP Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "flow-think": {
      "command": "bun",
      "args": ["run", "/path/to/flow/tools/flow-think/src/index.ts"]
    }
  }
}
```

Or using the built version:

```json
{
  "mcpServers": {
    "flow-think": {
      "command": "node",
      "args": ["/path/to/flow/tools/flow-think/dist/index.js"]
    }
  }
}
```

### Gemini CLI Integration

When installed via the Flow extension, the MCP server is automatically configured in `gemini-extension.json`. The tool is available as `mcp__flow-think__flow_think`.

**Extension Configuration** (in `gemini-extension.json`):

```json
{
  "mcpServers": {
    "flow-think": {
      "command": "node",
      "args": ["${extensionPath}${/}tools${/}flow-think${/}dist${/}index.js"],
      "cwd": "${extensionPath}",
      "env": {
        "FLOW_MCP_OUTPUT_FORMAT": "console",
        "FLOW_MCP_BEADS_SYNC": "true"
      }
    }
  }
}
```

**Gemini-Specific Considerations:**

1. **Path Variables**: Gemini CLI uses `${extensionPath}` to reference the extension installation directory and `${/}` as a cross-platform path separator
2. **Tool Naming**: In Gemini CLI, the tool is accessed as `mcp__flow-think__flow_think` (format: `mcp__<server>__<tool>`)
3. **Environment Variables**: Configure behavior via the `env` object in the MCP server config
4. **Trust Mode**: Unlike Claude Code, Gemini CLI MCP servers in extensions cannot use `trust: true` - all tool calls require confirmation unless globally disabled

**Manual Configuration** (in `~/.gemini/settings.json`):

```json
{
  "mcpServers": {
    "flow-think": {
      "command": "node",
      "args": ["/path/to/flow/tools/flow-think/dist/index.js"],
      "env": {
        "FLOW_MCP_OUTPUT_FORMAT": "console",
        "FLOW_MCP_BEADS_SYNC": "true"
      }
    }
  }
}
```

### Tool: `flow_think`

Record structured reasoning steps for complex problem-solving.

#### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `step_number` | integer | Sequential step number (starts at 1) |
| `estimated_total` | integer | Estimated total steps (adjust as needed) |
| `purpose` | string | Category: planning, research, implement, debug, analysis, validation, decision, exploration, reflection |
| `context` | string | What is already known or completed |
| `thought` | string | Your current reasoning process |
| `outcome` | string | Result or learning from this step |
| `next_action` | string or object | What you will do next |
| `rationale` | string | Why you chose this next action |

#### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | number | 0-1 scale confidence in this step |
| `uncertainty_notes` | string | Specific doubts or assumptions |
| `is_final_step` | boolean | Marks chain as complete |
| `revises_step` | integer | Step number being revised |
| `revision_reason` | string | Why revising earlier step |
| `branch_from` | integer | Step to branch from |
| `branch_id` | string | Unique branch identifier |
| `branch_name` | string | Human-readable branch name |
| `hypothesis` | string | Current hypothesis being tested |
| `verification_status` | enum | pending, confirmed, refuted |
| `tools_used` | string[] | Tools used in this step |
| `beads_task_id` | string | Linked Beads task ID |
| `flow_id` | string | Current Flow context |

#### Structured `next_action`

```json
{
  "tool": "Read",
  "action": "Read the config file",
  "parameters": { "path": "/config.json" },
  "expectedOutput": "Configuration settings"
}
```

### Example Workflow

```json
// Step 1: Planning
{
  "step_number": 1,
  "estimated_total": 3,
  "purpose": "planning",
  "context": "User reported login bug",
  "thought": "Need to understand the auth flow first",
  "outcome": "Will trace the login process",
  "next_action": { "tool": "Grep", "action": "Search for login handler" },
  "rationale": "Find entry point to understand flow"
}

// Step 2: Research with hypothesis
{
  "step_number": 2,
  "estimated_total": 3,
  "purpose": "debug",
  "context": "Found login handler in auth/login.ts",
  "thought": "Session token might be expiring too quickly",
  "outcome": "Found suspicious timeout value",
  "next_action": "Check token expiry logic",
  "rationale": "Token handling is most likely cause",
  "hypothesis": "Session timeout is incorrectly set",
  "verification_status": "pending",
  "confidence": 0.7
}

// Step 3: Final (verified)
{
  "step_number": 3,
  "estimated_total": 3,
  "purpose": "validation",
  "context": "Checked token expiry, found 10s timeout instead of 10m",
  "thought": "Confirmed the bug - missing zero in timeout",
  "outcome": "Root cause identified and fix ready",
  "next_action": "Apply fix and write test",
  "rationale": "Simple typo fix, will add test to prevent regression",
  "hypothesis": "Session timeout is incorrectly set",
  "verification_status": "confirmed",
  "confidence": 0.95,
  "is_final_step": true
}
```

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOW_MCP_OUTPUT_FORMAT` | console | Output format: console, json, markdown |
| `FLOW_MCP_MAX_HISTORY` | 100 | Maximum steps to retain (1-10000) |
| `FLOW_MCP_SESSION_TIMEOUT` | 60 | Session timeout in minutes (1-1440) |
| `FLOW_MCP_MAX_BRANCH_DEPTH` | 5 | Maximum branching depth (1-20) |
| `FLOW_MCP_BEADS_SYNC` | true | Enable Beads integration |
| `FLOW_MCP_LOW_CONFIDENCE` | 0.5 | Low confidence warning threshold |

## Development

### Run Tests

```bash
bun test
```

### Type Check

```bash
bun run typecheck
```

### Project Structure

```
src/
├── index.ts        # MCP server entry point
├── server.ts       # Core FlowThinkServer class
├── schema.ts       # MCP tool schema definition
├── formatter.ts    # Output formatting (console/JSON/markdown)
├── config.ts       # Configuration loading
├── types.ts        # TypeScript type definitions
└── *.test.ts       # Test files
```

## Response Format

The tool returns JSON responses:

```json
{
  "status": "flow_think_in_progress",
  "step_number": 2,
  "estimated_total": 3,
  "completed": false,
  "total_steps_recorded": 2,
  "next_action": "Continue implementation",
  "confidence": 0.85,
  "hypothesis": { "text": "...", "status": "pending" }
}
```

Status values:
- `flow_think_in_progress`: More steps expected
- `flow_think_complete`: Chain finished (is_final_step or completion phrase detected)

## Integration with Flow Framework

Flow Think integrates with the Flow Framework:

1. **Beads Sync**: Steps can link to Beads tasks via `beads_task_id`
2. **Flow Context**: Pass `flow_id` to associate steps with a Flow track
3. **Pattern Discovery**: Use `patterns_discovered` to capture learnings

## License

MIT
