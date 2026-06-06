# Installing Flow for Antigravity CLI

Google is transitioning **Gemini CLI** into **Antigravity CLI**. Consumer Gemini CLI
tiers (free, AI Pro, AI Ultra) stop serving requests on **June 18, 2026**; enterprise
Gemini Code Assist Standard/Enterprise tiers retain full Gemini CLI support. In
Antigravity, "extensions" are renamed **plugins**, and Agent Skills, Hooks, and
Subagents are preserved.

Flow targets Antigravity by **reusing its Gemini extension assets** — no separate
manifest is required as of June 2026.

## What carries forward

| Asset | File | Notes |
|---|---|---|
| Extension manifest | `gemini-extension.json` | Same schema; `${extensionPath}`/`${/}` tokens still valid |
| SessionStart hook | `hooks/hooks.json` | Auto-discovered; `bun \|\| node \|\| bash` ladder |
| Subagents | `agents/*.md` | Markdown + frontmatter |
| Commands | `commands/flow/*.toml` | TOML slash commands |
| Context | `GEMINI.md` / `AGENTS.md` | Antigravity reads both |
| Skills | `skills/**/SKILL.md` | `.agents/skills/` is recognized as an alias |

The config hub remains `~/.gemini` (conversations, MCP config, plugins, approved
project folders, shared skills).

## Install

While Antigravity's marketplace/install flow stabilizes, install Flow the same way as
the Gemini extension (Antigravity reads the same hub):

```bash
# Gemini CLI (still works on enterprise tiers and pre-cutover)
gemini extensions install https://github.com/cofin/flow --auto-update
```

For Antigravity-native installation, follow Google's transition guide once published
(`antigravity.google/docs`). The Flow assets above require no changes to register as
an Antigravity plugin.

## Verify at release

The Antigravity plugin manifest filename/location is being finalized by Google
("docs coming weeks" as of the transition announcement). At each Flow release:

1. Check `antigravity.google/docs` and the
   [Gemini → Antigravity CLI transition post](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
   for a required manifest rename or new location.
2. If a new manifest file is introduced, add it to the `[tool.bumpversion]` file list in
   `pyproject.toml` so its version stays in sync, and add it to the conformance matrix.
3. Confirm `${extensionPath}`/`${/}` hook tokens are still honored (they were as of June 2026).

## Hook token note

Antigravity uses the **Gemini** hook tokens (`${extensionPath}`, `${/}`) — NOT the
Codex `${PLUGIN_ROOT}` form. Flow keeps these separate: `hooks/hooks.json` (Gemini /
Antigravity) and `hooks/hooks-codex.json` (Codex). See
[host-conformance-matrix.md](./host-conformance-matrix.md).
