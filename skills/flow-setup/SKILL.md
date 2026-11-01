---
name: flow-setup
description: "Use when initializing or aligning Flow in a repository, migrating legacy .agents/ layouts, scaffolding OKF v0.2 knowledge bundles, or generating baseline and domain .agents/skills/ and .agents/agents/."
disable-model-invocation: true
---

# Flow Setup

<!-- lifecycle-ownership: owner=flow-setup; operations=setup -->

## Trigger

Use for `/flow:setup`. Follow [`../flow/references/setup.md`](../flow/references/setup.md).

## Workflow

1. **Environment Detection, Brownfield Alignment, & Toolchain Discovery**:
   - Inspect `.agents/setup-state.json` and `.agents/bundles/index.md`. If `.agents/` already exists, offer **Align & True-Up (Recommended)**, **Full Re-Setup**, or **Exit**.
   - In alignment/brownfield mode, inventory legacy layouts (`.beads/`, `.agents/specs/`, `.agents/tracks/`, `.agents/transactions/`, flat `knowledge/patterns.md`, un-promoted `bundles/research/`, legacy `.agents/skills/flow-memory-keeper/`), migrate active work and nested `knowledge/**` paths without data loss, and scrub obsolete tracker references after user confirmation.
   - Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) alongside repository manifests (`pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Makefile`, CI workflows). When `run_workflow` is available on Google Antigravity, fan out `parallel()` `@researcher` subsystem audits (`model="inherit"`).
2. **Scaffold Core Context Chapters & Rich OKF v0.2 Bundle (`.agents/bundles/`)**:
   - Initialize `.agents/bundles/index.md` (`okf_version: "0.2"`) and `.agents/bundles/log.md`.
   - Create Flow's core context chapters with bounded `<= 40`-line `<!-- truth: start -->` blocks: `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, and `knowledge/workflow.md` (populated with verified host commands from [`../../templates/agent/workflow.md`](../../templates/agent/workflow.md)).
   - Synthesize evidence-backed nested chapters across `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/` with `sources: [{ id, resource, title }]` + `[^id]` footnotes and `verified: [{ by, at }]`.
3. **Seed Baseline Engineering Disciplines & Stack-Specific Project-Local Skills (`.agents/skills/`) and Subagents (`.agents/agents/`)**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) and [`../flow-docs/references/agent-context.md`](../flow-docs/references/agent-context.md).
   - Embed baseline engineering rules into the repository's knowledge and skill set: **Deep-Module & Seam Design** (Module / Interface / Seam / Adapter boundaries, dependency categories, interface alternatives comparison), **Active Domain Modeling & ADR Filter** (*hard to reverse + surprising without context + genuine trade-off*), **Public-Seam Vertical-Slice TDD & Hypothesis-Driven Bug Diagnosis**, and **Cold-Reader Prose & Documentation Accuracy**.
   - Generate consolidated domain skills (`.agents/skills/<domain>/SKILL.md` `<= 200` lines + `references/*.md`), domain review capability skills (`.agents/skills/review-<domain>/SKILL.md` + `references/checklist.md` + `references/false-positive-suppressions.md`), `.agents/skills/index.md`, and paired project-local subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md` with H1 `# ` headings, `mainAgent: false`, `subagent: true`, and `model: inherit`).
4. **Cross-Harness Policy Bootstrap, `AGENTS.md`, & `.agents/setup-state.json`**:
   - Ask once via `structured-choice-v1` whether `.agents/` is **`shared`** (tracked in Git, Recommended) or **`local-only`** (stealth mode via `.git/info/exclude`).
   - Offer opt-in non-destructive harness policy merges (`.claude/settings.local.json` with backup, `opencode.json`), update root `AGENTS.md` (preserving `<!-- project-customization: start -->` blocks), and write `.agents/setup-state.json`.

## Guardrails

- Never copy Flow's global plugin skills (`flow`, `flow-*`, `okf`, `debloat`, `multi-harness-plugins`) or legacy `flow-memory-keeper` into `.agents/skills/`.
- Every materialized knowledge chapter must cite real repository paths (`path/to/file::Symbol`) in `sources:` and `[^id]` footnotes.
- Preserve existing custom content inside `<!-- project-customization: start -->` and `<!-- truth: start -->` blocks during alignment.

## Output

Return the initialized or aligned `.agents/bundles/` tree, generated `.agents/skills/` and `.agents/agents/` inventory, verified host commands, and next command (`/flow:plan` or `/flow:prd`).

## Validation

Confirm root `index.md` declares `okf_version: "0.2"`, all links in `index.md` and `.agents/skills/index.md` resolve on disk, every non-reserved `.md` file has valid OKF frontmatter, and `.agents/setup-state.json` records `setup_status: "complete"`.
