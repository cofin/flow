# Flow for Claude Code

Use the Flow skill for context-driven development workflows in repositories that use `.agents/`.

> **Flow is a skill, not a CLI.** There is no `flow` executable. Never run `flow` as a shell command. Invoke the Flow skill or use slash commands (e.g. `/flow:plan`, `/flow:implement`, `/flow:sync`, `/flow:review`).

## Core Conventions

- **Task Persistence**: All planning artifacts and task files live under `.agents/bundles/specs/<flow_id>/` (`spec.md` and `tasks/*.md`).
- **Direct Frontmatter Sync**: Reconcile `spec.md` checklist markers directly from task file frontmatter via `/flow:sync`.
- **Knowledge Base**: Project context and conventions live in `.agents/bundles/knowledge/` and `.agents/bundles/product/`.

## Lifecycle Routing

Route operations to the dedicated Flow lifecycle skills:

- **Setup & Alignment**: `skills/flow-setup/SKILL.md` (`/flow:setup`)
- **Planning & Refinement**: `skills/flow-planning/SKILL.md` (`/flow:prd`, `/flow:plan`, `/flow:refine`, `/flow:revise`)
- **Implementation & TDD**: `skills/flow-execution/SKILL.md` (`/flow:implement`)
- **Sync & Status**: `skills/flow-sync-status/SKILL.md` (`/flow:sync`, `/flow:status`, `/flow:refresh`)
- **Review, Docs & Finish**: `skills/flow-completion/SKILL.md` (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:docs`, `/flow:validate`)

## Operational Protocol

- **Refined Tasks First**: Refine task worksheets with concrete public seams, test commands, and steps before dispatching executors.
- **Seam-First TDD**: Run failing verification tests (red) before writing code, and pass tests cleanly (green) before closing tasks.
- **Atomic Commits**: Stage touched files and create signed Git commits with the recorded commit SHA.
- **Git Boundaries**: Work on the active branch; never push force or mutate Git tags.
