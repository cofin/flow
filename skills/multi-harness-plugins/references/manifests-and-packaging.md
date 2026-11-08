# Manifests & Single-Root Packaging

Package multi-harness agent plugins from a single repository root without duplicate directory mirrors or codegen sync scripts.

## Single-Root Directory Layout

```text
<plugin-root>/
├── AGENTS.md
├── README.md
├── hooks.json                             # Google Antigravity SessionStart hook manifest (must stay at root)
├── package.json                           # OpenCode V2 package entry ("main": ".opencode/plugins/<name>.js")
├── plugin.json                            # Google Antigravity plugin manifest
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
│   ├── on-session-start.sh                # Pure POSIX sh + awk priming script (Unix/macOS)
│   └── on-session-start.ps1               # Native PowerShell priming script (Windows / pwsh)
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
  "description": "Concise plugin summary."
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
  "description": "Concise plugin summary."
}
```

### 5. OpenCode V2 (`package.json` & `.opencode/plugins/<name>.js`)

Point `main` and `exports` (`"."` and `"./server"`) in `package.json` at `.opencode/plugins/<name>.js`, and list the runtime directories in `files`. OpenCode resolves a package's `./server` export first. For a local directory plugin, it reads `exports` only when `exports` is defined; otherwise it looks for root `server` or `index` files and ignores `main`.

The default export must be `{ id, setup(ctx) }` (or `{ id, effect }`). Anything else fails with "Plugin must export a default definition with an id and an effect or setup function", which is how pre-V2 standalone copies left in `~/.config/opencode/plugins/` break.

```javascript
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

export default {
  id: "my-plugin",
  async setup(ctx) {
    await ctx.skill.transform((editor) => {
      editor.add({ id: "my-skill", name: "my-skill", path: path.join(PLUGIN_ROOT, "skills/my-skill/SKILL.md"), content: "..." });
    });
    await ctx.agent.transform((editor) => {
      editor.update("my-reviewer", (agent) => {
        agent.mode = "subagent";
        agent.system = "...";
        agent.permissions.push({ action: "edit", resource: "*", effect: "deny" });
      });
    });
  },
};
```

- `transform` callbacks receive an editor and their return value is ignored. `agent` editors create missing agents from the default (primary, allow-all) record, so set `mode` and permissions explicitly.
- OpenCode does not discover skills from a plugin package's `skills/` directory; register them through `ctx.skill.transform`.
- `setup` must return nothing or a cleanup function. OpenCode calls any returned value on unload.

### npm and npx bin entry points

npm and npx launch `bin` scripts through a `node_modules/.bin/<name>` symlink. Node resolves the symlink for `import.meta.url` but keeps it in `process.argv[1]`, so a guard such as `path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)` never matches and the bin exits silently. Compare `fs.realpathSync` of both paths.
