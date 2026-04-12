# Host Matrix

## Claude Code

- Preferred install path: marketplace.
- Preferred commands:
  - `claude plugin marketplace add <source>`
  - `claude plugin install <plugin>@<marketplace>`
  - `claude plugin marketplace update [name]`
  - `claude plugin update <plugin>@<marketplace>`
- Git-based marketplaces are supported and are the best fit for shared plugins.
- Updating marketplace metadata and updating an installed plugin are separate steps.

## Gemini CLI

- Preferred install path: native extension install from GitHub.
- Preferred commands:
  - `gemini extensions install <source> [--auto-update]`
  - `gemini extensions update <name>`
  - `gemini extensions link <path>` for local development only
- Gemini copies installed extensions into `~/.gemini/extensions`.
- Management operations take effect after the CLI session is restarted.
- `contextFileName` controls which extension-local context file is loaded.

## Codex CLI

- Plugin manifests live in `.codex-plugin/plugin.json`.
- Marketplaces live in `.agents/plugins/marketplace.json`.
- Keep the marketplace as the published catalog and treat the installed plugin as a cached copy.
- Codex can refresh plugin cache/version state independently of the source checkout, so docs should distinguish source checkout from installed state.

## OpenCode

- Preferred install path: local plugin files in `.opencode/plugins/` or `~/.config/opencode/plugins/`.
- `opencode.json` `plugin` entries are for npm packages, not the default local-development path.
- OpenCode merges config layers instead of replacing them.
- npm plugins are cached under `~/.cache/opencode/node_modules/`.
- Skills can be discovered from:
  - `.opencode/skills/`
  - `.claude/skills/`
  - `.agents/skills/`
  - their matching global directories

## Google Antigravity

- Prefer workspace-local `.agents` assets when the build supports them.
- Keep a global fallback for environments that still rely on home-directory skills.
- Separate workspace guidance from global installer guidance so local repos avoid unnecessary admin work.
