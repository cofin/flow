---
name: integrating-agent-platforms
description: "Use when installing, updating, packaging, or troubleshooting Flow integrations across Claude Code, Gemini CLI, Codex CLI, OpenCode, Cursor, VS Code/Copilot, OpenClaw, or Google Antigravity."
---

# Integrating Agent Platforms

## Overview

Use official host-native install and update flows first. Keep the shared mental model consistent across hosts: install source, update path, cache behavior, local-vs-shared scope, and restart requirements.

<workflow>

1. Prefer the platform's official marketplace, extension, or plugin system.
2. Use git-backed installs where the host officially supports them.
3. Reserve local links and wrapper files for development or hosts without a first-class git install story.
4. Explain what is copied, what is linked, what is cached, and when a restart is required.

- **Claude Code:** Prefer marketplace install and marketplace update commands.
- **Gemini CLI:** Prefer `gemini extensions install` from GitHub and `gemini extensions update`. Use `link` only for local development.
- **Codex CLI:** Treat the plugin manifest and marketplace as the source of truth. Distinguish repo marketplace metadata from the installed cached copy.
- **OpenCode:** Follow local plugin directory and skills discovery rules. Do not imply undocumented git-url plugin installs are the default.
- **Google Antigravity:** Prefer workspace-local `.agents` customization when supported by the current build; keep global fallback guidance available.

</workflow>

<guardrails>

- Prefer user-scoped installs for personal tooling.
- Use project-scoped or workspace-scoped registration only when the team should inherit it.
- When local-only ignores are needed, prefer `.git/info/exclude` before `.gitignore`.
- Do not present undocumented install paths as if they were official.
- Distinguish source checkout, installed copy, and cache behavior when the host does.

</guardrails>

<validation>

Before giving host-integration guidance, verify:

- [ ] The install path is host-native when one exists
- [ ] Update/refresh commands are current for the target host
- [ ] Scope is clear: user, project, workspace, or local
- [ ] Cache/copy/link behavior is explained when it affects updates
- [ ] Restart requirements are called out when relevant

</validation>

<example>

Example framing:

- "Gemini CLI should use the GitHub-backed extension install flow. Use `link` only for local development against a checkout."

</example>

## Reference

Read [references/host-matrix.md](references/host-matrix.md) when you need exact host-by-host guidance.
