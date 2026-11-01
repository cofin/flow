# Manifests & Single-Root Packaging

Package multi-harness agent plugins from a single repository root without duplicate directory mirrors or codegen sync scripts.

## Single-Root Directory Layout

```text
<plugin-root>/
├── AGENTS.md
├── Makefile
├── README.md
├── hooks.json                             # Google Antigravity SessionStart hook manifest (must stay at root)
├── package.json                           # OpenCode V2 package entry ("main": ".opencode/plugins/<name>.js")
├── plugin.json                            # Google Antigravity plugin manifest
├── pyproject.toml                         # Dev/CI tooling (ruff, mypy, pyright, pytest, bump-my-version)
├── .agents/
│   └── plugins/marketplace.json           # Codex CLI marketplace ("source": {"source": "local", "path": "./"})
├── .claude-plugin/
│   ├── marketplace.json                   # Claude Code marketplace catalog ("source": "./")
│   └── plugin.json                        # Claude Code & VS Code Agent Plugins manifest
├── .codex/
│   └── agents/*.toml                      # Codex CLI TOML custom subagents
├── .codex-plugin/
│   └── plugin.json                        # Codex CLI plugin manifest
├── .cursor-plugin/
│   └── plugin.json                        # Cursor native plugin manifest
├── .opencode/
│   └── plugins/<name>.js                  # OpenCode V2 plugin module ({ id, async setup(ctx) })
├── agents/*.md                            # Universal Markdown subagents (AGY, Claude, Cursor, VS Code, OpenCode)
├── hooks/
│   ├── hooks-claude.json                  # Claude Code & VS Code SessionStart hook config
│   ├── hooks-cursor.json                  # Cursor sessionStart hook config
│   └── session-start.sh                   # Pure POSIX sh + awk priming script
├── rules/*.md                             # Operational rules (AGY & Cursor)
└── skills/<skill-name>/
    ├── SKILL.md
    └── references/*.md
```

## Harness Manifest Schemas

### 1. Google Antigravity (`plugin.json` at Root)

Antigravity's plugin validator checks `plugin.json` against a strict key allowlist (`$schema`, `name`, `displayName`, `version`, `description`, `contextFileName`, `excludeTools`, `skills`, `agents`, `rules`, `mcpServers`, `apps`). Do not add non-standard keys (`author`, `license`, `hooks`, `commands`) to root `plugin.json`.

```json
{
  "$schema": "https://raw.githubusercontent.com/google/antigravity/main/schemas/plugin.schema.json",
  "name": "my-plugin",
  "displayName": "My Plugin",
  "version": "0.1.0",
  "description": "Concise plugin summary."
}
```

### 2. Claude Code & VS Code (`.claude-plugin/plugin.json` & `.claude-plugin/marketplace.json`)

Claude Code and VS Code Agent Plugins (`chat.plugins.enabled`) read `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Concise plugin summary.",
  "hooks": "./hooks/hooks-claude.json"
}
```

> **Important**: Never ship a root `CLAUDE.md` in a plugin repository—`claude plugin validate --strict` rejects root `CLAUDE.md`, and Cursor double-loads both `AGENTS.md` and `CLAUDE.md`. Use `AGENTS.md` at the repository root.

### 3. Codex CLI (`.codex-plugin/plugin.json` & `.agents/plugins/marketplace.json`)

Point `.agents/plugins/marketplace.json` directly at `"path": "./"` so no `plugins/<name>/` mirror directory is needed:

```json
{
  "name": "my-plugin-local",
  "interface": {
    "displayName": "My Plugin Local Marketplace"
  },
  "plugins": [
    {
      "name": "my-plugin",
      "source": {
        "source": "local",
        "path": "./"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

### 4. Cursor (`.cursor-plugin/plugin.json`)

Cursor natively discovers `.cursor-plugin/plugin.json`, `skills/`, `agents/`, and `rules/`:

```json
{
  "name": "my-plugin",
  "displayName": "My Plugin",
  "version": "0.1.0",
  "description": "Concise plugin summary.",
  "hooks": "./hooks/hooks-cursor.json"
}
```

### 5. OpenCode V2 (`package.json` & `.opencode/plugins/<name>.js`)

Set `"main": ".opencode/plugins/<name>.js"` in `package.json` and export an OpenCode V2 plugin object `{ id: "<name>", async setup(ctx) { ... } }`:

```javascript
export const MyPlugin = {
  id: "my-plugin",
  async setup(ctx) {
    ctx.config.skills = ctx.config.skills || {};
    ctx.config.skills.paths = ctx.config.skills.paths || [];
  },
};

export default MyPlugin;
```

## Version Synchronization via `pyproject.toml`

Register all 8 manifest paths under `[[tool.bumpversion.files]]` in `pyproject.toml` so `make release bump=minor|patch|major` updates every manifest atomically without custom sync scripts.
