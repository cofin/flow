---
name: project-bootstrap
description: Analyze a project and bootstrap reusable assistant workflows (Claude Code + Gemini CLI) with current, official folder conventions.
---

# Project Bootstrap Skill

Analyze a repository, identify patterns, and scaffold reusable local workflows with current assistant conventions.

## When to Use

Use when the user asks to bootstrap a project, set up reusable commands/skills, or standardize assistant workflows.

## Scope and Output

Produce a concise bootstrap plan and create only the requested artifacts.

1. Project analysis summary
2. Recommended workflow artifacts
3. Exact install paths used
4. Quick usage examples

## Bootstrap Process

### 1. Analyze the project

1. Identify stack and tooling from root manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.).
2. Identify testing, linting, formatting, CI, and architecture conventions.
3. Detect existing assistant config and avoid duplicating it.

### 2. Choose target surfaces

Use the smallest useful set.

1. `Claude Code` skills/subagents
2. `Gemini CLI` custom commands and (if requested) extensions

### 3. Create starter workflows

Prefer a minimal starter set the team can evolve.

1. `prd` flow
2. `implement` flow
3. `explore-codebase` flow
4. `test-feature` flow

Keep prompts short, opinionated, and aligned to detected project patterns.

## Canonical Paths (Verified)

### Claude Code

1. Personal skills: `~/.claude/skills/<skill-name>/SKILL.md`
2. Project skills: `.claude/skills/<skill-name>/SKILL.md`
3. Personal subagents: `~/.claude/agents/*.md`
4. Project subagents: `.claude/agents/*.md`
5. Legacy commands still work: `.claude/commands/*.md` and `~/.claude/commands/*.md`, but skills are the recommended default.

### Gemini CLI

1. User commands: `~/.gemini/commands/*.toml`
2. Project commands: `.gemini/commands/*.toml`
3. Extensions install directory: `~/.gemini/extensions/<extension-name>/`
4. Extension manifest: `~/.gemini/extensions/<extension-name>/gemini-extension.json`
5. Extension-provided commands: `commands/*.toml` inside the extension directory

Note: Gemini CLI loads extensions from the user extension directory on startup; keep extension assets inside that extension folder structure.

## Guardrails

1. Reuse existing conventions before introducing new structure.
2. Keep generated workflows concise and composable.
3. Do not overwrite existing assistant assets unless asked.
4. For monorepos, prefer project-local artifacts near the owning package when appropriate.

## Learn More (Official)

### Claude Code

- Skills (recommended, includes where skills live): https://code.claude.com/docs/en/skills
- Subagents (locations and format): https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Slash commands (legacy/custom command behavior): https://docs.anthropic.com/en/docs/claude-code/slash-commands

### Gemini CLI

- Custom commands (locations and precedence): https://google-gemini.github.io/gemini-cli/docs/cli/custom-commands.html
- Extensions (install/update and extension folder layout): https://google-gemini.github.io/gemini-cli/docs/extensions/
