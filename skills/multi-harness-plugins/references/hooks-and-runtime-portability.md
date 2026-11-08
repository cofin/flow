# Hooks & Runtime Portability

Design runtime hooks that execute reliably across Linux, macOS, and Windows without assuming `python3`, `node`, or `jq` are installed on the host machine.

## Runtime Environment Reality Across Harnesses

| Harness | Host Binary Type | Guaranteed Runtime Dependencies |
| --- | --- | --- |
| **Google Antigravity (`agy`)** | Compiled native binary | POSIX `sh`, `awk`, `git` on Unix; `pwsh` / `powershell` on Windows (no bundled Python or Node.js) |
| **Codex CLI (`codex`)** | Compiled Rust binary | POSIX `sh`, `awk`, `git` on Unix; `%COMSPEC% /C` + `powershell` (`commandWindows`) on Windows |
| **Claude Code (`claude`)** | Bun / Node binary | POSIX `sh`, `awk`, `git` on Unix; `pwsh` / `powershell` (`commandWindows`) on Windows |
| **Cursor (`cursor`)** | Electron IDE | POSIX `sh`, `awk`, `git` on Unix; `pwsh` / `powershell` on Windows |
| **VS Code (`code`)** | Electron IDE | POSIX `sh`, `awk`, `git` on Unix; `pwsh` / `powershell` (`commandWindows`) on Windows |
| **OpenCode V2 (`opencode`)** | Bun / Node runtime | In-process `node:fs` and `node:path` inside `.opencode/plugins/<name>.js` |

## Harness Hook Configurations (Plugin & Project-Local)

### 1. Google Antigravity (`hooks.json` at Plugin Root or `.agents/hooks.json` in Project)

Antigravity requires **flat** handler arrays for lifecycle events (`SessionStart`, `PreInvocation`, `PostInvocation`, `Stop`) and **nested** `matcher` arrays only for tool events (`PreToolUse`, `PostToolUse`). Nesting `SessionStart` under `{ "matcher": "*", "hooks": [...] }` causes `ParseHooks` to fail and drop the entire `hooks.json` file.

