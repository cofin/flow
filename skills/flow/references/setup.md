# Flow Setup (`/flow:setup`)

Initialize or align a repository for Spec-Driven Development with a rich OKF v0.2 knowledge bundle (`.agents/bundles/`), dynamically generated project-local domain and review skills (`.agents/skills/`), and paired project-local subagents (`.agents/agents/`).

## Phase 1: Toolchain & Repository Discovery

1. **Check Existing State**:
   - Inspect `.agents/setup-state.json` and `.agents/bundles/index.md` if present.
   - If `.agents/bundles/` already exists, offer **Align & True-Up (Recommended)** (which runs the brownfield migration and [`learn.md`](learn.md) resynthesis pass) or **Full Re-Setup**.
2. **Probe Host Binaries & Repository Manifests**:
   - Inspect repository manifests (`pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Makefile`, `justfile`, `.github/workflows/*.yml`).
   - Probe installed binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`) so `.agents/bundles/knowledge/workflow.md` records only commands that work on the host.
3. **Parallel Subsystem Discovery**:
   - Identify the repository's core domains, architecture seams, data models, and test harnesses.
   - When the `run_workflow` tool is available in the active harness (Google Antigravity), fan out `parallel(subsystems, inspect_subsystem)` using `agent(type_name="researcher", schema=SUBSYSTEM_SCHEMA, model="inherit")` to audit each subsystem concurrently.

## Phase 2: Scaffold & Populate Rich OKF v0.2 Bundle (`.agents/bundles/`)

Create the hierarchical OKF v0.2 bundle layout:

```text
.agents/bundles/
├── index.md                        # Root manifest (okf_version: "0.2")
├── log.md                          # Append-only ISO-dated changelog
├── product/
│   ├── index.md
│   ├── product.md                  # Vision, users, and core capabilities (with <= 40-line <!-- truth: start --> block)
│   ├── product-guidelines.md       # Engineering tenets, naming, API/UX standards
│   └── tech-stack.md               # Languages, frameworks, runtimes, databases, test/lint toolchain
├── knowledge/
│   ├── index.md
│   ├── workflow.md                 # Verified setup, lint, typecheck, test, and release gates
│   ├── architecture/<area>.md      # Subsystem boundaries, dataflow, concurrency, IPC/RPC contracts
│   ├── patterns/<topic>.md         # Idiomatic patterns anchored to path/to/file::Symbol
│   ├── domains/<domain>.md         # Domain vocabulary, invariants, and business rules
│   ├── testing/<topic>.md          # Test matrix, fixture patterns, SUT integrity rules
│   ├── gotchas/<area>.md           # Non-obvious footguns and runtime traps
│   └── decisions/adr-NNN-<slug>.md # Architectural Decision Records (when explicit decisions exist)
├── research/
│   └── index.md
└── specs/
    └── index.md
```

- Every concept document carries OKF v0.2 YAML frontmatter (`type`, `title`, `description`, `status: stable`, `tags`, `generated: { by, at }`, `verified: [{ by, at, commit }]`, `sources: [{ id, resource, title }]`), a bounded `<= 40`-line `<!-- truth: start -->` block, and `[^id]` footnotes matching `sources[].id`.
- If legacy `.agents/` files or uncontracted completed specs exist, migrate durable knowledge into `knowledge/**`, remove obsolete `.agents/transactions/` directories, and contract completed specs into `knowledge/**` + `log.md`.

## Phase 3: Dynamically Generate Project-Local Skills (`.agents/skills/`) & Paired Subagents (`.agents/agents/`)

For each discovered technical domain (`1–6` cohesive domains matching the repository's real stack):

1. **Engineering Domain Skill (`.agents/skills/<domain>/`)**:
   - `SKILL.md` (`<= 200` lines, `< 24,000` bytes) with YAML frontmatter (`name`, `description`), a bounded `<= 40`-line `<!-- truth: start -->` block, and progressive-disclosure links to `references/*.md`.
   - `references/*.md` containing concrete `path/to/file::Symbol` patterns, anti-patterns, and verification commands.
2. **Domain Review Capability Skill (`.agents/skills/review-<domain>/`)**:
   - `SKILL.md` scoping the review lens to its domain paths and checklists.
   - `references/checklist.md` with domain review rules (`<PREFIX>-01..NN`).
   - `references/false-positive-suppressions.md` with intentional repository patterns (`FP-<PREFIX>-01..NN`) and explicit `"DO NOT FLAG"` rationale.
3. **Skill Index (`.agents/skills/index.md`)**:
   - Matrix mapping `Domain | Rule Prefix | Engineering Skill | Review Skill | Reviewer Subagent | Specialist Subagent | Knowledge Chapters`.
4. **Paired Project-Local Subagents (`.agents/agents/`)**:
   - `.agents/agents/<domain>-reviewer.md`: Read-only reviewer (`model: inherit`, `mainAgent: false`, `subagent: true`, `readonly: true`, `commandExecutionPolicy: off`, YAML list `disallowedTools: [Write, Edit, NotebookEdit, write_file, edit_file]`, H1 `# ` section headers) preloaded with `.agents/skills/<domain>` and `.agents/skills/review-<domain>`.
   - `.agents/agents/<domain>-specialist.md`: Write-enabled domain specialist (`model: inherit`, `mainAgent: false`, `subagent: true`, `commandExecutionPolicy: sandbox`, H1 `# ` section headers) preloaded with `.agents/skills/<domain>` and `.agents/skills/review-<domain>`.

Never copy Flow's global skills (`flow`, `flow-*`, `okf`, `debloat`) or legacy `flow-memory-keeper` into `.agents/skills/`.

## Phase 4: Workspace `AGENTS.md`, Git Tracking Policy & `.agents/setup-state.json`

1. Ask once via `structured-choice-v1` ([`interaction.md`](interaction.md)) whether `.agents/` should be **`shared`** (tracked in Git, Recommended) or **`local-only`** (ignored in `.gitignore`).
2. Update root `AGENTS.md` to reference `.agents/bundles/index.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md` while preserving any `<!-- project-customization: start -->` blocks.
3. Write `.agents/setup-state.json`:

   ```json
   {
     "setup_status": "complete",
     "root_directory": ".agents",
     "bundle_root": ".agents/bundles",
     "okf_version": "0.2",
     "workflow_preferences": {
       "ignore_policy": "shared"
     }
   }
   ```

4. Verify all relative links in `.agents/bundles/index.md`, `knowledge/index.md`, and `.agents/skills/index.md` resolve on disk, and present the setup summary with the next command (`/flow:plan` or `/flow:prd`).
