# Flow Setup (`/flow:setup`)

Initialize or align a repository for Spec-Driven Development with Flow's core context chapters, an OKF v0.2 knowledge bundle (`.agents/bundles/`), project-local skills (`.agents/skills/`), and paired subagents (`.agents/agents/`).

## Phase 0: Environment Detection & Brownfield Mode

1. **Check Existing State**:
   - Inspect `<hook_context>`, `.agents/setup-state.json`, and `.agents/bundles/index.md`.
   - Treat `setup_status: "complete"` as a claim to verify against current files, not blind proof.
   - If `.agents/` already exists, ask via [`interaction.md`](interaction.md):
     - `align` — **Align & Sync (Recommended)**: Validate and migrate existing `.agents/` files, refresh drifted knowledge and skills via [`learn.md`](learn.md), and keep local customizations.
     - `resetup` — **Full Re-Setup**: Run the full interactive setup while keeping existing `knowledge/**` and active `specs/**`.
     - `exit` — **Exit**: Keep current setup unchanged.
2. **Brownfield Alignment & Legacy Migration (`align`)**:
   - Inventory existing `.agents/` files in one read-only pass before proposing writes:
     - **Legacy Spec Migration**: Detect legacy `.agents/specs/`, `.agents/tracks/`, `tracks.md`, `metadata.json`, or older sibling PRD child specs (`parent_prd: <prd_id>`). Migrate active specs into `.agents/bundles/specs/<flow_id>/spec.md`, inspect steps via `node <plugin_root>/sidecars/studio/flow-cli.mjs tasks plan --briefs`, and sync task states, `depends_on` edges, user deferrals, and commit SHAs.
     - **Legacy Trackers & Journals**: Detect obsolete `.beads/`, `.agents/beads.json`, `.agents/transactions/`, or `.git/hooks/pre-commit` tracker hooks. Present exact paths and confirm before removing them.
     - **OKF v0.2 Hygiene & Knowledge Tree**: Strip YAML frontmatter from subdirectory `index.md` files (`product/index.md`, `knowledge/index.md`, `knowledge/<ns>/index.md`, `research/index.md`, `specs/index.md`, `chapters/index.md`) and `log.md`. Remove standalone `---` body rules and split flat `knowledge/patterns.md` into `knowledge/patterns/<topic>.md` while keeping nested directories and relative links.
     - **Research Reorganization**: Sync `.agents/bundles/research/` (un-promoted research only) per [`research.md`](research.md):
       1. Promote research used by an existing flow into `.agents/bundles/specs/<flow_id>/research/` (`state: promoted`, `promoted_to: <flow_id>`).
       2. Adopt actionable orphaned research into a `state: planned` spec, or keep open research as `<slug>_<YYYYMMDD>.md` (`state: open`).
       3. Fold spent research from archived flows into the matching `knowledge/**` chapter and remove the spent file after user confirmation.
     - **Workflow & Truth Block Sync**: Sync `.agents/bundles/knowledge/workflow.md` with [`../../../templates/agent/workflow.md`](../../../templates/agent/workflow.md) while keeping local `<= 40`-line `<!-- truth: start -->` truth blocks.
     - **Spec-to-Codebase Verification**: For every `planned` or `active` spec under `specs/<flow_id>/`, verify `tasks/*.md` frontmatter (`state`, `commit`) against live Git history and sync `spec.md` checklists.

## Phase 1: Toolchain & Subsystem Discovery

1. **Probe Host Binaries & Repository Manifests**:
   - Inspect `pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Makefile`, `justfile`, and `.github/workflows/*.yml`.
   - Probe installed binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) so `knowledge/workflow.md` records only working commands.
2. **Parallel Subsystem Discovery**:
   - Map the repository's core domains, deep module interfaces, data models, and canonical test files.
   - When `run_workflow` is available (Google Antigravity), call `run_workflow(ScriptPath="<plugin_root>/workflows/flow-scout/workflow.py", Args={"subsystems": [...]})` (`await parallel(...)` with `agent(..., schema=DIGEST_SCHEMA, type_name="self", model="flash")`) and check `git status --porcelain` afterward.

## Phase 2: Scaffold Core Context & OKF Bundle

Create the OKF v0.2 bundle layout (only root `index.md` carries `okf_version: "0.2"` YAML frontmatter; subdirectory `index.md` files and `log.md` are frontmatter-free):

