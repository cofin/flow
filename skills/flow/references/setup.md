# Flow Setup (`/flow:setup`)

Initialize or align a repository for Spec-Driven Development with Flow's core project context chapters, a hierarchical OKF v0.2 knowledge bundle (`.agents/bundles/`), baseline and stack-specific project-local skills (`.agents/skills/`), and paired project-local subagents (`.agents/agents/`).

## Phase 0: Environment Detection & Brownfield Alignment Mode

1. **Check Existing State**:
   - Inspect `<hook_context>`, `.agents/setup-state.json`, and `.agents/bundles/index.md`.
   - Treat `setup_status: "complete"` as a claim to verify against current files, never as blind proof.
   - If `.agents/` already exists, ask via `structured-choice-v1` ([`interaction.md`](interaction.md)):
     - `align` — **Align & True-Up (Recommended)**: Validate and migrate existing `.agents/` artifacts, resynthesize drifted knowledge/skills via [`learn.md`](learn.md), and preserve local customizations.
     - `resetup` — **Full Re-Setup**: Run the complete interactive setup flow while preserving existing `knowledge/**` and active `specs/**`.
     - `exit` — **Exit**: Keep current setup unchanged.
2. **Brownfield Alignment & Legacy Layout Migration (`align`)**:
   - Inventory existing `.agents/` files in one read-only pass before proposing writes:
     - **Legacy Spec & Track Migration**: Detect legacy `.agents/specs/`, `.agents/tracks/`, `tracks.md`, `metadata.json` manifests, or older sibling PRD child specs (`parent_prd: <prd_id>`), and offer to migrate active specifications into `.agents/bundles/specs/<flow_id>/spec.md` (plus frontmatter-free `chapters/index.md` and nested `chapters/ch01-<slug>/..chNN-<slug>/` for multi-chapter initiatives) with normalized `OKF v0.2` frontmatter and structured `tasks/<id>-<slug>.md` blueprints.
     - **Legacy Trackers & Journals**: Detect obsolete `.beads/`, `.agents/beads.json`, `.agents/transactions/` journals, `.git/hooks/pre-commit` tracker hooks, or `.agents/skills/flow-memory-keeper/`. Present exact paths and obtain user confirmation before removing them.
     - **OKF v0.2 Hygiene & Knowledge Tree Preservation**: Strip YAML frontmatter from subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `research/index.md`, `specs/index.md`, `chapters/index.md`) and `log.md`, remove standalone `---` horizontal rules from bundle Markdown bodies, and convert any flat `knowledge/patterns.md` into topic-specific `knowledge/patterns/<topic>.md` chapters while preserving scope-derived nested directories (`architecture/`, `domains/`, `patterns/`, `testing/`, `gotchas/`, `decisions/`) and relative links.
     - **Research Reorganization**: Reconcile `.agents/bundles/research/` (which holds un-promoted research only) per [`research.md`](research.md):
       1. Promote research consumed by an existing flow into `.agents/bundles/specs/<flow_id>/research/` (`state: promoted`, `promoted_to: <flow_id>`).
       2. Adopt actionable orphaned research into a new `state: planned` spec bundle or keep genuinely open research normalized as `<slug>_<YYYYMMDD>.md` (`state: open`).
       3. Contract spent research from archived flows into the matching `knowledge/**` chapter and remove the spent file after user confirmation.
     - **Workflow & Truth Block Sync**: Synchronize `.agents/bundles/knowledge/workflow.md` with [`../../../templates/agent/workflow.md`](../../../templates/agent/workflow.md) while preserving local `<!-- truth: start -->` and `<!-- truth: end -->` blocks (`<= 40` lines).
     - **Spec-to-Codebase Verification**: For every `planned` or `active` spec under `specs/<flow_id>/`, verify `tasks/*.md` frontmatter (`state`, `commit`) against live Git history and reconcile `spec.md` checklists.

