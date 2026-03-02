# Plan-Mode Capability Matrix

This document defines how Flow planning commands (`flow-plan`, `flow-prd`) leverage native reasoning or plan modes across host adapters.

| Host | Native Mode Name | Invocation Pattern | Fallback Behavior |
|------|------------------|--------------------|-------------------|
| Claude Code | Plan Mode | Tool uses internal Claude plan features | Standard response |
| Gemini CLI | Plan Mode | `/plan` or `enter_plan_mode` tool | Standard reasoning |
| OpenCode | Reasoning Mode | Agent reasoning tools | Default model planning |
| Codex | Think/Plan Mode | Codex-specific thinking blocks | Standard text generation |
| Antigravity | Think/Plan Mode | Antigravity planning features | Standard text generation |

## Guidelines

- **Planning Commands:** All planning commands (e.g., `flow-plan`, `flow-prd`) MUST explicitly instruct the agent to use the host's native plan/reasoning mode before generating the artifact.
- **Safety First:** Plan mode ensures the model creates an exhaustive strategy before executing any mutations to the codebase.