```text
.agents/bundles/
├── index.md                        # Root manifest (okf_version: "0.2")
├── log.md                          # Frontmatter-free append-only ISO-dated changelog
├── product/
│   ├── index.md                    # Frontmatter-free catalog
│   ├── product.md                  # Vision, users, and core capabilities (<= 40-line <!-- truth: start --> block)
│   ├── product-guidelines.md       # Engineering tenets, deep module interfaces, present-tense prose & debloat standards
│   └── tech-stack.md               # Verified languages, frameworks, runtimes, databases, test/lint toolchain
├── knowledge/
│   ├── index.md                    # Frontmatter-free catalog
│   ├── workflow.md                 # Verified setup, lint, typecheck, focused test, and full verification checks
│   ├── architecture/<area>.md      # Deep modules, public interfaces vs. hidden implementation, adapters
│   ├── patterns/<topic>.md         # Idiomatic patterns anchored to path/to/file::Symbol + anti-patterns
│   ├── domains/<domain>.md         # Domain glossary, entity lifecycles, and invariants
│   ├── testing/<topic>.md          # Public interface TDD rules, dependency categories, canonical test file map
│   ├── gotchas/<area>.md           # Non-obvious footguns and runtime traps
│   └── decisions/adr-NNN-<slug>.md # Architectural Decision Records (hard to reverse + surprising + real trade-off)
├── research/
│   └── index.md                    # Frontmatter-free catalog
└── specs/
    └── index.md                    # Frontmatter-free catalog (chapters nested under specs/<flow_id>/chapters/)
```

- Gather or confirm the core context chapters one question at a time via [`interaction.md`](interaction.md):
  1. **Product Definition (`product/product.md`)**: Core problem, users, and capabilities.
  2. **Product & Engineering Guidelines (`product/product-guidelines.md`)**: Naming, deep module interface rules, first-time reader clarity, and debloat prose rules.
  3. **Tech Stack (`product/tech-stack.md`)**: Auto-detected stack confirmed with the user.
  4. **Workflow (`knowledge/workflow.md`)**: Verified setup, lint, typecheck, focused test, and full check commands.
