# Skills, Subagents, Local `.agents/`, & MCP Limits

Author skills, subagents, local `.agents/` directories, and MCP configurations that satisfy the strictest parser constraints across Google Antigravity, Claude Code, Codex CLI, Cursor, OpenCode V2, and VS Code.

## How Each Harness Uses Local `.agents/` & Project Config Folders

### 1. Project-Local Skills (`.agents/skills/`)

- **Native `.agents/skills/<name>/SKILL.md` Discovery**:
  Google Antigravity (`agy`), Codex CLI (`codex`), Cursor (`cursor`), OpenCode V2 (`opencode`), and VS Code (`code`) all natively discover project-local skills in `.agents/skills/<name>/SKILL.md`.
- **Claude Code Compatibility**:
  Claude Code discovers project-local skills from `.claude/skills/<name>/SKILL.md`. If a project uses Claude Code alongside `.agents/skills/`, either symlink `.claude/skills` $\rightarrow$ `../.agents/skills` or load the Flow plugin which primes `.agents/skills/index.md` at `SessionStart`.
- **Recommended Project-Local Skill Layout**:

  ```text
  .agents/skills/
  ├── index.md                                     # Concise catalog of project-local skills & triggers
  ├── <domain>/
  │   ├── SKILL.md                                 # Domain architecture & implementation rules (< 24 KB)
  │   └── references/
  │       ├── checklist.md                         # High-signal engineering checklist
  │       └── false-positive-suppressions.md       # Known safe patterns reviewers must not flag
  └── review-<domain>/
      ├── SKILL.md                                 # Zero-context review lens for specs & diffs (< 24 KB)
      └── references/
          ├── checklist.md
          └── false-positive-suppressions.md
  ```

### 2. Project-Local Subagents (`.agents/agents/`, `.codex/agents/`, `.claude/agents/`)

- **Google Antigravity**: Loads `.agents/agents/<name>.md` and `.agents/agents/<name>/agent.md` (plus `_agents/agents/`).
- **Codex CLI**: Loads `.codex/agents/<name>.toml` recursively in trusted projects (Codex plugins cannot register custom subagents via the plugin loader, so project-local `.codex/agents/*.toml` or `~/.codex/agents/*.toml` is required).
- **Cursor**: Loads `.cursor/agents/*.md` plus compatibility `.claude/agents/*.md` and `.codex/agents/`.
- **Claude Code & VS Code**: Load `.claude/agents/*.md` (and `.github/agents/*.agent.md` in VS Code).
- **OpenCode V2**: Loads `.opencode/agents/*.md` or registers `.agents/agents/*.md` dynamically via `ctx.agent.transform` inside `.opencode/plugins/flow.js`.

### 3. Project-Local Rules & Instructions (`AGENTS.md` & `.agents/rules/`)

- **Universal Baseline (`AGENTS.md`)**:
  All six harnesses natively read `AGENTS.md` at the repository root (and nested directory `AGENTS.md` files).
  - Never place a `CLAUDE.md` file alongside `AGENTS.md` unless `CLAUDE.md` explicitly imports `@AGENTS.md`: Claude Code's `claude-md-or-agents-md` mode suppresses `AGENTS.md` when `CLAUDE.md` is present, while Cursor's third-party import loads both and duplicates prompt tokens.
- **Scoped Rules (`.agents/rules/*.md` & `.cursor/rules/*.mdc`)**:
  - In Google Antigravity, `.agents/rules/*.md` supports YAML frontmatter `trigger: always_on | model_decision | glob | manual` (with `globs:` and `description:`).
  - In Cursor, `.cursor/rules/*.mdc` (or `.md`) supports `alwaysApply: true|false`, `globs:`, and `description:`.

### 4. Project-Local & Plugin MCP Configurations

Each harness reads MCP server definitions from a distinct file and applies different variable expansion and tool-name length rules:

