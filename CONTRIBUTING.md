# Flow Project Context

Flow is a multi-harness Spec-Driven Development plugin for **Google Antigravity**, **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / Copilot**. Flow has no `flow` shell executable; invoke the [`flow`](skills/flow/SKILL.md) skill or a `/flow:*` command.

## Architecture & Routing

- **Lifecycle Router**: [skills/flow/SKILL.md](skills/flow/SKILL.md) routes across [`flow-setup`](skills/flow-setup/SKILL.md) (`setup`), [`flow-planning`](skills/flow-planning/SKILL.md) (`prd`, `spec`, `revise`, `research`), [`flow-execution`](skills/flow-execution/SKILL.md) (`implement`, `status`), [`flow-learn`](skills/flow-learn/SKILL.md) (`learn`, `refresh`, `sync`), [`flow-docs`](skills/flow-docs/SKILL.md) (`docs`), and [`flow-completion`](skills/flow-completion/SKILL.md) (`review`, `finish`, `archive`, `cleanup`, `revert`, `validate`).
- **Foundation & Harness Skills**: [`okf`](skills/okf/SKILL.md) (`OKF v0.2` knowledge bundles and provenance), [`debloat`](skills/debloat/SKILL.md) (deep-module deletion test, public-interface test strength, and prose pruning), and [`multi-harness-plugins`](skills/multi-harness-plugins/SKILL.md) (local `.agents/` and cross-harness plugin standards).
- **Planning, Execution, & Independent Review**: Planners (`@prd-orchestrator`, `@plan-generator`) default cohesive features to one single-chapter `spec.md` (`has_chapters: false`) and split into `ch01-<slug>/..chNN-<slug>/` only at real checkpoints or independent subsystems. Model roles (`strong`, `standard`, `fast`, `light`), task briefs (`<= 250` LOC, `<= 3` files), and `flow-cli.mjs spec sync` are defined in [`skills/flow/references/orchestration.md`](skills/flow/references/orchestration.md). Independent reviewers and isolated workers (`@code-reviewer`, `@quality-reviewer`, `@researcher`, `@executor`) use read lists, parallel steps (`<= 4` workers), public-interface TDD, and cross-harness `Stop` completion checks.
- **Present-Tense Markdown State Contract**: Root specs (`.agents/bundles/specs/<flow_id>/spec.md`), chapter catalogs (`chapters/index.md`), chapter specs (`chapters/<ch_id>/spec.md`), and task worksheets (`tasks/<id>-<slug>.md`) stay synced in place in present tense ([`skills/flow/references/state.md`](skills/flow/references/state.md)).

## Development & Verification

- **Plugin Root Hygiene**: Keep the root free of `AGENTS.md` and `CLAUDE.md` so `make lint` and plugin validation pass. Place contributor instructions in `CONTRIBUTING.md` and workspace-scoped Antigravity rules in `.agents/rules/`.
- **Quality Checks**: Run `make check` locally before committing or opening a pull request.

## Discipline

Initialize with [the setup guide](skills/flow/references/setup.md), then use `.agents/bundles/index.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`. Execute one active chapter per `/flow:implement` run (or consecutive ready chapters with `--all`), splitting `> 4`-task chapters across parallel workers on separate files (`<= 3` writers, `tasks_per_worker` default `4`) or `chapter_batch` chunks. Run the `< 60s` chapter check, sync present-tense OKF/docs, and pass independent chapter review before stopping. Preserve unrelated work, stage exact paths, and commit locally only after verification passes. Never create or mutate Git tags, and never push without explicit user instruction.
