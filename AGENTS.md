# Flow Project Context

Flow is a unified toolkit for Context-Driven Development.

> **Flow is a skill, not a CLI.** There is no `flow` executable. Never run `flow` as a shell command. Use the Flow lifecycle skills or slash commands (e.g. `/flow:plan`, `/flow:implement`, `/flow:sync`, `/flow:review`).

## The Task-First Mandate

1. **Specs & Worksheets**: All plans and tasks live under `.agents/bundles/specs/<flow_id>/`. The roadmap is defined in `spec.md`, and atomic task worksheets live in `tasks/<short_id>.md`.
2. **Task State Authority**: Task files (`tasks/*.md`) are the sole authority for task state (`open`, `in_progress`, `closed`, `blocked`, `skipped`) and commit SHAs following [skills/flow/references/state.md](skills/flow/references/state.md).
3. **Direct Frontmatter Sync**: Use `/flow:sync` to reconcile `spec.md` checklist markers directly from task file frontmatter.
4. **Task Discoveries**: Append findings to the task worksheet under `## Notes & Discoveries`.

### Spec File Schema (`spec.md`)

```yaml
---
type: Spec
flow_id: example-feature
title: Example Feature
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
description: Feature description.
---
```

### Task File Schema (`tasks/<short_id>.md`)

```yaml
---
type: Task
id: example-feature:001
flow_id: example-feature
title: Implement Seam
state: open
priority: P2
estimate_minutes: 30
dependencies: []
required_skills: [flow-execution]
commit: null
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
```

## Lifecycle Routing

Route operations directly to the dedicated Flow skill:

- **Setup & Alignment**: `skills/flow-setup/SKILL.md` (`/flow:setup`)
- **Planning & Refinement**: `skills/flow-planning/SKILL.md` (`/flow:prd`, `/flow:plan`, `/flow:refine`, `/flow:revise`)
- **Implementation & TDD**: `skills/flow-execution/SKILL.md` (`/flow:implement`)
- **Sync & Status**: `skills/flow-sync-status/SKILL.md` (`/flow:sync`, `/flow:status`, `/flow:refresh`)
- **Review, Docs & Finish**: `skills/flow-completion/SKILL.md` (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:docs`, `/flow:validate`)

## Auto-Activation

Auto-activate Flow lifecycle skills when `.agents/` or `.agents/bundles/specs/` exists in the repository.

## Project Context Index

Resolve all project context and architecture through `.agents/bundles/`:

- **Bundle Root Index**: `.agents/bundles/index.md`
- **Product Definition**: `.agents/bundles/product/product.md`
- **Tech Stack & Invariants**: `.agents/bundles/product/tech-stack.md`
- **Canonical Workflow & Commands**: `.agents/bundles/knowledge/workflow.md`
- **Architecture & Deep Modules**: `.agents/bundles/knowledge/architecture/`
- **Data Models & Schemas**: `.agents/bundles/knowledge/data-model/`
- **Domain Glossaries**: `.agents/bundles/knowledge/domains/`
- **Architectural Decisions (ADRs)**: `.agents/bundles/knowledge/decisions/`
- **Rejection Memory (Out-of-Scope)**: `.agents/bundles/knowledge/rejections/`
- **Patterns & Elevated Conventions**: `.agents/bundles/knowledge/patterns.md`
- **Research Documents**: `.agents/bundles/research/`
- **Active Flow Specifications**: `.agents/bundles/specs/<flow_id>/`
- **Archived Flows**: `.agents/bundles/archive/<year>/<flow_id>/`

## Operational Guardrails

- **Single-Task Execution**: Subagents execute exactly one task worksheet per invocation.
- **Empirical Test Verification**: Confirm tests fail on the missing behavior (red) before implementing code, and pass cleanly (green, exit code 0) before closing tasks.
- **Atomic Commits**: Record the 7+ character Git commit SHA in task frontmatter upon completion.
- **Git Safety**: Create signed commits on the working branch. Tags and remote pushes remain explicit user actions.
