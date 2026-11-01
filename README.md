# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Spec-Driven Development** backed by **Open Knowledge Format (`OKF v0.2`)** bundles. It works natively from a single repository root across **Google Antigravity** (IDE & CLI), **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / Copilot**.

## Architecture & Lifecycle

Flow combines **Conductor's persistent context pillars**, **Elephant & Goldfish epistemic separation**, and **deep-module & public-seam TDD engineering disciplines**:

1. **Setup (`/flow:setup`)**: Runs Brownfield Alignment & Legacy Migration, scaffolds Conductor's 4 context pillars (`product/product.md`, `product/product-guidelines.md`, `product/tech-stack.md`, and `knowledge/workflow.md`) with bounded `<= 40`-line `<!-- truth: start -->` blocks, synthesizes project-local domain and review skills under `.agents/skills/`, and generates paired project-local subagents under `.agents/agents/`.
2. **Plan (`/flow:prd`, `/flow:plan`, `/flow:revise`, `/flow:research`) — The Stateful Elephant**:
   - **Master PRD (`/flow:prd`)**: Decomposes multi-flow initiatives into locked architectural decisions, a Mandatory Alternatives Table, and ordered `state: draft` child flow charters.
   - **Feature Specification (`/flow:plan`)**: Interviews the user along the Design-Tree Frontier (separating agent-researched *Facts* from user *Decisions*), authors a 5-section specification (`spec.md`) with deep-module seams (*"Design It Twice"*) and `1–8` disjoint vertical-slice task worksheets (`tasks/<id>-<slug>.md`) anchored to `path/to/file::Symbol`, dispatches stateless Goldfish reviewers under the Zero-Memory Anti-Leakage Rules, and adjudicates findings (`ADOPT`, `CONTEST`, or `ESCALATE`).
3. **Implement (`/flow:implement`, `/flow:status`) — The Stateless Goldfish Executor**: Runs the 5-check preflight (failing closed before modifying production files on symbol/requirement drift), executes one approved task worksheet per `@executor` subagent turn using Public-Seam Vertical-Slice TDD (or the 6-Phase Hypothesis-Driven Bug Diagnosis Loop when blocked), creates an atomic Git commit, and updates task frontmatter + `spec.md` checklists directly.
4. **Learn & Document (`/flow:learn`, `/flow:docs`)**:
   - **`/flow:learn`**: Runs anytime (`refresh`, `sync`, `resynthesize`) to reorient across machines/harnesses, intersect `git diff` against `sources:` provenance, sharpen domain glossaries and 3-part ADRs, resynthesize `knowledge/**` across 5 dimensions with `writing-for-agents` pruning, and sync `.agents/skills/`.
   - **`/flow:docs`**: Tool-agnostic documentation & communication discipline (`write`, `validate`, `capture`, `sync`, `pr`) grounded in Goldfish comprehension, manifest-driven `[k/N files documented]` coverage, `writing-for-agents` context efficiency, and clean PR/commit/changelog hygiene.
