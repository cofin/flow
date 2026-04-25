# Multi-Host Plugin Patterns (April 2026)

Reference for any repo that ships skills, commands, hooks, or agents across **Claude Code**, **Gemini CLI**, **Codex CLI**, **OpenCode**, and **Cursor**. Captures the exact manifest paths, schema keys, and adoption status verified against official docs in this Flow session. Paste into your own project's `docs/` and trim to what applies.

## TL;DR — what every multi-host repo should ship

| File | Host | Purpose |
|---|---|---|
| `.claude-plugin/marketplace.json` | Claude Code | Marketplace catalog (`claude plugin marketplace add owner/repo`) |
| `.claude-plugin/plugin.json` | Claude Code | Plugin manifest — declares skills, commands, hooks, **`userConfig`** |
| `.agents/plugins/marketplace.json` | Codex CLI | Marketplace catalog (`codex plugin marketplace add owner/repo`) |
| `.codex-plugin/plugin.json` | Codex CLI | Plugin manifest with `interface` block |
| `gemini-extension.json` | Gemini CLI | Extension manifest — `plan.directory`, **`excludeTools`**, `contextFileName` |
| `hooks/hooks.json` | Gemini CLI | Auto-discovered hook manifest |
| `hooks/hooks-claude.json` | Claude Code | Per-host hook manifest (referenced from `.claude-plugin/plugin.json`) |
| `hooks/hooks-cursor.json` | Cursor | Per-host hook manifest |
| `.cursor-plugin/plugin.json` | Cursor | Marketplace listing manifest |
| `.opencode/plugins/<name>.js` | OpenCode | Local plugin entrypoint with managed-config awareness |
| `.gitignore` | All | Must `!`-include `.agents/plugins/marketplace.json` if `.agents/` is otherwise ignored |

If `.agents/` is gitignored, use `.agents/*` (NOT `.agents/`) so git descends into the directory and honors re-includes. Then `!.agents/plugins/marketplace.json` works.

## Per-host detail

### Claude Code

**Marketplace manifest** (`.claude-plugin/marketplace.json`):

```json
{
  "name": "<repo>-marketplace",
  "owner": { "name": "<github-handle>", "url": "https://github.com/<handle>" },
  "plugins": [
    { "name": "<plugin>", "description": "...", "version": "<x.y.z>", "source": "./", "author": { "name": "<handle>" } }
  ]
}
```

**Plugin manifest** (`.claude-plugin/plugin.json`):

```json
{
  "name": "<plugin>",
  "displayName": "<Display>",
  "version": "<x.y.z>",
  "skills": ["./skills/"],
  "commands": ["./commands/"],
  "hooks": "./hooks/hooks-claude.json",
  "userConfig": {
    "<field>": {
      "type": "select | string | boolean",
      "default": "<value>",
      "description": "<user-facing label>",
      "options": ["a", "b", "c"]
    }
  }
}
```

