# Hooks & Runtime Portability

Design runtime hooks that execute reliably across Linux, macOS, and Windows without assuming `python3`, `node`, or `jq` are installed on the host machine.

## Runtime Environment Reality Across Harnesses

| Harness | Host Binary Type | Guaranteed Runtime Dependencies |
| --- | --- | --- |
| **Google Antigravity (`agy`)** | Compiled native binary | POSIX `sh`, `awk`, `git` (no bundled Python or Node.js) |
| **Codex CLI (`codex`)** | Compiled Rust binary | POSIX `sh`, `awk`, `git` (no bundled Python or Node.js) |
| **Claude Code (`claude`)** | Bun / Node binary | POSIX `sh`, `awk`, `git` |
| **Cursor (`cursor`)** | Electron IDE | POSIX `sh`, `awk`, `git` |
| **VS Code (`code`)** | Electron IDE | POSIX `sh`, `awk`, `git` |
| **OpenCode V2 (`opencode`)** | Bun / Node runtime | In-process `node:fs` and `node:path` inside `.opencode/plugins/<name>.js` |

Reserve Python (`pyproject.toml`, `uv run`) strictly for plugin repository development and CI (`Makefile`, `tools/validate.py`, `pytest`), or when shipping an explicit Python MCP server launched via `uv run`.

## Harness Hook Configurations (Plugin & Project-Local)

### 1. Google Antigravity (`hooks.json` at Plugin Root or `.agents/hooks.json` in Project)

Antigravity requires **flat** handler arrays for lifecycle events (`SessionStart`, `PreInvocation`, `PostInvocation`, `Stop`) and **nested** `matcher` arrays only for tool events (`PreToolUse`, `PostToolUse`). Nesting `SessionStart` under `{ "matcher": "*", "hooks": [...] }` causes `ParseHooks` to fail and drop the entire `hooks.json` file.

Also note that for global plugins, Antigravity sets `cmd.Dir` to the **installed plugin directory** (not the user's workspace) and passes the active workspace inside stdin JSON (`workspacePaths[0]`):

```json
{
  "flow-session-start": {
    "SessionStart": [
      {
        "type": "command",
        "command": "sh ./hooks/session-start.sh --harness agy",
        "timeout": 15
      }
    ]
  }
}
```

### 2. Claude Code, Codex CLI, & VS Code (`hooks/hooks-claude.json` or `.claude/settings.json` / `.codex/hooks.json`)

Claude Code and Codex CLI require the **nested** `matcher` structure for all events:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh --harness claude"
          }
        ]
      }
    ]
  }
}
```

- In **Claude Code**, `hooks/hooks.json` auto-loads and merges with any file declared in `.claude-plugin/plugin.json` `hooks`. Point `.claude-plugin/plugin.json` at `./hooks/hooks-claude.json` and keep root `hooks.json` for Antigravity so neither harness collides.
- In **Codex CLI**, project-local `.codex/hooks.json` (or inline `[hooks]` in `.codex/config.toml`) only runs for trusted projects, and plugin hooks require user trust approval on install/upgrade.

### 3. Cursor (`hooks/hooks-cursor.json` or Project `.cursor/hooks.json`)

Cursor uses `version: 1` and camelCase event names (`sessionStart`) with flat command entries. For plugin hooks, Cursor sets `cwd` to the plugin install directory and passes the user's workspace in `CURSOR_PROJECT_DIR` (and `CLAUDE_PROJECT_DIR`) plus stdin `workspace_roots[0]`:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "./hooks/session-start.sh --harness cursor"
      }
    ]
  }
}
```

## Harness Stdout JSON Schemas for `SessionStart`

A single `hooks/session-start.sh --harness <agy|claude|cursor|json>` script adapts its stdout payload to each harness:

1. **Google Antigravity (`--harness agy`)**:
   Unmarshals stdout using strict `protojson.Unmarshal` into `HookExecutionOutput`. Unknown keys fail parsing. Use `injectSteps` with `systemMessage` (not `ephemeralMessage`, which is dropped after a single turn):

   ```json
   {"injectSteps":[{"systemMessage":{"systemMessage":"..."}}]}
   ```

2. **Claude Code, Codex CLI, & VS Code (`--harness claude`)**:
   When `CURSOR_VERSION` is present in the environment, Cursor is executing the compatibility `.claude-plugin/plugin.json` hook alongside `.cursor-plugin/plugin.json`; emit `{"continue":true}` and exit early to avoid duplicate context injection. Otherwise emit:

   ```json
   {"continue":true,"systemMessage":"...","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}
   ```

3. **Cursor (`--harness cursor`)**:

   ```json
   {"continue":true,"additional_context":"..."}
   ```

## Resolving the Active Workspace in POSIX `sh`

Extract the workspace path in priority order before falling back to `$PWD`:

1. Explicit `--project <path>` CLI flag.
2. `CURSOR_PROJECT_DIR` or `CLAUDE_PROJECT_DIR` environment variables.
3. Stdin JSON via `awk`:
   - `workspacePaths[0]` on Antigravity (`--harness agy`).
   - `workspace_roots[0]` on Cursor (`--harness cursor`).
   - `cwd` on Claude Code (`--harness claude`).
