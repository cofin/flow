---
name: flow-setup
description: "Use when initializing Flow in a repository, configuring .agents/bundles/, synthesizing OKF v0.2 knowledge chapters, or generating project-local .agents/skills/ and .agents/agents/."
disable-model-invocation: true
---

# Flow Setup

<!-- lifecycle-ownership: owner=flow-setup; operations=setup -->

## Trigger

Use for `/flow:setup`. Follow [`../flow/references/setup.md`](../flow/references/setup.md).

## Workflow

1. **Toolchain & Repository Discovery**: Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`) alongside repository manifests (`pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Makefile`, CI workflows) and existing `.agents/` files. When `run_workflow` is available, fan out `parallel()` `@researcher` subsystem audits with `model="inherit"`.
2. **Scaffold & Populate Rich OKF v0.2 Bundle (`.agents/bundles/`)**:
   - Initialize `.agents/bundles/index.md` (`okf_version: "0.2"`) and `.agents/bundles/log.md`.
   - Create `product/{index,product,product-guidelines,tech-stack}.md`.
   - Create `knowledge/index.md`, `knowledge/workflow.md`, and evidence-backed nested chapters across `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/` with `sources: [{ id, resource, title }]` + `[^id]` footnotes, `verified: [{ by, at }]`, and bounded `<= 40`-line `<!-- truth: start -->` blocks.
3. **Dynamically Generate Project-Local Domain & Review Skills (`.agents/skills/`) and Paired Subagents (`.agents/agents/`)**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) so generated `.agents/skills/` and `.agents/agents/` work across all harnesses.
   - Synthesize consolidated engineering domain skills (`.agents/skills/<domain>/SKILL.md` `<= 200` lines + `references/*.md`), domain review capability skills (`.agents/skills/review-<domain>/SKILL.md` + `references/checklist.md` + `references/false-positive-suppressions.md`), and `.agents/skills/index.md`.
   - Generate paired project-local subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md`) using H1 (`# `) section headers, `mainAgent: false`, `subagent: true`, and `model: inherit`.
4. **Update Workspace `AGENTS.md` & Write `.agents/setup-state.json`**:
   - Ensure root `AGENTS.md` routes to `.agents/bundles/index.md` and `.agents/skills/index.md` while preserving `<!-- project-customization: start -->` blocks.
   - Write `.agents/setup-state.json` (`setup_status: "complete"`, `bundle_root: ".agents/bundles"`, `okf_version: "0.2"`).

## Guardrails

- Never copy Flow's global skills (`flow`, `flow-*`, `okf`, `debloat`) or legacy `flow-memory-keeper` into `.agents/skills/`.
- Every materialized knowledge chapter must cite real repository paths (`path/to/file::Symbol`) in `sources:` and `[^id]` footnotes.
- Preserve existing custom content inside `<!-- project-customization: start -->` blocks.

## Output

Return the initialized `.agents/bundles/` tree, generated `.agents/skills/` and `.agents/agents/` inventory, verified toolchain commands, and next command (`/flow:plan` or `/flow:prd`).

## Validation

Confirm root `index.md` declares `okf_version: "0.2"`, all links in `index.md` and `.agents/skills/index.md` resolve on disk, every non-reserved `.md` file has valid OKF frontmatter, and `.agents/setup-state.json` records `setup_status: "complete"`.
