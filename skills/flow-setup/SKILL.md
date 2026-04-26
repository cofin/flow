---
name: flow-setup
description: "Use when initializing Flow in a repo, configuring .agents, installing or checking Beads bd, setting local-only sync policy, or creating first project context files."
---

# Flow Setup

Use this lifecycle skill for project initialization, installation checks, setup validation, and first context files.

## Workflow

1. Detect project root, existing `.agents/` state, Beads availability, and repo-native commands.
2. If Beads is missing, offer official Beads (`bd`) installation or no-Beads degraded mode.
3. Initialize Flow context files from templates and prefer local-only Beads settings.
4. Store setup decisions in Beads notes when a backend exists.
5. Re-run setup validation before handing off to planning.

## Guardrails

- Prefer `.git/info/exclude` for local-only ignores.
- Do not edit `.gitignore` unless the user wants shared repository policy.
- Do not run `bd dolt push`, export, or auto-stage unless policy explicitly allows it.
- Keep setup idempotent; preserve existing user context files and merge rather than overwrite.

## Validation

- Confirm `.agents/` root, `workflow.md`, `patterns.md`, `knowledge/index.md`, and Beads config existence when setup is expected.
- Confirm Beads config defaults are local-only: no git ops, no auto export, and no auto git add.
- Run repository validation commands documented in `.agents/workflow.md` or hook context.

## References Index

- [Setup command details](../flow/references/setup.md)
- [Validate command details](../flow/references/validate.md)
- [Refresh command details](../flow/references/refresh.md)

## Example

User: "Use Flow to set up this repo."

Action: detect the repo root, initialize `.agents/`, configure local-only Beads, capture setup notes, validate files, then hand off to `flow-planning` for the first flow.