5. **Complete (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`)**: Runs zero-context Two-Axis Code Review (Spec Conformance + Repo Standards / Deep-Module Seams / Fowler's 12 Baseline Code Smells) plus mandatory Debloat Quality Review (`quality-review-v1`), verifies release gates, contracts durable learnings into `.agents/bundles/knowledge/**` + `.agents/bundles/log.md`, and removes completed spec directories.

## Install

### Google Antigravity

Install from GitHub or a local checkout:

```bash
git clone https://github.com/cofin/flow.git ~/.Flow
agy plugin install ~/.Flow
```

Upgrade an existing installation:

```bash
cd ~/.Flow
git pull
agy plugin install ~/.Flow
```

Flow ships [`plugin.json`](plugin.json), the always-on operational rule [`rules/flow-antigravity.md`](rules/flow-antigravity.md), the root `SessionStart` hook [`hooks.json`](hooks.json), 10 core skills under [`skills/`](skills/), and 6 subagents under [`agents/`](agents/). When running in Google Antigravity, Flow automatically leverages the `run_workflow` Python orchestration API (`phase()`, `parallel()`, `pipeline()`, `agent(..., schema=..., model="inherit")`) for parallel zero-context reviews, persistent multi-turn reviewer handles, and task worksheet pipelines.

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

Install Flow as a native Cursor plugin (`.cursor-plugin/plugin.json`). Cursor automatically discovers `skills/*/SKILL.md`, `agents/*.md`, `rules/flow-antigravity.md`, and `hooks/hooks-cursor.json`.

### OpenCode V2

Flow ships an in-process OpenCode V2 plugin at [`.opencode/plugins/flow.js`](.opencode/plugins/flow.js) (`package.json` `main`), which registers Flow's 6 subagents and injects workspace `.agents/` context using native `node:fs` with zero external runtime dependencies.

### VS Code / Copilot

Install Flow through **Chat: Install Plugin From Source** using [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json). VS Code discovers `skills/*/SKILL.md`, `agents/*.md`, `rules/flow-antigravity.md`, and `hooks/hooks-claude.json`.

## Commands & Lifecycle Skills

| Command | Lifecycle Skill | Reference Procedure | Description |
| --- | --- | --- | --- |
| `/flow:setup` | [`flow-setup`](skills/flow-setup/SKILL.md) | [`setup.md`](skills/flow/references/setup.md) | Bootstrap `.agents/bundles/`, `.agents/skills/`, and `.agents/agents/` |
| `/flow:prd <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`prd.md`](skills/flow/references/prd.md) | Author Master PRD roadmap (`spec.md`) and seed child flow charters |
| `/flow:plan <goal>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`plan.md`](skills/flow/references/plan.md) | Author Feature Specification (`spec.md`) and `tasks/<id>-<slug>.md` worksheets |
| `/flow:revise <flow_id>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`revise.md`](skills/flow/references/revise.md) | Rewrite `spec.md` and `tasks/*.md` in place in present tense (alias: `refine`) |
| `/flow:research <topic>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`research.md`](skills/flow/references/research.md) | Primary-source research & time-boxed `.agents/scratch/` spikes (alias: `task`) |
| `/flow:implement [flow_id]` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`implement.md`](skills/flow/references/implement.md) | Execute ready task worksheets with Public-Seam TDD and atomic commits |
| `/flow:status` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`status.md`](skills/flow/references/status.md) | Inspect active flows, phase progress bars, and ready tasks |
| `/flow:learn [scope]` | [`flow-learn`](skills/flow-learn/SKILL.md) | [`learn.md`](skills/flow/references/learn.md) | Anytime reorientation (`refresh`), sync, 5-dimension knowledge resynthesis, and skill sync |
| `/flow:docs [mode]` | [`flow-docs`](skills/flow-docs/SKILL.md) | [`prose-and-documentation.md`](skills/flow-docs/references/prose-and-documentation.md) | Tool-agnostic user/developer docs, `writing-for-agents`, changelogs, and clean PRs |
| `/flow:review [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`review.md`](skills/flow/references/review.md) | Zero-context Two-Axis + mandatory Debloat quality review |
| `/flow:finish [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`finish.md`](skills/flow/references/finish.md) | Verify gates, evaluate 3-part ADR filter, and mark flow `completed` |
| `/flow:archive [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`archive.md`](skills/flow/references/archive.md) | Contract completed flow into `.agents/bundles/knowledge/**` and remove spec dir |
| `/flow:cleanup` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`cleanup.md`](skills/flow/references/cleanup.md) | 4-phase groundskeeping: reconcile specs, archive completed flows, and debloat touched files |
| `/flow:revert <scope>` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`revert.md`](skills/flow/references/revert.md) | Git-aware revert of a task, phase, or flow |
| `/flow:validate` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`validate.md`](skills/flow/references/validate.md) | 6-phase validator for `.agents/bundles/` and `.agents/skills/` integrity |

## Consumer Repository `.agents/` Layout

```text
.agents/
├── setup-state.json                              # Active bundle root & setup state
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
    └── specs/<flow_id>/
        ├── spec.md
        ├── learnings.md
        ├── research/<topic>_<YYYYMMDD>.md
        └── tasks/<id>-<slug>.md
```

## License

[Apache License 2.0](LICENSE)