**`userConfig` mechanics** ([plugins-reference](https://code.claude.com/docs/en/plugins-reference.md)):
- Prompted on first `claude plugin install`.
- Values written to `${CLAUDE_PLUGIN_ROOT}/.local.md` as YAML frontmatter.
- Skills/hooks read them via the `.local.md` file or the hook context.
- Upgrades preserve existing values; new fields default; user re-prompted only on schema changes.

**Hook env var:** `${CLAUDE_PLUGIN_ROOT}` (NOT `${CLAUDE_PLUGIN_DATA}` — that one is undocumented; ignore claims to use it).

**Hook decision migration** ([hooks docs](https://code.claude.com/docs/en/hooks.md)): if you ship a `PreToolUse` hook, return `hookSpecificOutput.permissionDecision: "allow" | "deny" | "ask" | "defer"`. The older approval/blocking format is deprecated.

**Manifest keys to evaluate (April 2026)**: `userConfig` (✅ adopt for any user-prompted setting), `monitors` (background watchers, e.g. file-state-driven sync), `lspServers` (only if you ship language servers), `channels` (DISABLES `AskUserQuestion` and plan-mode tools when active — skip if your setup needs interactive prompts).

### Codex CLI

**Marketplace manifest** (`.agents/plugins/marketplace.json` — at the source-repo root):

```json
{
  "name": "<repo>-marketplace",
  "interface": { "displayName": "<Display>", "shortDescription": "<one-liner>" },
  "owner": { "name": "<handle>", "url": "https://github.com/<handle>" },
  "plugins": [
    {
      "name": "<plugin>",
      "version": "<x.y.z>",
      "source": { "source": "local", "path": "./" },
      "policy": { "installation": "AVAILABLE" },
      "category": "Development"
    }
  ]
}
```

**Plugin manifest** (`.codex-plugin/plugin.json`):

```json
{
  "name": "<plugin>",
  "version": "<x.y.z>",
  "skills": "./skills/",
  "interface": {
    "displayName": "<Display>",
    "shortDescription": "<one-liner>",
    "category": "Development",
    "capabilities": ["Read", "Write"],
    "defaultPrompt": ["Use <plugin> to ..."]
  }
}
```

**Install command** (Codex CLI 0.117+):

```bash
codex plugin marketplace add <owner>/<repo>          # github source
codex plugin marketplace add <owner>/<repo>@<ref>    # pinned ref
codex plugin marketplace add <git-url> --sparse <path>
codex plugin marketplace add <local-path>            # local dev
codex plugin marketplace upgrade <marketplace-name>
codex plugin marketplace remove  <marketplace-name>
```

In a Codex session, `/plugins` enables/disables installed plugins.

**`storefront` interface block**: claimed in some sources but unverified in current Codex docs. Skip until you can read the schema directly from the openai/codex repo.

### Gemini CLI

**Extension manifest** (`gemini-extension.json` at repo root):

```json
{
  "name": "<extension>",
  "version": "<x.y.z>",
  "contextFileName": "GEMINI.md",
  "plan": { "directory": ".agents" },
  "excludeTools": [
    "run_shell_command(sudo *)",
    "run_shell_command(rm -rf /*)",
    "run_shell_command(rm -rf $HOME*)",
    "run_shell_command(rm -rf ~*)"
  ]
}
```

**Hooks** (`hooks/hooks.json` — auto-discovered, sibling to manifest):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "name": "<hook-name>",
            "type": "command",
            "command": "bun ${extensionPath}${/}hooks${/}session-start.js || node ${extensionPath}${/}hooks${/}session-start.js || bash ${extensionPath}${/}hooks${/}session-start.sh",
            "description": "<purpose>"
          }
        ]
      }
    ]
  }
}
```

Use `${extensionPath}` (Gemini's install-root variable) and `${/}` (cross-platform path separator). The multi-runtime fallback chain (`bun || node || bash`) keeps the hook portable across machines without bun installed.

**`excludeTools` caveat**: works for tools the user manually configured, but does NOT apply to MCP servers bundled with the extension itself ([known limitation, GH #8481](https://github.com/google-gemini/gemini-cli/issues/8481)). Treat it as belt-and-suspenders, not a hard guarantee.

**`plan.directory`** is the only first-class plugin-author hook for redirecting plan-mode artifacts. None of Claude/Codex/OpenCode have an equivalent — they're all user-side config.

### Cursor (2.4+)

**Plugin manifest** (`.cursor-plugin/plugin.json` at repo root):

```json
{
  "name": "<plugin>",
  "displayName": "<Display>",
  "version": "<x.y.z>",
  "author": { "name": "<handle>" },
  "description": "<...>",
  "keywords": ["..."],
  "license": "MIT",
  "homepage": "https://github.com/<handle>/<repo>",
  "repository": "https://github.com/<handle>/<repo>",
  "hooks": "./hooks/hooks-cursor.json"
}
```

**Marketplace** ([cursor.com/marketplace](https://cursor.com/marketplace)):
- Install in editor: `/add-plugin` → search.
- Submit: PR to [github.com/cursor/plugins](https://github.com/cursor/plugins) (open-source only) OR web form at cursor.com/marketplace/publish.
- Local dev: drop into `~/.cursor/plugins/local/<name>/` and restart.
- Team/Enterprise plans support **private team marketplaces** with central governance.

### OpenCode

**Plugin entrypoint** (`.opencode/plugins/<name>.js` — local plugin, npm publish optional):

```javascript
function isPluginDisabledByManagedConfig(ctx) {
  const managed = ctx?.config?.managedConfig ?? ctx?.config?.managed ?? null;
  if (!managed) return false;
  if (managed.disabledPlugins?.includes('<plugin>')) return true;
  if (managed.allowedPlugins && !managed.allowedPlugins.includes('<plugin>')) return true;
  return false;
}

export default async (ctx) => {
  if (isPluginDisabledByManagedConfig(ctx)) return {};
  return {
    'experimental.chat.system.transform': async (_input, output) => {
      output.system.push('<your context injection>');
    },
    'shell.env': async () => ({ env: { '<PLUGIN>_ROOT': '<...>' } })
  };
};
```

**Managed-config layer** ([opencode.ai/docs/config](https://opencode.ai/docs/config/)):
- Deployed via `ai.opencode.managed` PayloadType (macOS .mobileconfig — Jamf, Kandji, FleetDM).
- Loaded last; highest precedence; cannot be overridden by user/project config.
- Respect it. Early-return when disabled rather than fighting the policy.

**Why `experimental.chat.system.transform`**: OpenCode has no SessionStart hook as of `@opencode-ai/plugin@1.3.6`. System-prompt injection is the supported context-bootstrap point. Don't invent a SessionStart polyfill.

**Recommended project settings** (`opencode.json` at project root):

```json
{
  "permission": { "edit": "ask", "bash": "ask" },
  "instructions": ["AGENTS.md", ".agents/product.md", ".agents/tech-stack.md"]
}
```

## Skills format — agentskills.io standard

Adopted by Claude, Codex, Gemini, GitHub Copilot, VS Code, Cursor. Use the same `SKILL.md` for every host:

```markdown
---
name: <skill-name>             # 1–64 chars, lowercase + hyphens, no leading/trailing -, no --
description: <when to use>     # 1–1024 chars
license: Apache-2.0            # optional
compatibility: <env reqs>      # optional
metadata:                      # optional key-value
  author: <handle>
  version: "1.0"