| Harness | Local Project MCP File | Plugin MCP File | Variable Expansion | Tool Naming & Length Limit |
| --- | --- | --- | --- | --- |
| **Google Antigravity** | `.agents/mcp_config.json` (or `~/.gemini/antigravity/mcp_config.json`) | Root `mcp_config.json` | Expands `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` in `args`, `env`, `cwd` only (**never** in `command`) | `mcp_<pluginDir>_<server>_<tool>` — **strict `<= 64` char limit** (`^[a-zA-Z0-9_-]{1,64}$`); longer names are silently force-disabled |
| **Claude Code** | Root `.mcp.json` (`mcpServers`) | `.mcp.json` or inline `mcpServers` in `.claude-plugin/plugin.json` | Expands `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` | `mcp__plugin_<plugin>_<server>__<tool>` (or `mcp__<server>__<tool>`) — **`<= 128` char limit**; longer names are dropped |
| **Codex CLI** | Root `.mcp.json` or `[mcp_servers.<name>]` in `.codex/config.toml` | `.mcp.json` or inline `mcpServers` in `.codex-plugin/plugin.json` | No `${PLUGIN_ROOT}` expansion in `.mcp.json`; resolves relative `"cwd": "."` against plugin root | `mcp__<server>__<tool>` (sanitized to `[A-Za-z0-9_]`) — **`<= 128` bytes**; longer names get truncated + 12-hex SHA-1 suffix |
| **Cursor** | `.cursor/mcp.json` (`mcpServers`) | Root `mcp.json` or `mcpServers` in `.cursor-plugin/plugin.json` | Expands `${workspaceFolder}`, `${CURSOR_PLUGIN_ROOT}`, and `${CLAUDE_PLUGIN_ROOT}` (not `${PLUGIN_ROOT}`) | `<server>` + `<tool>` — **strict `<= 59` char limit**; longer names are filtered out with a warning |
| **OpenCode V2** | `opencode.json` (`mcp.servers.<name>`) | `ctx.mcp.transform` in `.opencode/plugins/<name>.js` | Relative `cwd` resolves from workspace | In Code Mode (`codemode: true`), called as `tools.<server>.<tool>()`; with `codemode: false`, `<server>_<tool>` (`<= 64` chars on Bedrock) |
| **VS Code** | `.vscode/mcp.json` (`servers` key) | Inline `mcpServers` in `.claude-plugin/plugin.json` or `.mcp.json` | Expands `${workspaceFolder}`, `${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_ROOT}` | `mcp_<serverInfo.name, <=13 chars>_<tool>` — truncated at **`64` chars** |

**MCP Best Practices**:

- Keep plugin directory names (`<= 12` chars), server keys (`<= 12` chars), and tool names (`<= 30` chars) short so `mcp_<plugin>_<server>_<tool>` stays well under Cursor's `59`-character and Antigravity's `64`-character limits.
- In Antigravity `mcp_config.json`, always put the bare executable name (`"command": "uv"` or `"command": "sh"`) in `command` and place `${PLUGIN_ROOT}/...` paths inside `args` or `cwd`.

## Progressive-Disclosure Skill Rules (`SKILL.md`)

1. **`24,000`-Byte (`24 KB`) Hard Cap**:
   Google Antigravity truncates `SKILL.md` files past `24,000` bytes (`MaxWorkflowContentBytes = 24000`), silently dropping `Guardrails` and `Validation` sections at the bottom of oversized files. Keep `SKILL.md` under `200` lines and `< 24,000` bytes.
2. **Frontmatter Contract**:
   `name` must match the parent directory slug; `description` must start with `Use when ...` and stay `<= 500` characters.

## Universal Subagent Format (`agents/*.md` & `.agents/agents/*.md`)

```yaml
---
name: code-reviewer
description: "Review an exact Git range for spec conformance, correctness, and verification depth."
model: inherit
mainAgent: false
subagent: true
readonly: true
commandExecutionPolicy: turbo
skills:
  - flow
  - flow-completion
  - debloat
disallowedTools:
  - Edit
  - Write
  - MultiEdit
  - NotebookEdit
---
```

- **Top-Level H1 (`# `) Headings**: Antigravity's `splitMarkdownSections` splits subagent Markdown bodies only on H1 (`# Header`) lines (`##` headings collapse into a single fallback section). Use `# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, and `# Output Contract`, with `###` for subsections.
- **`mainAgent: false` + `subagent: true`**: Keeps specialized reviewers and executors out of the primary top-level agent dropdown while keeping them invokable via `invoke_subagent` and `run_workflow`.
- **YAML List `tools` / `disallowedTools`**: Never use comma-separated strings (`tools: Read, Grep`), which fail YAML `[]string` unmarshaling in Antigravity.
- **Valid `model` Values**: Use `model: inherit` (compatibility across Antigravity, Claude Code, and Cursor; Antigravity rejects Claude-specific model aliases like `sonnet` or `opus`).
