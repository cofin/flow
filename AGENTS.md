# Flow Project Context

Flow is a multi-harness Spec-Driven Development plugin for **Google Antigravity**, **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / Copilot**. Flow has no `flow` shell executable; invoke the [`flow`](skills/flow/SKILL.md) skill or a `/flow:*` command.

## Architecture & Routing

- **Lifecycle Router**: [skills/flow/SKILL.md](skills/flow/SKILL.md) routes across [`flow-setup`](skills/flow-setup/SKILL.md) (`setup`), [`flow-planning`](skills/flow-planning/SKILL.md) (`prd`, `plan`, `revise` [alias `refine`], `research` [alias `task`]), [`flow-execution`](skills/flow-execution/SKILL.md) (`implement`, `status`), [`flow-learn`](skills/flow-learn/SKILL.md) (`learn` [aliases `resynthesize`, `refresh`, `sync`]), [`flow-docs`](skills/flow-docs/SKILL.md) (`docs` [subcommands `write`, `validate`, `capture`, `sync`, `pr`]), and [`flow-completion`](skills/flow-completion/SKILL.md) (`review`, `finish`, `archive`, `cleanup`, `revert`, `validate`).
- **Foundation & Harness Skills**: [`okf`](skills/okf/SKILL.md) (`OKF v0.2` knowledge bundles and provenance), [`debloat`](skills/debloat/SKILL.md) (deep-module deletion test, public-seam test strength, and anti-slop prose/context pruning), and [`multi-harness-plugins`](skills/multi-harness-plugins/SKILL.md) (project-local `.agents/` and multi-harness skill, subagent, hook, rule, and MCP standards).
- **Stateful Planning vs. Zero-Context Verification & Execution**: Stateful Co-Designers/Adjudicators (`@prd-orchestrator`, `@plan-generator`) enforce clear problem framing, mandatory alternatives comparison, deep-module seams, and the Zero-Decision Implementation Readiness Standard; Zero-Context Reviewers & Isolated Executors (`@code-reviewer`, `@quality-reviewer`, `@researcher`, `@executor`) operate under Zero-Context Isolation Rules, Public-Seam Vertical-Slice TDD, and the Hypothesis-Driven Bug Diagnosis Loop.
- **Direct Markdown State Contract**: Task worksheets (`.agents/bundles/specs/<flow_id>/tasks/<id>-<slug>.md`) and specifications (`.agents/bundles/specs/<flow_id>/spec.md`) are the sole authority for task state and commits ([`skills/flow/references/state.md`](skills/flow/references/state.md)).

## Discipline

Initialize with [the setup guide](skills/flow/references/setup.md), then use `.agents/bundles/index.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`. Execute one worksheet per subagent turn (`model: inherit`), preserve unrelated work, stage exact paths, and commit locally only after verification passes. Never create or mutate Git tags. Pushes and remote writes require explicit user instruction.