## Phase 1: Toolchain & Subsystem Discovery

1. **Probe Host Binaries & Repository Manifests**:
   - Inspect `pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Makefile`, `justfile`, and `.github/workflows/*.yml`.
   - Probe installed binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) so `knowledge/workflow.md` records only commands that execute cleanly on the current host.
2. **Parallel Subsystem Discovery**:
   - Map the repository's core domains, deep-module seams, public interfaces, data models, and canonical test files.
   - When the `run_workflow` tool is available in the active harness (Google Antigravity), invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [...]})` (`await parallel(...)` with `agent(..., schema=DIGEST_SCHEMA, type_name="self", model="flash")`, verifying `git status --porcelain` afterward) to audit each subsystem concurrently.

## Phase 2: Scaffold Core Context Chapters & OKF v0.2 Bundle (`.agents/bundles/`)

Create the hierarchical OKF v0.2 bundle layout (only root `index.md` carries `okf_version: "0.2"` YAML frontmatter; subdirectory `index.md` catalogs and `log.md` are frontmatter-free):

```text
.agents/bundles/
├── index.md                        # Root manifest (okf_version: "0.2")
├── log.md                          # Frontmatter-free append-only ISO-dated changelog
├── product/
│   ├── index.md                    # Frontmatter-free catalog
│   ├── product.md                  # Vision, users, and core capabilities (<= 40-line <!-- truth: start --> block)
│   ├── product-guidelines.md       # Engineering tenets, deep-module seams, present-tense prose & anti-bloat standards
│   └── tech-stack.md               # Verified languages, frameworks, runtimes, databases, test/lint toolchain
├── knowledge/
│   ├── index.md                    # Frontmatter-free catalog
│   ├── workflow.md                 # Verified setup, lint, typecheck, focused test, and full verification gates
│   ├── architecture/<area>.md      # Deep modules, public interfaces vs. hidden implementation, seams & adapters
│   ├── patterns/<topic>.md         # Idiomatic patterns anchored to path/to/file::Symbol + anti-patterns
│   ├── domains/<domain>.md         # Ubiquitous domain glossary, entity lifecycles, and invariants
│   ├── testing/<topic>.md          # Public-seam TDD rules, dependency categories, canonical test file map
│   ├── gotchas/<area>.md           # Non-obvious footguns and runtime traps
│   └── decisions/adr-NNN-<slug>.md # Architectural Decision Records (hard to reverse + surprising + real trade-off)
├── research/
│   └── index.md                    # Frontmatter-free catalog
└── specs/
    └── index.md                    # Frontmatter-free catalog (chapters nested under specs/<flow_id>/chapters/)
```

- Gather or confirm the core project context chapters one question at a time (`structured-choice-v1`):
  1. **Product Definition (`product/product.md`)**: Core problem, users, and capabilities.
  2. **Product & Engineering Guidelines (`product/product-guidelines.md`)**: Naming, deep-module seam rules, cold-reader comprehension standard, and anti-bloat prose discipline.
  3. **Tech Stack (`product/tech-stack.md`)**: Auto-detected stack confirmed with the user.
  4. **Workflow (`knowledge/workflow.md`)**: Verified setup, lint, typecheck, focused test, and aggregate check commands.
- Every concept document carries OKF v0.2 YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated: { by, at }`, `verified: [{ by, at, commit }]`, `sources: [{ id, resource, title }]`), a bounded `<= 40`-line `<!-- truth: start -->` block, and `[^id]` footnotes matching `sources[].id`.

## Phase 3: Seed Baseline Disciplines & Generate Stack-Specific `.agents/skills/` and `.agents/agents/`

Follow [`../../multi-harness-plugins/SKILL.md`](../../multi-harness-plugins/SKILL.md) and [`../../flow-docs/references/agent-context.md`](../../flow-docs/references/agent-context.md) so generated skills and subagents work natively across all six harnesses:

