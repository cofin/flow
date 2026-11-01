# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Spec-Driven Development** backed by **Open Knowledge Format (`OKF v0.2`)** bundles. It works natively from a single repository root across **Google Antigravity** (IDE & CLI), **Claude Code**, **Codex CLI**, **Cursor**, **OpenCode V2**, and **VS Code / Copilot**.

## Architecture & Lifecycle

Flow separates **Stateful Planning & Adjudication** from **Dynamic, Zero-Context Focused Review** and **Stateless Vertical-Slice Task Execution**:

1. **Setup (`/flow:setup`)**: Probes your repository's toolchain, scaffolds `.agents/bundles/` (`product/`, `knowledge/`, `research/`, `specs/`), synthesizes project-local domain and review skills under `.agents/skills/`, and generates paired project-local subagents under `.agents/agents/`.
2. **Plan (`/flow:prd`, `/flow:plan`, `/flow:revise`, `/flow:research`)**:
   - **Master PRD (`/flow:prd`)**: Decomposes multi-flow initiatives into locked architectural decisions and ordered `state: draft` child flow charters.
   - **Feature Specification (`/flow:plan`)**: Authors a 5-section specification (`spec.md`) and `1–8` disjoint vertical-slice task worksheets (`tasks/<id>-<slug>.md`) anchored to `path/to/file::Symbol`, dispatches zero-context reviewers using only on-disk paths, and adjudicates findings (`ADOPT` vs. `CONTEST` with evidence).
3. **Implement (`/flow:implement`, `/flow:status`)**: Executes one approved task worksheet per `@executor` subagent turn against the real System Under Test (SUT), verifies Red/Green TDD or the declared verification strategy, creates an atomic Git commit, and updates task frontmatter + `spec.md` checklists directly.
4. **Learn (`/flow:learn`)**: Runs anytime (mid-flow, post-flow, or standalone) to audit codebase/Git/spec drift, reconcile active specs and task worksheets, resynthesize `.agents/bundles/knowledge/**` chapters, and synchronize `.agents/skills/` and `.agents/agents/`.
5. **Complete (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`)**: Runs zero-context correctness and debloat quality review across `base_commit..HEAD`, verifies all release gates, contracts durable learnings into `.agents/bundles/knowledge/**` + `.agents/bundles/log.md`, and removes completed spec directories.

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
| `/flow:research <topic>` | [`flow-planning`](skills/flow-planning/SKILL.md) | [`research.md`](skills/flow/references/research.md) | Primary-source research & exploratory spikes (alias: `task`) |
| `/flow:implement [flow_id]` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`implement.md`](skills/flow/references/implement.md) | Execute ready task worksheets with TDD/SUT verification and atomic commits |
| `/flow:status` | [`flow-execution`](skills/flow-execution/SKILL.md) | [`status.md`](skills/flow/references/status.md) | Inspect active flows, task progress, and ready tasks |
| `/flow:learn [scope]` | [`flow-learn`](skills/flow-learn/SKILL.md) | [`learn.md`](skills/flow/references/learn.md) | Anytime drift true-up, knowledge resynthesis, and skill/agent sync (aliases: `resynthesize`, `refresh`, `sync`) |
| `/flow:docs` | [`flow-docs`](skills/flow-docs/SKILL.md) | [`guides-and-api-docs.md`](skills/flow-docs/references/guides-and-api-docs.md) | Write user guides, API reference pages, changelogs, and clean pull requests |
| `/flow:review [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`review.md`](skills/flow/references/review.md) | Zero-context correctness & mandatory debloat quality review |
| `/flow:finish [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`finish.md`](skills/flow/references/finish.md) | Run full verification gates and mark flow `completed` |
| `/flow:archive [flow_id]` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`archive.md`](skills/flow/references/archive.md) | Contract completed flow into `.agents/bundles/knowledge/**` and remove spec dir |
| `/flow:cleanup` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`cleanup.md`](skills/flow/references/cleanup.md) | Reconcile specs, archive completed flows, and debloat touched files |
| `/flow:revert <scope>` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`revert.md`](skills/flow/references/revert.md) | Git-aware revert of a task, phase, or flow |
| `/flow:validate` | [`flow-completion`](skills/flow-completion/SKILL.md) | [`validate.md`](skills/flow/references/validate.md) | Validate `.agents/bundles/` and `.agents/skills/` integrity |

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
