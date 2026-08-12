# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Context-Driven Development** that works with **Antigravity**, **Codex CLI**, **Claude Code**, **OpenCode**, **VS Code / Copilot**, **Cursor**, and **OpenClaw**. It combines spec-first planning with a local, task-centric filesystem engine (OKF) to track task state and learnings, enabling AI-assisted development with deep, persistent project awareness.

## Philosophy

Control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction. Flow ensures a consistent, high-quality lifecycle for every task:

**Lifecycle:** Context → Spec & Plan → Implement → Learn

## Key Features

- **Task-Centric Filesystem Engine (OKF)**: Persistent task files and specs that survive context compaction and are git-tracked
- **Multi-Harness Support**: Works with Antigravity, Codex CLI, Claude Code, OpenCode, VS Code / Copilot, Cursor, and OpenClaw
- **Spec-First Development**: Create specs and task lists before writing code
- **TDD Workflow**: Red-Green-Refactor with >80% coverage requirements
- **Knowledge Flywheel**: Capture and elevate patterns across flows (Ralph-style)
- **Flow Management**: Revise, archive, and revert with full audit trail
- **Git-Aware Revert**: Reverts logical units of work (tasks or phases), not just raw commits
- **Parallel Execution**: Phase-level task parallelism via sub-agents

## Install

Use each harness's native plugin, marketplace, rules, or skills mechanism. Flow no longer ships a multi-harness installer or symlink-based install path.

### Antigravity

Install Flow through Antigravity's native Plugins & Skills flow from the `cofin/flow` repository. Flow ships the Antigravity plugin manifest at `plugin.json` and the root SessionStart hook manifest at `hooks.json`.

After installing or updating the plugin, restart Antigravity so the plugin manifest, skills, agents, and hooks are reloaded.

### Claude Code

```bash
claude plugin marketplace add cofin/flow
claude plugin install flow@flow-marketplace
```

This installs Flow at user scope (`~/.claude/plugins/...`). Restart Claude Code after install. The plugin ships skills, commands, and hooks; Claude-specific subagents remain optional and are not bundled in the current release.

<!-- markdownlint-disable -->
<details>
<summary>Update commands</summary>
<!-- markdownlint-restore -->

```bash
claude plugin marketplace update flow-marketplace
claude plugin update flow@flow-marketplace
```

</details>

<!-- markdownlint-disable -->
<details>
<summary>Recommended Claude Code settings</summary>
<!-- markdownlint-restore -->

Claude Code does not let plugin authors pre-declare a plan-artifact directory. To keep plan artifacts under Flow's canonical `.agents/bundles/specs/` directory, set this in your project `.claude/settings.json`:

```json
{
  "plansDirectory": ".agents/bundles/specs"
}
```

Optionally, force plan mode by default for Flow projects:

