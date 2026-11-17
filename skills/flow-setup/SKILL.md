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
   - Inspect `.agents/setup-state.json` and `.agents/bundles/index.md`. If `.agents/` already exists, offer **Align & Sync (Recommended)**, **Full Re-Setup**, or **Exit**.
   - Inventory legacy layouts (`.beads/`, `.agents/specs/`, `.agents/tracks/`, `.agents/transactions/`, flat `knowledge/patterns.md`, un-promoted `bundles/research/`). Ensure subdirectory `index.md` files and `log.md` have no YAML frontmatter or standalone `---` body rules. Inspect fragmented specs via `node <plugin_root>/sidecars/studio/flow-cli.mjs spec status` and migrate active work after user confirmation.
   - Probe installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) alongside repository manifests. Fan out parallel read-only `@researcher` workers (`type_name="self"` with `agents/researcher.md` on Google Antigravity; `model="inherit"`).
2. **Scaffold Core Context Chapters & OKF v0.2 Bundle (`.agents/bundles/`)**:
   - Initialize `.agents/bundles/index.md` (`okf_version: "0.2"`) and frontmatter-free `.agents/bundles/log.md`, `product/index.md`, `knowledge/index.md`, `research/index.md`, and `specs/index.md`.
   - Create core context chapters with `<= 40`-line `<!-- truth: start -->` blocks and zero body `---` separators. Include `product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, and `knowledge/workflow.md` using verified host commands from [`../../templates/agent/workflow.md`](../../templates/agent/workflow.md).
   - Write evidence-backed nested chapters across `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/` with `sources: [{ id, resource, title }]`, `[^id]:` footnotes, and `verified: [{ by, at }]`. Use parallel domain workers when `>= 2` domains exist.
3. **Seed Engineering Disciplines, Project Skills, & Subagents**:
   - Follow [`../multi-harness-plugins/SKILL.md`](../multi-harness-plugins/SKILL.md) and [`../flow-docs/references/agent-context.md`](../flow-docs/references/agent-context.md).
   - Embed baseline engineering rules into the knowledge and skill set: deep-module design, domain modeling and ADRs, public-interface TDD, bug diagnosis, and present-tense documentation for first-time readers.
   - Generate domain skills (`.agents/skills/<domain>/SKILL.md` `<= 200` lines + `references/*.md`), review skills (`.agents/skills/review-<domain>/SKILL.md` + `references/checklist.md` + `references/false-positive-suppressions.md`), and `.agents/skills/index.md`. Pair them with project subagents (`.agents/agents/<domain>-reviewer.md` and `.agents/agents/<domain>-specialist.md`) using H1 headings, `mainAgent: false`, `subagent: true`, `model: inherit`, and `commandExecutionPolicy: sandbox`.
4. **Worktrees, Permissions, `Stop` Hooks, `AGENTS.md`, & Setup State**:
   - Ask once whether `.agents/` is **`shared`** (tracked in Git, Recommended) or **`local-only`** (stealth mode via `.git/info/exclude`). In linked `git worktree` checkouts, edit worktree `.agents/` when `shared` or the primary checkout's `.agents/` when `local-only`, and verify `.venv` / `node_modules` symlinks.
   - Offer opt-in non-destructive harness permissions (`.claude/settings.local.json` with backup, Codex `writable_roots`, `.cursor/hooks.json`, `opencode.json`). Update root `AGENTS.md` (preserving `<!-- project-customization: start -->` blocks) and write `.agents/setup-state.json` (`workflow_preferences.ignore_policy`, `workflow_preferences.model_routing: "auto"`).

## Guardrails

- Never copy Flow's global plugin skills (`flow`, `flow-*`, `okf`, `debloat`, `multi-harness-plugins`) into `.agents/skills/`.
- Every materialized knowledge chapter must cite real repository paths (`path/to/file::Symbol`) in `sources:` and `[^id]` footnotes.
- Preserve existing custom content inside `<!-- project-customization: start -->` and `<!-- truth: start -->` blocks during alignment.

## Output

Return the initialized or aligned `.agents/bundles/` tree, generated `.agents/skills/` and `.agents/agents/` inventory, verified host commands, and next command (`/flow:spec` or `/flow:prd`).

## Validation

Confirm root `index.md` declares `okf_version: "0.2"`, all links in `index.md` and `.agents/skills/index.md` resolve on disk, every non-reserved `.md` file has valid OKF frontmatter, and `.agents/setup-state.json` records `setup_status: "complete"`.