allowed-tools: "Bash(pdftotext:*) Read"   # optional, space-separated
---

## Instructions
...
```

[agentskills.io/specification](https://agentskills.io/specification) is authoritative.

## Cross-host policy bootstrap pattern

Each host has knobs only the user can flip — there's no plugin-author hook for plan-mode directories or default permissions outside Gemini's `plan.directory`. Pattern: have your `/setup` workflow detect installed hosts and **opt-in prompt** to merge recommended settings.

| Host | Target file | Gitignored by host? | Merge keys |
|---|---|---|---|
| Claude | `.claude/settings.local.json` | YES (per-developer) | `plansDirectory`, `permissions.allow` |
| OpenCode | `opencode.json` | NO (committed unless user excludes) | `permission`, `instructions` |
| Codex | `~/.codex/config.toml` (global) | N/A | DON'T auto-write — recommend trust prompt |
| Gemini | `.gemini/policies/<name>-overrides.toml` + `.geminiignore` | NO (committed) | tool allowlist, ignore allowlist |

**Critical rules for the merge step**:
- ALWAYS back up to `.bak` before editing.
- ALWAYS merge — never overwrite user keys.
- Use `jq` when available; fall back to a Python helper.
- Make the prompt opt-in (Yes / Skip), not default-yes-with-undo.
- Reruns must be idempotent (`unique` on arrays).

## Install commands per host (canonical, copy-paste)

```bash
# Gemini CLI
gemini extensions install https://github.com/<owner>/<repo> --auto-update
gemini extensions update <name>

# Claude Code
claude plugin marketplace add <owner>/<repo>
claude plugin install <plugin>@<marketplace-name>
claude plugin marketplace update <marketplace-name>
claude plugin update <plugin>@<marketplace-name>

# Codex CLI
codex plugin marketplace add <owner>/<repo>
# in session: /plugins → enable
codex plugin marketplace upgrade <marketplace-name>

# OpenCode (local, no marketplace yet)
git clone https://github.com/<owner>/<repo>.git ~/.config/opencode/<name>
ln -sf ~/.config/opencode/<name>/.opencode/plugins/<name>.js ~/.config/opencode/plugins/<name>.js

# Cursor
# In editor: /add-plugin → search → install
```

## What NOT to ship

- A custom `install.sh` as the primary install path. Native marketplace commands replaced ~80% of what those scripts used to do. Keep the script only as a multi-host orchestrator that wraps the native commands.
- Manual `~/.agents/plugins/marketplace.json` authoring instructions to end users — the native `codex plugin marketplace add` covers this.
- jq mutations of `~/.claude/settings.json` from your installer — `claude plugin install` does it.
- Symlink-based "plugin install" instructions for Claude or Codex — both have native marketplace commands now.
- Reliance on undocumented env vars (`${CLAUDE_PLUGIN_DATA}`) or undocumented Gemini settings (`autoEnter`).

## Verifying changes locally

```bash
# JSON manifests
python3 -c "import json; [json.load(open(p)) for p in [
  '.claude-plugin/marketplace.json', '.claude-plugin/plugin.json',
  '.agents/plugins/marketplace.json', '.codex-plugin/plugin.json',
  '.cursor-plugin/plugin.json', 'gemini-extension.json',
  'hooks/hooks.json', 'hooks/hooks-claude.json', 'hooks/hooks-cursor.json'
]]"

# OpenCode plugin
node --check .opencode/plugins/<name>.js

# Codex marketplace registration (from a checkout)
codex plugin marketplace add ./

# SKILL.md frontmatter compliance
python3 -c "
import os, re
for dp,_,fn in os.walk('skills'):
    for f in fn:
        if f != 'SKILL.md': continue
        p = os.path.join(dp,f); t = open(p).read()
        assert t.startswith('---\n'), p
        e = t.find('\n---\n', 4); assert e > 0, p
        fm = t[4:e]
        assert re.search(r'^name:\s*\S', fm, re.M), p
        assert re.search(r'^description:\s*\S', fm, re.M), p
print('all SKILL.md compliant')
"
```

## Source documents (pin these)

- Claude Code: <https://code.claude.com/docs/en/plugins-reference> · <https://code.claude.com/docs/en/hooks.md> · <https://code.claude.com/docs/en/settings>
- Codex CLI: <https://developers.openai.com/codex/plugins/build> · <https://developers.openai.com/codex/config-reference>
- Gemini CLI: <https://geminicli.com/docs/extensions/reference/> · <https://geminicli.com/docs/hooks/reference/>
- OpenCode: <https://opencode.ai/docs/plugins/> · <https://opencode.ai/docs/config/>
- Cursor: <https://cursor.com/docs/plugins> · <https://cursor.com/marketplace>
- Skills: <https://agentskills.io/specification>