Also note that for global plugins, Antigravity sets `cmd.Dir` to the **installed plugin directory** (not the user's workspace) and passes the active workspace inside stdin JSON (`workspacePaths[0]`):

```json
{
  "my-plugin-session-start": {
    "SessionStart": [
      {
        "type": "command",
        "command": "sh ./hooks/on-session-start.sh --harness agy",
        "timeout": 15
      }
    ]
  },
  "my-plugin-stop-check": {
    "Stop": [
      {
        "type": "command",
        "command": "sh ./hooks/on-stop.sh --harness agy",
        "timeout": 10
      }
    ]
  }
}
```

### 2. Claude Code, Codex CLI, & VS Code (`.claude/settings.json` / `.codex/hooks.json` or Plugin Hook Config)

Claude Code and Codex CLI require the **nested** `matcher` structure for all events (`SessionStart` and `Stop`). Provide `"commandWindows"` invoking native PowerShell (`hooks/on-session-start.ps1`, `hooks/on-stop.ps1`) equivalents so Windows hosts executing via `%COMSPEC% /C` (`cmd.exe /c`) do not require `sh` on `PATH`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/on-session-start.sh --harness claude",
            "commandWindows": "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"${CLAUDE_PLUGIN_ROOT}/hooks/on-session-start.ps1\" --harness claude"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/on-stop.sh --harness claude",
            "commandWindows": "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"${CLAUDE_PLUGIN_ROOT}/hooks/on-stop.ps1\" --harness claude",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- In **Claude Code**, `hooks/hooks.json` auto-loads and merges with any file declared in `.claude-plugin/plugin.json` `hooks`. Point `.claude-plugin/plugin.json` at a dedicated file and keep root `hooks.json` for Antigravity so neither harness collides.
- In **Claude Code** and **Codex CLI**, `Stop` runs on the main agent loop (subagents fire `SubagentStop`). In **Codex CLI**, project-local `.codex/hooks.json` (or inline `[hooks]` in `.codex/config.toml`) only runs for trusted projects, and plugin hooks require user trust approval on install/upgrade.

### 3. Cursor (Project `.cursor/hooks.json` or Plugin Hook Config)

Cursor uses `version: 1` and camelCase event names (`sessionStart`, `stop`) with flat command entries and `"loop_limit"` on `stop` hooks. For plugin hooks, Cursor sets `cwd` to the plugin install directory and passes the user's workspace in `CURSOR_PROJECT_DIR` (and `CLAUDE_PROJECT_DIR`) plus stdin `workspace_roots[0]`:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "./hooks/on-session-start.sh --harness cursor"
      }
    ],
    "stop": [
      {
        "command": "./hooks/on-stop.sh --harness cursor",
        "loop_limit": 2
      }
    ]
  }
}
```

### 4. OpenCode V2 (`.opencode/plugins/<name>.js`)

In OpenCode V2, `ctx.session.hook("context", (event) => { event.system.push({ type: "text", text: readSummary(workspaceDir) }); })` runs on **every model request** in the agent loop, including tool continuations. The callback mutates `event.system` in place; return values are ignored, and V1 hooks such as `"experimental.chat.system.transform"` never run. Resolve the workspace from `ctx.location.directory`, and re-evaluate bundle state inside the hook callback (never cache once at `setup(ctx)`) so mid-session chapter progress and pending review/sync warnings surface on the next turn.

## Harness Stdout JSON Schemas for `SessionStart`

A single POSIX `sh` script can adapt its stdout payload to each harness:

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

## Harness Stdout JSON Schemas & Circuit Breakers for `Stop`

`Stop` hooks prevent premature coordinator turn completion when checklists drift, completed chapters lack review stamps, or living Markdown specs are out of sync. Always emit `{}` and exit `0` when clean or when a safety guard fires:

1. **Google Antigravity (`--harness agy`)**:
   - **Stdin (`StopHookArgs`)**: `executionNum`, `terminationReason` (`"model_stop"`, `"max_steps_exceeded"`, `"error"`), `error`, `fullyIdle`, `workspacePaths`, `lastUserInput`, `parentConversationId`.
   - **Circuit Breaker & Subagent Guard**: Allow stop (`{}`) if `terminationReason != "model_stop"`, `error` is non-empty, `executionNum >= 2`, or `parentConversationId` / leaf `agents/*.md` indicates a leaf subagent turn without checklist corruption.
   - **Block Stop (`StopHookResult` — `"block"` is deprecated; always use `"continue"`)**:

     ```json
     {"decision":"continue","reason":"Synchronize present-tense specs and complete chapter review before stopping."}
     ```

2. **Claude Code, Codex CLI, & VS Code (`--harness claude`)**:
   - **Circuit Breaker & Cursor Dedupe**: Allow stop (`{}`) when `CURSOR_VERSION` is set or stdin contains `"stop_hook_active": true`.
   - **Block Stop**:

     ```json
     {"decision":"block","reason":"Synchronize present-tense specs and complete chapter review before stopping."}
     ```

3. **Cursor (`--harness cursor`)**:
   - **Circuit Breaker**: Allow stop (`{}`) when stdin `"status"` is non-empty and `!= "completed"` or `"loop_count"` `>= 1`.
   - **Block Stop**:

     ```json
     {"followup_message":"Synchronize present-tense specs and complete chapter review before stopping."}
     ```

## Resolving the Active Workspace in POSIX `sh`

Extract the workspace path in priority order before falling back to `$PWD`:

1. Explicit `--project <path>` CLI flag.
2. `CURSOR_PROJECT_DIR` or `CLAUDE_PROJECT_DIR` environment variables.
3. Stdin JSON via `awk`:
   - `workspacePaths[0]` on Antigravity (`--harness agy`).
   - `workspace_roots[0]` on Cursor (`--harness cursor`).
   - `cwd` on Claude Code (`--harness claude`).
