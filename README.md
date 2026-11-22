<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-inline-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-inline-light.svg">
    <img alt="Flow" src="assets/banner-inline-light.svg" width="520">
  </picture>

  <p><strong>Spec-First Engineering &amp; Directed Agent Workflows — Measure twice, code once.</strong></p>

  <p>
    <a href="https://github.com/litestar-org"><img alt="Litestar Ecosystem" src="https://img.shields.io/badge/Litestar%20Org-Flow-202235?labelColor=202235&color=edb641"></a>
    <a href="skills/okf/SKILL.md"><img alt="OKF v0.2" src="https://img.shields.io/badge/OKF-v0.2-202235?labelColor=202235&color=edb641"></a>
    <a href="skills/multi-harness-plugins/SKILL.md"><img alt="Harnesses" src="https://img.shields.io/badge/harnesses-6-202235?labelColor=202235&color=edb641"></a>
    <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-202235?labelColor=202235&color=edb641"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&labelColor=202235"></a>
  </p>

  <p>
    <a href="#architecture--lifecycle">Architecture &amp; Lifecycle</a>
    &middot;
    <a href="#flow-studio--local-knowledge-catalog">Flow Studio</a>
    &middot;
    <a href="#install">Install</a>
    &middot;
    <a href="#commands--lifecycle-skills">Commands</a>
    &middot;
    <a href="#consumer-repository-agents-layout">Bundle Layout</a>
  </p>
</div>

Flow is a unified toolkit for **Spec-Driven Development** backed by **Open Knowledge Format (`OKF v0.2`)** bundles. It works natively from a single repository root across **Google Antigravity** (IDE & CLI), **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / Copilot**.

## Architecture & Lifecycle

Flow separates planning and review from isolated task execution:

