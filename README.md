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

Flow separates **Stateful Planning & Adjudication** from **Zero-Context Verification** and **Isolated Vertical-Slice Task Execution**:

1. **Setup (`/flow:setup`)**:
   - Runs **Brownfield Alignment & Legacy Migration** (`align` mode) to upgrade existing `.agents/` layouts without data loss, or initializes a new repository from scratch.
   - Probes installed host binaries (`uv`, `python3`, `cargo`, `go`, `bun`, `pnpm`, `npm`, `make`, `just`, `pwsh`, `powershell`) and scaffolds Flow's core context chapters (`product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, and `knowledge/workflow.md`) with bounded `<= 40`-line `<!-- truth: start -->` blocks and nested `knowledge/{architecture,patterns,domains,testing,gotchas,decisions}/` chapters anchored to `path/to/file::Symbol`.
   - Seeds baseline engineering disciplines (deep-module seams, active domain modeling, public-seam TDD, hypothesis-driven bug diagnosis, and cold-reader documentation accuracy) alongside stack-specific `.agents/skills/<domain>/`, `.agents/skills/review-<domain>/`, and paired `.agents/agents/<domain>-{reviewer,specialist}.md` subagents.
   - Configures Git tracking (`shared` team mode vs. `local-only` stealth mode via `.git/info/exclude`) and opt-in cross-harness settings.
2. **Spec (`/flow:prd`, `/flow:spec`, `/flow:revise`, `/flow:research`) — Subagent-Scaled Co-Design & Upfront Chapter Blueprints**:
   - **Sharded Discovery & Questioning**: Fans out read-only Scout subagents returning structured `SubsystemDigest` payloads, then walks the Design-Tree Frontier (`1` question for dependent forks; `2–3` batched orthogonal leaf questions on settled frontiers via `structured-choice-v1`).
   - **High-Detail Chaptered Specifications (`/flow:prd` & `/flow:spec`)**: Locks cross-chapter seams, shared types, and a **Documentation & OKF Knowledge Plan** in root `specs/<flow_id>/spec.md` + `chapters/index.md`, then fans out parallel Chapter Planner subagents to author **all chapters (`ch01..chNN`, zero upper cap, `1–4` vertical-slice tasks per chapter) and 8-section task blueprints upfront**—scaling horizontally so plans, edge-case matrices, worked test cases, OKF provenance, and user docs gain depth without ever truncating scope or compacting context.
   - **Per-Chapter Zero-Context Spec Review & Revision (`/flow:revise`)**: Dispatches per-chapter zero-context reviewers passing only disk paths, adjudicates findings (`ADOPT`, `CONTEST`, `ESCALATE`), and keeps root `spec.md`, `chapters/index.md`, and chapter blueprints synchronized in present tense (current state, remaining chapters, and full plan—zero revision history inside specs).
   - **Research & Prototyping (`/flow:research`, alias `/flow:task`)**: Runs primary-source `@researcher` audits (promoted into OKF v0.2 `research/*.md` with `sources:` + `[^id]:` footnotes) or time-boxed throwaway prototypes in untracked `.agents/scratch/<slug>/`.
