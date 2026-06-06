# Flow Multi-Host Conformance Matrix (June 2026)

Authoritative per-host contract for what Flow ships and how each host consumes it,
verified against the June 2026 state of each platform. When a host's behavior or a
token changes, update this table **and** the validator/test that guards it so the
two never drift. This complements [multi-host-plugin-patterns.md](./multi-host-plugin-patterns.md)
(the how-to) with a tight conformance contract (the what-must-be-true).

## Contract table

| Host | Install root / manifest | Marketplace | Hook manifest | Hook token | Hook event | Agent file / format | Commands |
|---|---|---|---|---|---|---|---|
| **Claude Code** | `.claude-plugin/plugin.json` (components auto-discover at plugin root) | `.claude-plugin/marketplace.json` | `hooks/hooks-claude.json` (referenced from `plugin.json` `hooks`) | `${CLAUDE_PLUGIN_ROOT}` | `SessionStart` | `agents/*.md` (no `hooks`/`mcpServers`/`permissionMode` in plugin agents) | `commands/*.md` |
| **OpenAI Codex** | `.codex-plugin/plugin.json` (package: `plugins/flow/`) | `.agents/plugins/marketplace.json` (canonical); `.claude-plugin/marketplace.json` legacy | project: `.codex/hooks.json`; installed plugin: auto-discovered `hooks/hooks.json` (emitted from `hooks/hooks-codex.json`) | `${PLUGIN_ROOT}` canonical, `${CLAUDE_PLUGIN_ROOT}` alias, `.` fallback | `SessionStart` | `.codex/agents/*.toml` — requires `name`+`description`+`developer_instructions`; no per-agent `tools` (inherits session) | `commands/flow-*.md` |
| **Gemini CLI** | `gemini-extension.json` | `gemini extensions install <repo>` | `hooks/hooks.json` (auto-discovered) | `${extensionPath}` + `${/}` | `SessionStart` | `agents/*.md` (`.gemini/agents/*.md` for user scope) | `commands/flow/*.toml` |
| **Antigravity CLI** | `gemini-extension.json` (carried forward; "extensions" → "plugins") | install hub `~/.gemini/config/plugins/` | `hooks/hooks.json` (reuses Gemini manifest) | `${extensionPath}` + `${/}` | `SessionStart` | reuses Gemini `agents/*.md`; reads `AGENTS.md`/`GEMINI.md` + `.agents/skills/` | reuses `commands/flow/*.toml` |
| **opencode** | `.opencode/plugins/flow.js` (`@opencode-ai/plugin`) | local / git (`opencode.json` `plugin`) | no SessionStart hook → `experimental.chat.system.transform` + `shell.env` | `FLOW_PLUGIN_ROOT` (set by plugin) | n/a (system-prompt injection) | `.opencode/agents/*.md` — `permission:` object (`allow`/`ask`/`deny`); `steps` not `maxSteps` | reuses skills/commands |
| **Cursor** | `.cursor/rules/flow.mdc` + `AGENTS.md` | n/a (no stable repo plugin API) | `hooks/hooks-cursor.json` (`sessionStart`, cwd-relative) — see constraint | cwd-relative `./hooks/session-start.sh` | `sessionStart` (camelCase) | n/a (rules-based) | n/a |
| **GitHub Copilot** | `.github/agents/*.agent.md` | n/a | n/a | n/a | n/a | `.agent.md` — `description` required; no retired `infer` | n/a |

## Invariants (enforced by validators/tests)

- **Codex hook commands** (`tools/validate-codex-manifest.py::validate_codex_hook_commands`): every Codex-consumed manifest (`.codex/hooks.json`, `hooks/hooks-codex.json`, and the two package copies) must contain **no** Gemini tokens (`${extensionPath}`/`${/}`) and must anchor to `$PLUGIN_ROOT`/`$CLAUDE_PLUGIN_ROOT`. Guards flow-9qx / GH #64.
- **Gemini hook manifest** (`tests/test_gemini_hooks.py`): top-level `hooks/hooks.json` keeps `${extensionPath}`/`${/}` and never embeds `${CLAUDE_PLUGIN_ROOT}`.
- **Claude hook manifest**: `hooks/hooks-claude.json` uses `${CLAUDE_PLUGIN_ROOT}` and never Gemini tokens; `plugin.json` points its `hooks` at it.
- **Package freshness** (`make codex-package-check`): `plugins/flow/` is regenerated from source; its auto-discovered `hooks/hooks.json` is the Codex-native manifest (Gemini installs from the repo root, not the package).
- **Version sync** (`tools/sync-manifests.py`): all bumpversion-tracked manifests carry one version.

## How Codex resolves the plugin root (the flow-9qx fix)

Codex runs `SessionStart` command hooks **through a shell with the session cwd**
(the user's project), not the plugin root. A bare `./hooks/session-start.sh` therefore
does not resolve once installed. The command anchors with a defensive expansion:

```bash
bun "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-.}}/hooks/session-start.js" || node "…/session-start.js" || bash "…/session-start.sh"
```

- `${PLUGIN_ROOT}` — canonical Codex var (installed plugin).
- `${CLAUDE_PLUGIN_ROOT}` — Codex compat alias.
- `.` — cwd fallback for the in-repo project layer (where Codex sets neither var and cwd *is* the repo).

`hooks/session-start.{sh,ps1}` host detection checks `CODEX_PLUGIN_ROOT`/`PLUGIN_ROOT`
**before** the Claude branch (Codex exports the alias too, so order matters).

## Antigravity CLI status

Gemini CLI consumer tiers stop serving **June 18, 2026**; the product becomes
**Antigravity CLI**, where "extensions" are renamed **plugins** (Skills/Hooks/Subagents
preserved). The extension format carries forward: Flow's existing `gemini-extension.json`,
`hooks/hooks.json` (`${extensionPath}`/`${/}`), `agents/*.md`, and `commands/flow/*.toml`
are the Antigravity plugin assets — `~/.gemini` remains the config hub and `.agents/skills/`
is recognized. Enterprise Gemini Code Assist tiers retain full Gemini CLI support.

**Action at release:** verify the Antigravity plugin manifest filename/location against
live docs (`antigravity.google/docs`, the Gemini→Antigravity transition blog). If a new
manifest name is required, add it to the bumpversion file list so it stays version-synced.
See [antigravity.md](./antigravity.md) for the install/migration guide.

## Documented constraints / deferred hardening

- **Cursor command path** is cwd-relative (`./hooks/session-start.sh`). Cursor's repo
  plugin API and whether it expands `${VAR}` in hook commands are not stably documented;
  changing the form risks breaking a working integration. Left cwd-relative until Cursor
  documents a plugin-root token. `session-start.sh` already detects `CURSOR_PLUGIN_ROOT`.
- **Claude exec-form hooks** (`args`) are available in June 2026 but **not adopted**: the
  Codex/Gemini commands require shell form for the `bun||node||bash` ladder, the Claude
  command is a fixed path with no user input (marginal injection benefit), and exec-form
  token substitution in `args` is unverified in this environment. Shell form is kept
  consistently across hosts. Revisit if Claude deprecates shell-form hooks.
- **opencode `@opencode-ai/plugin`** is pinned at `1.4.6` in `.opencode/package-lock.json`
  (latest is `1.16.2`). The plugin uses documented hooks (`experimental.chat.system.transform`,
  `shell.env`). Bumping requires regenerating the lockfile (network + a `package.json`);
  re-verify the hook API against `1.16.2` and regenerate the lockfile as a follow-up rather
  than hand-editing integrity hashes.