1. **Embed Foundational Engineering Disciplines Tailored to the Repository**:
   - **Deep Modules & Seam Discipline (`knowledge/architecture/` & domain skills)**: Document each subsystem's **Module**, **Interface**, **Implementation**, **Seam**, and **Adapter** boundaries, classifying dependencies into (1) *In-process*, (2) *Local-substitutable*, (3) *Remote-owned (Ports & Adapters)*, and (4) *External boundary (Mock)*.
   - **Active Domain Glossary & ADRs (`knowledge/domains/` & `knowledge/decisions/`)**: Define ubiquitous domain terms so tests, specs, and code share exact vocabulary, and apply the ADR filter (*hard to reverse + surprising without context + genuine trade-off*).
   - **Public-Seam Vertical-Slice TDD & Bug Diagnosis (`knowledge/testing/`)**: Map source modules to their canonical test files (`tests/<module>/test_<unit>.*`), enforce testing through public interfaces without mocking the System Under Test, reject tautological tests, and record the repository's tight red-capable bug reproduction command pattern.
   - **Cold-Reader Prose & Documentation Standard (`product/product-guidelines.md`)**: Enforce zero-context comprehension, manifest-driven `[k/N files documented]` coverage, conceptual (`4–6` node) diagrams in `docs/`, and clean `<type>(<scope>): <summary>` PR/commit conventions.