- Every concept document carries OKF v0.2 YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated`, `verified`, `sources`), a `<= 40`-line `<!-- truth: start -->` truth block, and `[^id]` footnotes.

## Phase 3: Seed Disciplines, Skills & Subagents

Follow [`../../multi-harness-plugins/SKILL.md`](../../multi-harness-plugins/SKILL.md) and [`../../flow-docs/references/agent-context.md`](../../flow-docs/references/agent-context.md) so generated skills and subagents work across all six harnesses:

1. **Embed Foundational Engineering Disciplines**:
   - **Deep Modules & Interfaces (`knowledge/architecture/` & domain skills)**: Document each subsystem's **Module**, **Interface**, **Implementation**, and **Adapter** boundaries, classifying dependencies into (1) *In-process*, (2) local test double, (3) *Remote-owned (Ports & Adapters)*, and (4) *External boundary (Mock)*.
   - **Domain Glossary & ADRs (`knowledge/domains/` & `knowledge/decisions/`)**: Define shared domain terms across tests, specs, and code, and apply the ADR filter (*hard to reverse + surprising without context + genuine trade-off*).
   - **Public Interface TDD & Bug Diagnosis (`knowledge/testing/`)**: Map source modules to canonical test files (`tests/<module>/test_<unit>.*`), test through public interfaces without mocking real code, reject mock-only tests, and record the fast failing test command.
   - **First-Time Reader Prose & Docs (`product/product-guidelines.md`)**: Require standalone clarity, file checklist `[k/N files documented]` coverage, conceptual (`4–6` node) diagrams in `docs/`, and `<type>(<scope>): <summary>` PR/commit conventions.
2. **Generate Stack-Specific Domain Skills (`.agents/skills/<domain>/`)**:
   - For each discovered technical domain (`1–6` domains matching the repo's real stack):
     - `SKILL.md` (`<= 200` lines, `< 24,000` bytes) with YAML frontmatter (`name`, `description`), a `<= 40`-line `<!-- truth: start -->` truth block, and links to `references/*.md`.
     - `references/*.md` with concrete `path/to/file::Symbol` patterns, module interfaces, anti-patterns, and verification commands.
3. **Generate Domain Review Skills (`.agents/skills/review-<domain>/`)**:
   - `SKILL.md` scoping the independent review lens to its domain paths and checklists.
   - `references/checklist.md` with domain review rules (`<PREFIX>-01..NN`).
   - `references/false-positive-suppressions.md` with intentional patterns (`FP-<PREFIX>-01..NN`) and explicit `"DO NOT FLAG"` rationale.
4. **Write Skill Index (`.agents/skills/index.md`) & Paired Subagents (`.agents/agents/`)**:
   - `.agents/skills/index.md` mapping `Domain | Rule Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
   - `.agents/agents/<domain>-reviewer.md`: Read-only independent reviewer (`model: inherit`, `mainAgent: false`, `subagent: true`, `readonly: true`, `commandExecutionPolicy: sandbox`, YAML list `disallowedTools: [Write, Edit, MultiEdit, NotebookEdit, write_file, edit_file]`, H1 `# ` headers).
   - `.agents/agents/<domain>-specialist.md`: Write-enabled domain specialist (`model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy: sandbox`, H1 `# ` headers).
   - Never copy Flow's global plugin skills (`flow`, `flow-*`, `okf`, `debloat`, `multi-harness-plugins`) into `.agents/skills/`.

## Phase 4: Tracking Policy, Hooks & `setup-state.json`

1. **Git Tracking Policy & Worktrees (`shared` vs. `local-only` Stealth Mode)**:
   - Ask once via [`interaction.md`](interaction.md) and save `workflow_preferences.ignore_policy` in `.agents/setup-state.json`:
     - **`shared` (Recommended for teams)**: Track `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and `.agents/setup-state.json` in Git; exclude `.agents/scratch/` via `.git/info/exclude` or `.gitignore`. Linked `git worktree` checkouts edit worktree Markdown directly.
     - **`local-only` (Stealth mode)**: Append `.agents/` to `.git/info/exclude`. Flow writes nothing in `.agents/` to Git; `knowledge/**` and `log.md` on disk are the record. In a linked `git worktree`, `hooks/session-start.{sh,ps1}` (or `node <plugin_root>/sidecars/studio/flow-cli.mjs worktree bootstrap`) symlinks `$WORKTREE/.agents -> $MAIN_WORKTREE/.agents`.
   - **Automatic Linked-Worktree Symlinking**: Regardless of `ignore_policy`, linked `git worktree` checkouts symlink missing `.venv`, `node_modules`, `uv.toml`, `.npmrc`, and `.python-version` from `$MAIN_WORKTREE` so agents run `uv run --no-sync`.
2. **Opt-In Cross-Harness Permissions & `Stop` Hook Bootstrap**:
   - Detect installed harnesses (`claude`, `opencode`, `codex`, `cursor`, `agy`/`antigravity`) and offer non-destructive policy merges (when Flow is installed as a plugin, `SessionStart` and `Stop` hooks run from the plugin root):
     - **Claude Code**: Offer to merge `plansDirectory: ".agents/bundles/specs"` and read/test `permissions.allow` entries into `.claude/settings.local.json` (backing up to `.claude/settings.local.json.bak` first, never overwriting user permissions) so background subagents do not stall.
     - **Codex CLI**: Confirm native discovery of `AGENTS.md`, `.agents/skills/`, and `.codex/agents/*.toml`. Under `local-only` stealth mode in worktrees, note adding the primary checkout's `.agents` path to `sandbox_workspace_write.writable_roots` in `.codex/config.toml`.
     - **OpenCode**: Offer to merge Flow-recommended instructions into `opencode.json` if present.
     - **Google Antigravity / Cursor / VS Code**: Confirm native discovery of `AGENTS.md`, `.agents/skills/`, `.agents/agents/`, and `SessionStart` + `Stop` hooks. Keep fast chapter check commands offline-safe on Antigravity.
3. **Update Root `AGENTS.md` & Write `.agents/setup-state.json`**:
   - Ensure root `AGENTS.md` (`<= 100` lines) links to `.agents/bundles/index.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md` while keeping `<!-- project-customization: start -->` blocks.
   - Write `.agents/setup-state.json`:

     ```json
     {
       "setup_status": "complete",
       "last_successful_step": "complete",
       "root_directory": ".agents",
       "bundle_root": ".agents/bundles",
       "okf_version": "0.2",
       "stop_check": "enforce",
       "workflow_preferences": {
         "ignore_policy": "shared",
         "model_routing": "auto",
         "sha_tracking": "strict"
       }
     }
     ```

   - Keep any existing optional `knowledge_catalog` block (`enabled`, `project_id`, `location`, `entry_group`, `entry_groups`, `content_layout`, `last_synced_sha256`) when updating `.agents/setup-state.json`.
4. Verify all relative links in `.agents/bundles/index.md`, `knowledge/index.md`, and `.agents/skills/index.md` resolve on disk, and ask whether to start the first flow (`/flow:spec` or `/flow:prd`).
