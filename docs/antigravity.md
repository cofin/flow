# Installing Flow for Antigravity

Flow treats Antigravity as a first-class plugin harness.

## Shipped plugin files

| Asset | File | Purpose |
|---|---|---|
| Plugin manifest | `plugin.json` | Antigravity plugin identity and metadata |
| Hook manifest | `hooks/hooks-agy.json` | `PreInvocation` priming hook registration |
| Hook implementation | `hooks/agy-pre-invocation.sh` (+ `.ps1` twin) | Once-per-conversation OKF bundle context injection |
| Context generator | `hooks/detect-env.sh` (+ `.ps1` twin) | Renders project purpose, invariants, active flows, and skills from `.agents/bundles/` |
| Subagents | `agents/*.md` + `templates/antigravity/agents/flow-reconciler.md` | Flow lifecycle agents and the reconciler sidecar |
| Skills | `skills/**/SKILL.md` | Agent Skills-compatible Flow and technology skills |

## How priming works

Antigravity has **no SessionStart hook event** — its events are `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, and `Stop`. Flow therefore registers a `PreInvocation` hook. On the conversation's first model invocation it emits:

```json
{"injectSteps": [{"ephemeralMessage": "<project context markdown>"}]}
```

and on every later invocation an empty `injectSteps` array. Idempotence comes from the stdin payload's `invocationNum` plus a marker file keyed by `conversationId` under `artifactDirectoryPath`. The hook is pure shell (sh on POSIX, PowerShell on Windows), always exits 0, and stays well inside the default 30-second hook timeout.

The hook manifest uses Antigravity's named-hook format:

```json
{
  "flow-priming": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "bash \"${PLUGIN_ROOT:-${ANTIGRAVITY_PLUGIN_ROOT:-.}}/hooks/agy-pre-invocation.sh\"",
        "timeout": 25
      }
    ]
  }
}
```

## Install

Antigravity has two surfaces, installed differently:

- **Antigravity CLI**: install Flow through the CLI's extension/plugin installer — hooks, agents, and skills ship with the plugin; no manual file placement.
- **Antigravity IDE**: use the native Plugins & Skills installer for the `cofin/flow` repository. Do not install Flow by copying directories or creating symlinks.

Workspace-level pieces live in Antigravity's customization directory, which is `.agents/` — the same root Flow already uses:

- hook config (IDE/workspace): `.agents/hooks.json` (contents of `hooks/hooks-agy.json`), or globally at `~/.gemini/config/`; a nonstandard location can be set via `hooks_dir` in `.agents/config.json`
- subagents: `.agents/agents/<name>.md` (workspace) or `~/.gemini/config/agents/` (global)

Install the `flow-reconciler` sidecar from `templates/antigravity/agents/flow-reconciler.md` into `.agents/agents/` so `/flow:sync` and `/flow:status` work can run in a clean-context subagent instead of the main conversation.

After install or update, restart Antigravity so it reloads `plugin.json`, hooks, agents, and skills.

## Validate

```bash
make validate
```

The consolidated validator checks the Antigravity plugin manifest, the named-hook config (including that only real Antigravity events are registered and no hook command requires Python), and the shared agent surfaces.
