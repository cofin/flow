---
name: flow
description: "Project-tailored Flow router. Use when executing lifecycle commands, task tracking, spec planning, TDD implementation, review, or status in this repository."
---

# Flow Router (Project-Tailored)

<!-- lifecycle-ownership: owner=flow; operations= -->

## Project Context

- **Knowledge Base:** `.agents/bundles/knowledge/`
- **Specs Directory:** `.agents/bundles/specs/`

## Trigger

Use Flow whenever `.agents/` exists, spec bundles live under `.agents/bundles/specs/`, or the request names a Flow lifecycle action (`/flow-plan`, `/flow-implement`, `/flow-sync`, `/flow-finish`, etc.).

> **Flow is a skill, not a CLI.** Never run `flow` as a shell command.

## Routing Table

Route the requested operation directly to its tailored project-local lifecycle skill:

| Requested Operation | Target Project-Local Skill | File Location |
| :--- | :--- | :--- |
| `setup` | `flow-setup` | Global or `.agents/skills/flow-setup/` |
| `prd`, `plan`, `refine`, `revise`, `research`, `task` | `flow-planning` | `.agents/skills/flow-planning/SKILL.md` |
| `implement` | `flow-execution` | `.agents/skills/flow-execution/SKILL.md` |
| `sync`, `status`, `refresh` | `flow-sync-status` | `.agents/skills/flow-sync-status/SKILL.md` |
| `review`, `finish`, `archive`, `revert`, `docs`, `cleanup`, `validate` | `flow-completion` | `.agents/skills/flow-completion/SKILL.md` |

## Workflow

1. Identify the requested operation from the user prompt or slash command.
2. Load the corresponding project-local skill from `.agents/skills/<skill-name>/SKILL.md`.
3. Hand off the request to the owning skill.

## Guardrails

- The router owns no lifecycle operations and makes no file mutations.
- Prefer project-local tailored skills under `.agents/skills/` over generic global skills.
- Preserve Git history and tag immutability.

<!-- project-customization: start -->
## Project Routing Nuances
- Consult `.agents/bundles/knowledge/architecture/` for subsystem boundaries.
<!-- project-customization: end -->
