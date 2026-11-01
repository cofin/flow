---
name: multi-harness-plugins
description: Use when creating, structuring, or validating multi-harness plugins or project-local .agents/ skills, subagents, hooks, rules, and MCP configs across Google Antigravity, Claude Code, Codex CLI, Cursor, OpenCode, and VS Code.
---

# Multi-Harness Plugins & Project-Local `.agents/` Architecture

Build and maintain skills, subagents, hooks, rules, and MCP configurations that work cleanly across **Google Antigravity (IDE & CLI)**, **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / GitHub Copilot**—both for **project-local `.agents/` folders** and **extension-wide plugins**.

## Project-Local Discovery Matrix (`.agents/` & Repo-Local Configs)

How each harness discovers project-local instructions, skills, subagents, hooks, and MCP servers inside a repository:

| Surface | Google Antigravity (`agy`) | Claude Code (`claude`) | Codex CLI (`codex`) | Cursor (`cursor`) | OpenCode V2 (`opencode`) | VS Code / Copilot (`code`) |
| --- | --- | --- | --- | --- | --- | --- |
| **Instructions** | `AGENTS.md`, `GEMINI.md`, `.agents/rules/*.md` | `AGENTS.md` (native; suppressed if `CLAUDE.md` exists without `@AGENTS.md`) | `AGENTS.md` (`AGENTS.override.md` wins; trusted projects) | `AGENTS.md`, `.cursor/rules/*.mdc` or `*.md` | `AGENTS.md` (walked from `cwd` to root; no `CLAUDE.md` fallback) | `AGENTS.md` (`chat.useAgentsMdFile: true`) |
| **Project Skills** | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` (or symlinked to `.agents/skills/`) | `.agents/skills/<name>/SKILL.md` | `.agents/skills/`, `.cursor/skills/`, `.claude/skills/` | `.agents/skills/`, `.opencode/skills/`, `.claude/skills/` | `.agents/skills/`, `.github/skills/` |
| **Project Subagents** | `.agents/agents/<name>.md` (`agents/*/agent.md`) | `.claude/agents/<name>.md` | `.codex/agents/<name>.toml` (recursive in trusted projects) | `.cursor/agents/*.md`, `.claude/agents/*.md`, `.codex/agents/` | `.opencode/agents/*.md` or `ctx.agent.transform` in `.opencode/plugins/*.js` | `.github/agents/*.agent.md`, `.claude/agents/*.md` |
| **Project Hooks** | `.agents/hooks.json` (flat lifecycle array; nested tool matcher) | `.claude/settings.json` / `.claude/settings.local.json` (nested matchers) | `.codex/hooks.json` or `[hooks]` in `.codex/config.toml` (trusted projects) | `.cursor/hooks.json` (`version: 1`, camelCase events) | `.opencode/plugins/*.{ts,js}` (`ctx.session.hook("context", ...)`) | `.claude/settings.json`, `.github/hooks/*.json` |
| **Project MCP Config** | `.agents/mcp_config.json` (or `~/.gemini/antigravity/mcp_config.json`) | `.mcp.json` (`mcpServers` at repo root) | `.mcp.json` or `[mcp_servers.<name>]` in `.codex/config.toml` | `.cursor/mcp.json` (`mcpServers`; `${workspaceFolder}`) | `opencode.json` (`mcp.servers.<name>`) or `ctx.mcp.transform` | `.vscode/mcp.json` (`servers` object) |

## Workflow

1. **Choose the Target Scope**:
   - **Project-Local (`.agents/` inside a repository)**: Used by `/flow:setup`, `/flow:learn`, and repository maintainers to store `.agents/bundles/` knowledge, `.agents/skills/<domain>/` domain and review skills, `.agents/agents/<name>.md` subagents, `.codex/agents/<name>.toml` agents, and `.agents/mcp_config.json` / `.mcp.json` server definitions.
   - **Extension-Wide Plugin (Plugin Repository Root)**: Used when packaging reusable skills, subagents, hooks, rules, and MCP servers as an installable plugin across all six harnesses.
2. **Author Progressive-Disclosure Skills**:
   - Keep every `SKILL.md` concise (`<= 200` lines and strictly `< 24,000` bytes so Google Antigravity never truncates the bottom of the file).
   - Start `description` with `Use when ...` (`<= 500` characters) and avoid vague prefixes (`Auto-activate`, `Produces`, `Expert knowledge`, `Comprehensive`).
   - Put detailed schemas, checklists, and examples in `references/*.md` files linked from `SKILL.md`.
3. **Author Compatible Subagents**:
   - Format Markdown subagents (`agents/<name>.md` or `.agents/agents/<name>.md`) with `name`, `description`, `model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy`, `skills: [...]`, and `readonly: true` + YAML list `disallowedTools` for read-only reviewers.
   - Use top-level H1 (`# `) section headings (`# Role & Identity`, `# Responsibilities`, `# Verification & Constraints`, `# Output Contract`) with `###` subsections so Antigravity splits sections into XML system-prompt blocks.
   - Pair Markdown subagents with `.codex/agents/<name>.toml` for Codex CLI.
4. **Keep Runtime Hooks Zero-Dependency & Cross-Platform**:
   - Do not require `python3`, `node`, or `jq` in `SessionStart` shell hooks (`agy` and `codex` ship as static native binaries).
   - Pair pure POSIX `sh` + `awk` (`hooks/<name>.sh`) with native PowerShell (`hooks/<name>.ps1`, `pwsh` / Windows PowerShell 5.1+) and `"commandWindows"` for Windows hosts, plus `.opencode/plugins/<name>.js` in native `node:fs` / `node:path`.
5. **Validate Structural Parity**:
   - Run `/flow:validate` to verify `SKILL.md` byte budgets, subagent frontmatter and H1 headings, hook schemas, and relative links.

## Guardrails

- **No Duplicate Surface Mirrors**: Never maintain `plugins/<name>/` mirrors, root `CLAUDE.md` files alongside `AGENTS.md` (breaks `claude plugin validate --strict` and double-loads with `AGENTS.md` in Cursor), `.github/agents/*.agent.md` copies, `.opencode/agents/*.md` copies, or `commands/` wrappers.
- **Strict `24 KB` `SKILL.md` Cap**: Never exceed `24,000` bytes in any `SKILL.md` file.
- **YAML List Tool Restrictions**: Always format `tools` and `disallowedTools` as YAML lists (`- Edit`), never comma-separated strings (`tools: Read, Grep` fails YAML unmarshaling in Antigravity and silently drops the subagent).
- **Short MCP Server & Tool Names**: Keep combined MCP tool names under `60` characters (`^[a-zA-Z0-9_-]+$`) so Cursor (`59`-char cap) and Antigravity (`64`-char cap on `mcp_<plugin>_<server>_<tool>`) never drop or truncate tools.

## References

- [Skills, Subagents, Local `.agents/`, & MCP Limits](references/skills-subagents-and-mcp-limits.md) — How each harness loads `.agents/` folders, local MCP configs (`.agents/mcp_config.json`, `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `opencode.json`), H1 subagent sections, and Antigravity's Python `run_workflow` API.
- [Hooks & Runtime Portability](references/hooks-and-runtime-portability.md) — Project-local and plugin hook schemas (flat Antigravity lifecycle hooks vs. nested Claude/Codex matchers), stdout JSON keys, Cursor deduplication, and OpenCode V2 `setup(ctx)`.
- [Manifests & Single-Root Packaging](references/manifests-and-packaging.md) — Root layout and manifest schemas for `plugin.json`, `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.agents/plugins/marketplace.json`, `package.json`, and OpenCode V2.

## Validation

- Confirm every `SKILL.md` has `name` and `description` (`Use when ...`, `<= 500` chars) and is `< 24,000` bytes.
- Confirm every subagent in `agents/*.md` or `.agents/agents/*.md` includes `model: inherit`, `mainAgent: false`, `subagent: true`, H1 (`# `) section headings, and YAML list `disallowedTools` on read-only agents.
- Confirm all relative Markdown links resolve on disk.

## Example

Invoke this skill when scaffolding project-local skills, subagents, hooks, or MCP configs under `.agents/` during `/flow:setup` or `/flow:learn`, or when authoring an extension-wide multi-harness plugin.