1. **Setup (`/flow:setup`)**:
   - Runs **Brownfield Alignment & Legacy Migration** (`align` mode) to upgrade existing `.agents/` layouts without data loss, or initializes a new repository from scratch.
   - Probes host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) and scaffolds core context chapters (`product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, `knowledge/workflow.md`). Adds `<= 40`-line `<!-- truth: start -->` blocks and nested `knowledge/**` chapters anchored to `path/to/file::Symbol`.
   - Seeds engineering disciplines (deep-module design, domain modeling, public-interface TDD, bug diagnosis, and first-time reader docs) alongside stack-specific `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/`, and `.agents/agents/<domain>-{reviewer,specialist}.md` subagents.
   - Configures Git tracking (`shared` team mode vs. `local-only` stealth mode via `.git/info/exclude`) and opt-in cross-harness settings.
2. **Spec (`/flow:prd`, `/flow:spec`, `/flow:revise`, `/flow:research`) — Upfront Chapter Plans**:
   - **Parallel Research & Questioning**: Fans out read-only `@researcher` subagents returning subsystem summaries, then resolves open decisions (`1` question for dependent forks; `2–3` batched independent questions with `<Label> (Recommended)` first).
   - **Feature-Sized Specifications (`/flow:prd` & `/flow:spec`)**: Defaults cohesive features to a single-chapter `spec.md` (`has_chapters: false`) and splits into `chapters/ch01..chNN/` only at real checkpoints or independent subsystems. Allows `compact` worksheets for any size, runs parallel per-chapter planners for `>= 2` chapters, validates `OKF v0.2` right after writing, and warns on `planning_quality: degraded`.
   - **Independent Spec Review & Revision (`/flow:revise`)**: Runs independent reviewers (`1` combined reviewer up to `4` chapters) using only disk paths and decides on each finding (`ADOPT`, `CONTEST`, `ESCALATE`). Keeps root `spec.md`, `chapters/index.md`, and chapter worksheets synced in present tense.
   - **Research & Prototyping (`/flow:research`, alias `/flow:task`)**: Runs primary-source `@researcher` audits promoted into `research/*.md` with `sources:` + `[^id]:` footnotes, or time-boxed prototypes in untracked `.agents/scratch/<slug>/`.
3. **Implement (`/flow:implement`, `/flow:status`) — Parallel Steps & Fast Chapter Check**:
   - Resolves linked `git worktree` checkouts (symlinking `.venv`/`node_modules` and routing `shared` vs. `local-only` `.agents/`), runs preflight, and executes the active chapter (`1..N` tasks; or ready chapters with `--all`). Runs parallel workers on separate files (`small_swarm` on Antigravity; `parallel_tasks` on Claude Code, Codex CLI, Cursor, and OpenCode) or sequential `chapter_batch` passes.
   - Runs the `< 60s` chapter check once per chapter (reserving `> 60s` full suites for `/flow:finish`), records commit SHAs before syncing `.agents/bundles/knowledge/**`, `docs/**`, `chapters/index.md`, and root `spec.md` in present tense. Passes independent review (`@code-reviewer` + `@quality-reviewer`), stamps `last_reviewed_commit`, and enforces completion checks in cross-harness `Stop` hooks (`hooks/stop-check.{sh,ps1}`).
4. **Learn & Document (`/flow:learn`, `/flow:docs`)**:
   - **`/flow:learn` (aliases `refresh`, `sync`)**: Runs anytime—across machines, mid-flow, or post-flow—to sync Git history with task worksheets and intersect `git diff` against `sources[].resource`. Sharpens domain glossaries and ADRs (`knowledge/decisions/adr-NNN-<slug>.md`), updates `knowledge/**` in present tense, and syncs `.agents/skills/` and `.agents/agents/`.
   - **`/flow:docs` (`write`, `validate`, `capture`, `sync`, `pr`)**: Tool-agnostic documentation and agent-context discipline grounded in first-time reader clarity, file-checklist `[k/N files documented]` coverage, progressive disclosure ([`agent-context.md`](skills/flow-docs/references/agent-context.md)), and clean PR/commit/changelog hygiene ([`prs-commits-and-changelogs.md`](skills/flow-docs/references/prs-commits-and-changelogs.md)).
5. **Complete (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Runs independent code review covering spec conformance, repository standards, deep-module design, and debloat. Verifies release checks on the current branch, captures durable learnings into `.agents/bundles/knowledge/**` + `.agents/bundles/log.md`, and removes completed spec directories.

## Flow Studio & Local Knowledge Catalog

Flow includes **Flow Studio** ([`studio.md`](skills/flow/references/studio.md)) and cross-harness orchestration ([`orchestration.md`](skills/flow/references/orchestration.md)). It runs across **Google Antigravity** (`sidecars/studio/` + `sidecars/studio/mcp-server.mjs`), **Claude Code** (`mods/claude-flow/`), **Codex CLI** (`CodexAppServerBridge`), **VS Code & Cursor** (`vscode-extension/`), and **OpenCode V2** (`.opencode/plugins/flow.js`):

- **Studio Home, Multi-Branch Specs, & Review**: Switch pinned or remote repositories from Studio Home and browse specs across branches. Record out-of-tree feedback under `<git-common-dir>/spec-feedback/<flow_id>/<author_slug>.json`, publish spec PRs (`flow spec pr`), and send notes straight to `/flow:revise`.
- **Dynamic Model Routing & `flow` CLI**: Evaluate live model inventories across all six harnesses (`flow models`) while keeping planning and verification on `strong` models. Install the unified CLI with `flow install-cli` for sync, branch specs, bundle linting, and agent helpers.
- **Federated Knowledge Catalog & Python Runner Auto-Detection**: Searches local and sibling workspaces (`sidecars/studio/knowledge/catalog.mjs` BM25 + graph links alongside `flow-catalog` DuckDB RRF) and manages workspace permission allowlists. Dispatches tasks in `direct-workspace`, `worktree-isolated`, or `read-only` mode (including loopback A2A `/.well-known/agent-card.json` + `POST /a2a`).

## Install

### Google Antigravity

```bash
agy plugin install https://github.com/cofin/flow
```

When running in Google Antigravity, Flow uses the `run_workflow` Python API (`phase()`, `parallel()`, `pipeline()`, `agent(..., type_name="self", schema=..., model="inherit")`) for parallel research, chapter spec authoring, independent reviews, and isolated single-chapter task runs.

### Claude Code

```bash
claude plugin marketplace add cofin/flow
claude plugin install flow@flow-marketplace
```

Update commands:

```bash
claude plugin marketplace update flow-marketplace
claude plugin update flow@flow-marketplace
```

### Codex CLI

```bash
codex plugin marketplace add cofin/flow
```

Then run `/plugins` inside a Codex session to enable `flow`, or update with `codex plugin marketplace upgrade flow-marketplace`. Invoke Flow through natural-language skill requests such as `Use Flow to set up this project` or `Use Flow to plan user authentication`.

### Cursor

1. **Agent Plugin (`.cursor-plugin/plugin.json`)**: Install Flow as a Cursor plugin (`https://github.com/cofin/flow`) so skills, subagents, and lifecycle hooks (`hooks/hooks-cursor.json`) load automatically.
2. **Flow Studio Extension (`vscode-extension/`)**: Installed automatically into `~/.cursor/extensions` on your first session (`hooks/session-start.{sh,ps1}`), or run directly from GitHub without cloning the repository:

```bash
npx --yes --package github:cofin/flow flow-studio-vscode --target cursor
```

### OpenCode V2

Install the packaged plugin. It registers Flow's skills and subagents and adds the live bundle summary to every model request:

```bash
opencode plugin add github:cofin/flow
```

For local development, add the checkout directory to the OpenCode `plugins` configuration instead.

If OpenCode reports `Plugin must export a default definition with an id and an effect or setup function` for `~/.config/opencode/plugins/flow.js`, that file is a standalone copy from before Flow 0.26 that OpenCode V2 rejects. Delete it and install the package with the command above.

### VS Code / Copilot ( plus Windsurf & Positron )

1. **Chat / Agent Plugin**: Install Flow through **Chat: Install Plugin From Source** (or from a local checkout, where `make install-vscode` / `node ./vscode-extension/install.mjs --link` can also be used for local development).
2. **Flow Studio Extension (`vscode-extension/`)**: Run the one-line installer from GitHub (no Git clone needed) to bundle `vscode-extension/` + `sidecars/studio/` and register `cofin.flow-studio` into your editor's `extensions.json`. Then reload the window (`Developer: Reload Window`):

```bash
# Auto-detect installed VS Code-compatible editors and install cofin.flow-studio
npx --yes --package github:cofin/flow flow-studio-vscode

# Or target a specific editor (vscode | vscode-insiders | cursor | windsurf | positron | all)
npx --yes --package github:cofin/flow flow-studio-vscode --target vscode
```

## Commands & Lifecycle Skills

| Command | Lifecycle Skill | Reference Procedure | Description |
| --- | --- | --- | --- |
| `/flow:setup` | [`flow-setup`](skills/flow-setup/SKILL.md) | [`setup.md`](skills/flow/references/setup.md) | Align brownfield repos or bootstrap `.agents/bundles/`, `.agents/skills/`, and `.agents/agents/` |
| `/flow:prd <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`prd.md`](skills/flow/references/prd.md) | Author multi-chapter roadmap (`spec.md` + `chapters/ch01..chNN/`) and upfront worksheets |
| `/flow:spec <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`spec.md`](skills/flow/references/spec.md) | Author high-detail specification (`spec.md`), `chapters/`, and `tasks/*.md` worksheets (alias: `plan`) |
| `/flow:revise <flow_id>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`revise.md`](skills/flow/references/revise.md) | Rewrite root `spec.md`, `chapters/`, and `tasks/*.md` in place in present tense (alias: `refine`) |
| `/flow:research <topic>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`research.md`](skills/flow/references/research.md) | Primary-source research & time-boxed `.agents/scratch/` spikes (alias: `task`) |
| `/flow:implement [flow_id]` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`implement.md`](skills/flow/references/implement.md) | Execute active chapter (`1..N` tasks, or `--all` chapters) with public-interface TDD, doc/OKF sync, and review |
| `/flow:status` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`status.md`](skills/flow/references/status.md) | Inspect active flows, chapter progress, remaining plan, and ready tasks |
| `/flow:dispatch` | [`flow-dispatch`](skills/flow-dispatch/SKILL.md) | [`orchestration.md`](skills/flow/references/orchestration.md) | Route models and worker briefs, dispatch cross-harness runs, and coordinate peer conversations |
| `/flow:learn [scope]` | [`flow-learn`](skills/flow-learn/SKILL.md) | [`learn.md`](skills/flow/references/learn.md) | Anytime catch-up (`refresh`), sync, `OKF v0.2` knowledge update, and skill sync |
| `/flow:docs [mode]` | [`flow-docs`](skills/flow-docs/SKILL.md) | [`prose-and-documentation.md`](skills/flow-docs/references/prose-and-documentation.md) | Tool-agnostic user/developer docs, [`agent-context.md`](skills/flow-docs/references/agent-context.md), changelogs, and clean PRs |
| `/flow:review [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`review.md`](skills/flow/references/review.md) | Independent spec, Markdown-sync, standards, debloat, and subtraction-only `simplify` review |
| `/flow:finish [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`finish.md`](skills/flow/references/finish.md) | Verify release checks, chapter review stamps, ADR filter, and mark flow `completed` |
| `/flow:archive [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`archive.md`](skills/flow/references/archive.md) | Capture completed flow into `.agents/bundles/knowledge/**` and remove spec dir |
| `/flow:cleanup` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`cleanup.md`](skills/flow/references/cleanup.md) | Groundskeeping: sync specs, archive completed flows, and debloat touched files |
| `/flow:revert <scope>` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`revert.md`](skills/flow/references/revert.md) | Git-aware revert of a task, chapter, phase, or flow |
| `/flow:validate` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`validate.md`](skills/flow/references/validate.md) | Validate `.agents/bundles/`, `.agents/skills/`, `.agents/agents/`, and active specs |

## Consumer Repository `.agents/` Layout

```text
.agents/
├── setup-state.json                              # Active bundle root, setup state & ignore_policy (shared | local-only)
├── scratch/                                      # Untracked throwaway prototypes & spikes
├── skills/                                       # Project-local domain & review skills (generated by /flow:setup & /flow:learn)
│   ├── index.md
│   ├── <domain>/{SKILL.md,references/*.md}
│   └── review-<domain>/{SKILL.md,references/{checklist,false-positive-suppressions}.md}
├── agents/                                       # Paired project-local subagents
│   ├── <domain>-reviewer.md
│   └── <domain>-specialist.md
└── bundles/
    ├── index.md                                  # Root OKF v0.2 manifest
    ├── log.md                                    # ISO-dated lifecycle log (prepend new entries)
    ├── product/{index,product,product-guidelines,tech-stack}.md
    ├── knowledge/
    │   ├── index.md
    │   ├── workflow.md
    │   ├── architecture/<area>.md
    │   ├── patterns/<topic>.md
    │   ├── domains/<domain>.md
    │   ├── testing/<topic>.md
    │   ├── gotchas/<area>.md
    │   └── decisions/adr-NNN-<slug>.md
    ├── research/<topic>_<YYYYMMDD>.md
    └── specs/
        ├── index.md                              # Frontmatter-free spec catalog
        └── <flow_id>/
            ├── spec.md                           # Full-plan roadmap & present-tense state snapshot
            ├── learnings.md
            ├── research/<topic>_<YYYYMMDD>.md
            ├── tasks/<id>-<slug>.md              # Single-chapter flows (1..N tasks)
            └── chapters/                         # Multi-chapter flows (ch01..chNN, zero upper cap)
                ├── index.md
                └── ch01-<slug>/
                    ├── spec.md
                    └── tasks/<id>-<slug>.md      # Deliverable chapter task worksheets (1..N tasks)
```

## License

[Apache License 2.0](LICENSE)