3. **Implement (`/flow:implement`, `/flow:status`) — Single-Chapter Execution & Pre-Review Sync**:
   - Resolves the active chapter (`current_chapter`), runs execution preflight (`dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`), and executes strictly **one chapter (`1–4` tasks)** per `/flow:implement` invocation via isolated `@executor` subagents bound to `Bounded Read Manifests` (`<= 6` files).
   - Closes each chapter by running the Chapter Recovery Checkpoint, syncing affected `.agents/bundles/knowledge/**`, `docs/**`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` in present tense, passing Zero-Context Chapter Code & Markdown-Sync Review (`@code-reviewer` + `@quality-reviewer`), stamping `last_reviewed_commit`, and stopping cleanly—enforced by cross-harness `Stop` hooks (`hooks/stop-check.{sh,ps1}` and OpenCode session checks).
4. **Learn & Document (`/flow:learn`, `/flow:docs`)**:
   - **`/flow:learn` (aliases `resynthesize`, `refresh`, `sync`)**: Runs anytime—across machines/harnesses, mid-flow, or post-flow—to reconcile Git history with task worksheets, intersect `git diff` against `sources[].resource` provenance, sharpen domain glossaries and Architectural Decision Records (`knowledge/decisions/adr-NNN-<slug>.md`), resynthesize `knowledge/**` in present tense, and synchronize `.agents/skills/` and `.agents/agents/`.
   - **`/flow:docs` (`write`, `validate`, `capture`, `sync`, `pr`)**: Tool-agnostic documentation, prose, and agent-context discipline grounded in cold-reader comprehension, manifest-driven `[k/N files documented]` source coverage, progressive disclosure ([`agent-context.md`](skills/flow-docs/references/agent-context.md)), and clean PR/commit/changelog hygiene ([`prs-commits-and-changelogs.md`](skills/flow-docs/references/prs-commits-and-changelogs.md)).
5. **Complete (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Runs zero-context code review across **Spec Conformance**, **Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells**, and **Mandatory Quality & Debloat Review (`quality-review-v1`)**, verifies release gates on the current branch, contracts durable learnings into `.agents/bundles/knowledge/**` + `.agents/bundles/log.md`, and removes completed spec directories.

## Flow Studio & Local Knowledge Catalog

Flow includes **Flow Studio** ([`studio.md`](skills/flow/references/studio.md))—a shared, low-noise UI core across **Google Antigravity** (`sidecars/studio/` `AuxPane` companion + `Sidebar` full Studio), **VS Code & Cursor** (`vscode-extension/`), and **standalone loopback HTTP + SSE** (`npx --yes --package github:cofin/flow flow-studio` / `make studio` for **Claude Code**, **Codex CLI**, and **OpenCode V2**):

- **Roadmap, Spec Authoring, & Line-Anchored Review**: Track chapter progress across single or portfolio workspaces, scaffold new `Spec` or `PRD` bundles (`+ New Spec`), attach line-anchored review notes on rendered `spec.md`, and dispatch batch revisions directly to `/flow:revise`.
- **Derived Hybrid DuckDB + EmbeddingGemma Catalog (`flow-catalog`)**: Indexes `.agents/bundles/` Markdown into a disposable local DuckDB catalog (`sqlspec` + `EmbeddingGemma-300m` ONNX Matryoshka `FLOAT[256]` embeddings + BM25 Reciprocal Rank Fusion), supporting reverse `path/to/file::Symbol` provenance lookups and source citation drift checks while degrading cleanly to pure BM25 when embeddings are not installed.
- **Python Runner Auto-Detection & Toggleable Cross-Harness Dispatch**: Automatically detects `uv`, `hatch`, `pdm`, `poetry`, `pipenv`, and `.venv` project entrypoints without requiring PyPI publication, and dispatches tasks or second-opinion reviews across `claude`, `codex`, `opencode`, `cursor-agent`, and `agy` in `direct-workspace` (default), `worktree-isolated`, or `read-only` mode (including loopback A2A v1 `/.well-known/agent-card.json` + `POST /a2a` and Antigravity lifecycle hooks).

## Install

### Google Antigravity

```bash
agy plugin install https://github.com/cofin/flow
```

When running in Google Antigravity, Flow automatically uses the `run_workflow` Python orchestration API (`phase()`, `parallel()`, `pipeline()`, `agent(..., type_name="self", schema=..., model="inherit")`) for sharded discovery scouts, upfront parallel chapter blueprint authoring, zero-context reviews, and isolated single-chapter task pipelines.

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
2. **Flow Studio Extension (`vscode-extension/`)**: Run the one-line installer directly from GitHub (no Git clone required) to bundle `vscode-extension/` + `sidecars/studio/` and register `cofin.flow-studio` into your editor's `extensions.json` (`~/.vscode/extensions`, `~/.cursor/extensions`, `~/.windsurf/extensions`, or `~/.positron/extensions`), then reload the window (`Developer: Reload Window`):

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
| `/flow:prd <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`prd.md`](skills/flow/references/prd.md) | Author multi-chapter roadmap (`spec.md` + `chapters/ch01..chNN/`) and upfront blueprints |
| `/flow:spec <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`spec.md`](skills/flow/references/spec.md) | Author high-detail specification (`spec.md`), `chapters/`, and `tasks/*.md` blueprints (alias: `plan`) |
| `/flow:revise <flow_id>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`revise.md`](skills/flow/references/revise.md) | Rewrite root `spec.md`, `chapters/`, and `tasks/*.md` in place in present tense (alias: `refine`) |
| `/flow:research <topic>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`research.md`](skills/flow/references/research.md) | Primary-source research & time-boxed `.agents/scratch/` spikes (alias: `task`) |
| `/flow:implement [flow_id]` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`implement.md`](skills/flow/references/implement.md) | Execute one chapter (`1–4` tasks) with Public-Seam TDD, doc/OKF sync, and chapter review |
| `/flow:status` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`status.md`](skills/flow/references/status.md) | Inspect active flows, chapter progress, remaining plan, and ready tasks |
| `/flow:learn [scope]` | [`flow-learn`](skills/flow-learn/SKILL.md) | [`learn.md`](skills/flow/references/learn.md) | Anytime reorientation (`refresh`), sync, `OKF v0.2` knowledge resynthesis, and skill sync |
| `/flow:docs [mode]` | [`flow-docs`](skills/flow-docs/SKILL.md) | [`prose-and-documentation.md`](skills/flow-docs/references/prose-and-documentation.md) | Tool-agnostic user/developer docs, [`agent-context.md`](skills/flow-docs/references/agent-context.md), changelogs, and clean PRs |
| `/flow:review [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`review.md`](skills/flow/references/review.md) | Zero-context Spec, Markdown-Sync, Standards, and mandatory Debloat quality review |
| `/flow:finish [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`finish.md`](skills/flow/references/finish.md) | Verify gates, chapter review stamps, ADR filter, and mark flow `completed` |
| `/flow:archive [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`archive.md`](skills/flow/references/archive.md) | Contract completed flow into `.agents/bundles/knowledge/**` and remove spec dir |
| `/flow:cleanup` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`cleanup.md`](skills/flow/references/cleanup.md) | Groundskeeping: reconcile specs, archive completed flows, and debloat touched files |
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
    ├── log.md                                    # Append-only ISO-dated changelog
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
            ├── tasks/<id>-<slug>.md              # Single-chapter flows (1-4 tasks)
            └── chapters/                         # Multi-chapter flows (ch01..chNN, zero upper cap)
                ├── index.md
                └── ch01-<slug>/
                    ├── spec.md
                    └── tasks/<id>-<slug>.md      # 1-4 vertical-slice tasks per chapter
```

## License

[Apache License 2.0](LICENSE)
