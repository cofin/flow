# Installing Flow for Antigravity

Flow treats Antigravity as the primary plugin harness.

## Shipped plugin files

| Asset | File | Purpose |
|---|---|---|
| Plugin manifest | `plugin.json` | Antigravity plugin identity and metadata |
| Hook manifest | `hooks.json` | Root `SessionStart` hook registration |
| Hook implementation | `hooks/session-start.sh` | Beads, project, and Flow context injection |
| Subagents | `agents/*.md` | Flow lifecycle agents |
| Skills | `skills/**/SKILL.md` | Agent Skills-compatible Flow and technology skills |

The hook command resolves the plugin root from `ANTIGRAVITY_PLUGIN_ROOT`, `AGY_PLUGIN_ROOT`, or `PLUGIN_ROOT`, then falls back to the installed Antigravity plugin cache or the current checkout for local validation.

## Install

Use Antigravity's native Plugins & Skills installer for the `cofin/flow` repository. Do not install Flow by copying directories or creating symlinks.

After install or update, restart Antigravity so it reloads `plugin.json`, `hooks.json`, agents, and skills.

## Validate

```bash
make validate-antigravity-manifest
```

This validates the root manifest and rejects legacy extension-template hook tokens that shells cannot expand.