```json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

Verify the keys against your Claude Code version's [settings reference](https://code.claude.com/docs/en/settings).

</details>

### Codex CLI

```bash
codex plugin marketplace add cofin/flow
```

Then in a Codex session, run `/plugins` and enable Flow. Update with `codex plugin marketplace upgrade flow-marketplace`.

Codex CLI 0.117+ supports first-class marketplace commands — `add` accepts `owner/repo[@ref]`, HTTPS/SSH git URLs, or local paths, with optional `--ref <REF>` and `--sparse <PATH>`.

> Codex plugins do not currently expose plugin-defined `/flow:*` slash commands. Use Flow through the installed Flow skill with natural-language requests such as `Use Flow to set up this project`.

<!-- markdownlint-disable -->
<details>
<summary>Recommended Codex settings</summary>
<!-- markdownlint-restore -->

Codex CLI has no plugin-author hook for a plan-artifact directory. The closest useful knob is reasoning effort for plan mode — set in your `~/.codex/config.toml`:

```toml
plan_mode_reasoning_effort = "high"
```

</details>

### OpenCode

OpenCode supports npm plugins and local plugin files. Flow currently ships OpenCode-compatible project files and skills, but does not advertise a global install until a package is published through OpenCode's npm plugin path.

OpenCode also discovers skills from `.opencode/skills/`, `.claude/skills/`, and `.agents/skills/`, so Flow-compatible project-local skills do not require a global plugin install.

<!-- markdownlint-disable -->
<details>
<summary>Recommended OpenCode settings</summary>
<!-- markdownlint-restore -->

OpenCode has no plugin-author hook for a plan-artifact directory. Set sensible defaults in your project `opencode.json`:

```json
{
  "permission": { "edit": "ask", "bash": "ask" }
}
```

</details>

### Other harnesses

<!-- markdownlint-disable -->
<details>
<summary>Cursor IDE</summary>
<!-- markdownlint-restore -->

Cursor consumes Flow through project rules and shared repository instructions:

- `.cursor/rules/flow.mdc`
- `AGENTS.md`
- project-local skills when copied or linked into `.agents/skills/`

Do not install Flow through a repository `.cursor-plugin/plugin.json`; Flow does not ship a Cursor plugin manifest until Cursor exposes a stable documented plugin API for this use case.

</details>

<!-- markdownlint-disable -->
<details>
<summary>VS Code / Copilot</summary>
<!-- markdownlint-restore -->

VS Code discovers Flow custom agents from `.github/agents/*.agent.md` and shared skills from `.agents/skills/`, `.claude/skills/`, or `.github/skills/`. Flow ships workspace agent definitions for the core lifecycle agents.

Use VS Code settings such as `chat.agentSkillsLocations` only when you need additional skill directories beyond the standard project paths.

</details>

<!-- markdownlint-disable -->
<details>
<summary>OpenClaw</summary>
<!-- markdownlint-restore -->

OpenClaw should consume Flow through runtime skill discovery and its native `sessions_spawn` subagent mechanism. Flow does not ship a static OpenClaw plugin manifest.

</details>

## Quick Start

### Initialize a project

```bash
# Claude Code
/flow-setup

# Antigravity / OpenCode
/flow:setup
```

In Codex CLI, ask: `Use Flow to set up this project`

Flow will:

1. Create the Flow directory (defaults to `.agents/`)
2. Configure local ignores in `.git/info/exclude` to keep specifications local-only
3. Create project context files (`product.md`, `tech-stack.md`, `workflow.md`, `patterns.md`)
4. Guide you through product vision, tech stack configuration, and repository-native workflow commands setup

### Create a flow

```bash
# Claude Code
/flow-prd "Add user authentication"

# Antigravity / OpenCode
/flow:prd "Add user authentication"
```

In Codex CLI, ask: `Use Flow to create a PRD for add user authentication`

This creates a new specification bundle under `.agents/bundles/specs/<flow_id>/`:

- `spec.md` (unified spec + implementation plan)
- `learnings.md` (per-flow discoveries log)
- `tasks/` directory to store individual task markdown files

> Flow uses a unified `spec.md` implementation plan. Task statuses are tracked inside individual task files under `tasks/*.md` using YAML frontmatter. Run `/flow:sync` to reconcile `spec.md` checklists with the task files.

### Implement

```bash
# Claude Code
/flow-implement auth

# Antigravity / OpenCode
/flow:implement auth
```

In Codex CLI, ask: `Use Flow to implement auth`

Flow follows a TDD workflow:

1. Select the next ready task from `spec.md`
2. Claim the task: update `status` to `in_progress` in `tasks/<short_id>.md` and run `/flow:sync` to update `spec.md`
3. Write failing tests (Red)
4. Implement code to pass tests (Green)
5. Refactor while tests pass
6. Commit the task changes: `<type>(<scope>): <description>`
7. Close the task: update `status` to `closed` and set `commit: <sha>` in the task frontmatter
8. Record learnings inside the task file under `## Notes & Discoveries`
9. Run `/flow:sync` to reconcile status and append the commit SHA `[<sha>]` to the `spec.md` task checklist

## Commands

Flow keeps command behavior aligned, but each harness exposes a different command surface.

| Purpose | Claude Code | Antigravity | OpenCode | Codex CLI |
|---------|-------------|-------------|----------|-----------|
| Lifecycle commands | `/flow-setup`, `/flow-prd`, `/flow-plan`, etc. from `commands/flow-*.md` | Skill-derived slash commands from `skills/` such as `/flow`, `/flow-setup`, and lifecycle skills | Project/native command files when configured; otherwise use the Flow skill/plugin context | Natural-language Flow skill requests |
| Canonical prompt source | `commands/flow-*.md` | `skills/*/SKILL.md` plus `commands/flow/*.toml` as shared prompt source material | `templates/opencode/commands/*.md` for project command installs | `skills/*/SKILL.md` in the generated plugin package |
| Subagents | `agents/*.md` | `agents/*.md` | `.opencode/agents/*.md` | `.codex/agents/*.toml` |

Codex plugins do not currently expose plugin-defined `/flow:*` slash commands. OpenCode command names depend on whether the user installs project command files or uses the plugin context.

## Reference

<!-- markdownlint-disable -->
<details>
<summary>Directory structure</summary>
<!-- markdownlint-restore -->

```text
project/
├── .agents/
│   ├── product.md           # Product vision and goals
│   ├── product-guidelines.md # Brand/style guidelines
│   ├── tech-stack.md        # Technology choices
│   ├── workflow.md          # Development workflow (TDD, commits)
│   ├── patterns.md          # Consolidated learnings
│   ├── index.md             # File resolution index
│   ├── code-styleguides/    # Language style guides
│   ├── bundles/
│   │   ├── knowledge/       # Persistent knowledge base
│   │   │   ├── index.md      # Quick reference index
│   │   │   └── {flow_id}.md  # Per-flow detailed learnings
│   │   └── specs/
│   │       └── <flow_id>/   # e.g., user-auth/
│   │           ├── spec.md   # Unified spec + plan
│   │           ├── learnings.md
│   │           └── tasks/    # Task definitions
│   │               └── 1.1.md
│   └── archive/             # Completed flows
```

</details>

<!-- markdownlint-disable -->
<details>
<summary>Flow naming &amp; status markers</summary>
<!-- markdownlint-restore -->

Flows use format `shortname` — examples: `user-auth`, `dark-mode`, `api-v2`.

| Marker | Status | Description |
|--------|--------|-------------|
| `[ ]` | Pending | Not started |
| `[~]` | In Progress | Currently working |
| `[x]` | Completed | Done with commit SHA |
| `[!]` | Blocked | Cannot proceed (status: blocked in task file) |
| `[-]` | Skipped | Intentionally bypassed (status: skipped in task file) |

</details>

<!-- markdownlint-disable -->
<details>
<summary>Local Specs ignore guidelines</summary>
<!-- markdownlint-restore -->

By default, the `.agents/` directory is checked into Git so that specifications, implementation plans, and task histories are version-controlled alongside your code.

If you prefer to keep all Flow specifications and task files local-only (e.g. to avoid committing agent metadata to your repository), you can ignore the `.agents/` directory locally.

**Local Ignore Configuration**:
To ignore the `.agents/` directory only in your local clone without affecting other developers, append it to `.git/info/exclude` instead of `.gitignore`:

```bash
printf '\n# Flow specifications (local-only)\n.agents/\n' >> .git/info/exclude
```

</details>

<!-- markdownlint-disable -->
<details>
<summary>Knowledge system (three-tier flywheel)</summary>
<!-- markdownlint-restore -->

**Per-flow learnings** — each flow has `learnings.md`:

```markdown
## [2026-01-24 14:30] - Phase 1 Task 2: Add auth middleware
- **Files changed:** src/auth/middleware.ts
- **Commit:** abc1234
- **Learning:** Codebase uses Zod for validation
- **Pattern:** Import order: external → internal → types
```

**Project patterns** — consolidated in `patterns.md`:

```markdown
# Code Conventions
- Import order: external → internal → types

# Gotchas
- Always update barrel exports
```

**Persistent knowledge base** — learnings synthesized into cohesive, logically organized chapters in `knowledge/` during sync and archival. Content is integrated directly into existing chapters to describe the current state of the codebase.

**Flywheel:**

1. **Capture** — After each task, append learnings to `learnings.md`
2. **Elevate** — At phase/flow completion, move patterns to `patterns.md`
3. **Synthesize** — During sync and archive, integrate learnings directly into knowledge base chapters in `knowledge/` (e.g., `architecture.md`, `conventions.md`). Update current state, do not outline history.
4. **Inherit** — New flows read `patterns.md` + scan `knowledge/` chapters.

If `.agents/skills/flow-memory-keeper/SKILL.md` exists, use it at sync, archive, finish, revise, and failure checkpoints so spec cleanup, learnings capture, and refinement stay mandatory.

</details>

<!-- markdownlint-disable -->
<details>
<summary>Skills library</summary>
<!-- markdownlint-restore -->

Flow includes 50+ technology-specific skills in `skills/`:

| Category | Skills |
|----------|--------|
| **Frontend** | React, Vue, Svelte, Angular, TanStack |
| **Backend** | Litestar, Rust, PyO3, napi-rs |
| **Database** | SQLSpec, Advanced Alchemy, pytest-databases |
| **Testing** | pytest, Vitest, testing patterns |
| **Infrastructure** | GKE, Cloud Run, Railway |
| **Tools** | Vite, Tailwind, Shadcn, HTMX |

Copy to your CLI's skills directory for auto-activation.

</details>

## Resources

- [GitHub Issues](https://github.com/cofin/flow/issues) — Report bugs or request features

## License

[Apache License 2.0](LICENSE)