2. **Generate Stack-Specific Engineering Domain Skills (`.agents/skills/<domain>/`)**:
   - For each discovered technical domain (`1–6` cohesive domains matching the repository's real stack):
     - `SKILL.md` (`<= 200` lines, `< 24,000` bytes) with YAML frontmatter (`name`, `description` context pointer), a bounded `<= 40`-line `<!-- truth: start -->` block, and progressive-disclosure links to `references/*.md`.
     - `references/*.md` containing concrete `path/to/file::Symbol` patterns, seam boundaries, anti-patterns, and verification commands.
3. **Generate Domain Review Capability Skills (`.agents/skills/review-<domain>/`)**:
   - `SKILL.md` scoping the zero-context review lens to its domain paths and checklists.
   - `references/checklist.md` with domain review rules (`<PREFIX>-01..NN`).
   - `references/false-positive-suppressions.md` with intentional repository patterns (`FP-<PREFIX>-01..NN`) and explicit `"DO NOT FLAG"` rationale.
4. **Write Skill Routing Index (`.agents/skills/index.md`) & Paired Subagents (`.agents/agents/`)**:
   - `.agents/skills/index.md` mapping `Domain | Rule Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
   - `.agents/agents/<domain>-reviewer.md`: Read-only zero-context reviewer (`model: inherit`, `mainAgent: false`, `subagent: true`, `readonly: true`, `commandExecutionPolicy: sandbox`, YAML list `disallowedTools: [Write, Edit, MultiEdit, NotebookEdit, write_file, edit_file]`, H1 `# ` section headers).
   - `.agents/agents/<domain>-specialist.md`: Write-enabled domain specialist (`model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy: sandbox`, H1 `# ` section headers).
   - Never copy Flow's global plugin skills (`flow`, `flow-*`, `okf`, `debloat`, `multi-harness-plugins`) or legacy `flow-memory-keeper` into `.agents/skills/`.

## Phase 4: Git Tracking Policy, Worktrees, Subagent Permissions, `AGENTS.md`, & `setup-state.json`

1. **Git Tracking Policy & Linked Worktree Routing (`shared` vs. `local-only` Stealth Mode)**:
   - Ask once via `structured-choice-v1` ([`interaction.md`](interaction.md)) and persist `workflow_preferences.ignore_policy` in `.agents/setup-state.json`:
     - **`shared` (Recommended for teams)**: Track `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and `.agents/setup-state.json` in Git; exclude `.agents/scratch/` via `.git/info/exclude` (or `.gitignore`). Linked `git worktree` checkouts already contain tracked `.agents/` files and edit worktree Markdown directly.
     - **`local-only` (Stealth mode)**: Append `.agents/` to `.git/info/exclude`. Flow writes nothing in `.agents/` to Git; `knowledge/**` and `log.md` on disk are the durable record. When starting inside a linked `git worktree`, `hooks/session-start.{sh,ps1}` (or `tools/worktree_env.py --bootstrap`) symlinks `$WORKTREE/.agents -> $MAIN_WORKTREE/.agents` and routes all Flow Markdown edits to the primary checkout.
   - **Automatic Linked-Worktree Environment Symlinking**: Regardless of `ignore_policy`, linked `git worktree` checkouts automatically symlink missing `.venv`, `node_modules`, `uv.toml`, `.npmrc`, and `.python-version` from `$MAIN_WORKTREE` so agents run `uv run --no-sync` without needing `make install` or `uv sync`.
2. **Opt-In Cross-Harness Permissions & `Stop` Hook Bootstrap**:
   - Detect installed harnesses (`claude`, `opencode`, `codex`, `cursor`, `agy`/`antigravity`) and offer opt-in non-destructive policy merges (when Flow is installed as a plugin, `SessionStart` and `Stop` hooks run automatically from the plugin root):
     - **Claude Code**: Offer to merge `plansDirectory: ".agents/bundles/specs"` and subagent-friendly `permissions.allow` entries (`Bash(git status*)`, `Bash(git diff*)`, `Bash(git log*)`, `Bash(git rev-parse*)`, `Bash(git merge-base*)`, `Bash(uv run *)`, `Bash(make lint*)`, `Edit(/.agents/**)`, `Write(/.agents/**)`) into `.claude/settings.local.json` (always backing up to `.claude/settings.local.json.bak` first and never overwriting existing user permissions) so background `@researcher`, `@executor`, and reviewer subagents do not stall on read/test prompts.
     - **Codex CLI**: Confirm native discovery of root `AGENTS.md`, `.agents/skills/`, and `.codex/agents/*.toml`; when using `local-only` stealth mode across linked Git worktrees, note adding the primary checkout's `.agents` path to `sandbox_workspace_write.writable_roots` in `.codex/config.toml` so worktree agents can update shared specs directly.
     - **OpenCode**: Offer to merge Flow-recommended instructions into `opencode.json` if present.
     - **Google Antigravity / Cursor / VS Code**: Confirm native discovery of root `AGENTS.md`, `.agents/skills/`, `.agents/agents/`, and plugin `SessionStart` + `Stop` review/sync hooks (`.agents/hooks.json` or `.cursor/hooks.json` when using project-local hook configs; on Antigravity, keep Fast Chapter Gate commands offline-safe so `run_workflow` subagents execute without unsandboxed network prompts).
3. **Update Root `AGENTS.md` & Write `.agents/setup-state.json`**:
   - Ensure root `AGENTS.md` (`<= 100` lines) routes to `.agents/bundles/index.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md` while preserving `<!-- project-customization: start -->` blocks.
   - Write `.agents/setup-state.json`:

     ```json
     {
       "setup_status": "complete",
       "last_successful_step": "complete",
       "root_directory": ".agents",
       "bundle_root": ".agents/bundles",
       "okf_version": "0.2",
       "stop_gate": "enforce",
       "workflow_preferences": {
         "ignore_policy": "shared",
         "model_routing": "auto",
         "sha_tracking": "strict"
       }
     }
     ```

   - Preserve any existing optional `knowledge_catalog` block (`enabled`, `project_id`, `location`, `entry_group`, `entry_groups`, `content_layout`, `last_synced_sha256`) when reading or updating `.agents/setup-state.json`.

4. Verify all relative links in `.agents/bundles/index.md`, `knowledge/index.md`, and `.agents/skills/index.md` resolve on disk, and ask whether the user wants to start their first flow (`/flow:spec` or `/flow:prd`).
