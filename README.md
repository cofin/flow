# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Context-Driven Development** that works with **Claude Code**, **Gemini CLI**, **Codex CLI**, **OpenCode**, and **Google Antigravity**. It combines spec-first planning with **Beads** for persistent cross-session memory, enabling AI-assisted development with deep, persistent project awareness.

## Philosophy

Control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction. Flow ensures a consistent, high-quality lifecycle for every task:

**Lifecycle:** Context → Spec & Plan → Implement → Learn

## Key Features

- **Beads Integration**: Persistent task memory that survives context compaction
- **Multi-CLI Support**: Works with Claude Code, Gemini CLI, Codex CLI, OpenCode, and Google Antigravity
- **Spec-First Development**: Create specs and plans before writing code
- **TDD Workflow**: Red-Green-Refactor with >80% coverage requirements
- **Knowledge Flywheel**: Capture and elevate patterns across flows (Ralph-style)
- **Flow Management**: Revise, archive, and revert with full audit trail
- **Git-Aware Revert**: Understands logical units of work, not just commits
- **Parallel Execution**: Phase-level task parallelism via sub-agents

## Install

Each host has a native plugin/extension system. Use it. The `tools/install.sh` script is a multi-host orchestrator for users who want to install Flow across several CLIs at once — it just runs the same native commands for you.

### Gemini CLI

```bash
gemini extensions install https://github.com/cofin/flow --auto-update
```

Update with `gemini extensions update flow`. Use `gemini extensions link .` only for local development against a checkout — Gemini copies installed extensions, so linked development and installed releases are different workflows.

<!-- markdownlint-disable -->
<details>
<summary>Recommended Gemini settings</summary>
<!-- markdownlint-restore -->

Flow's `gemini-extension.json` already sets `plan.directory: ".agents"` so `enter_plan_mode` / `exit_plan_mode` write the approval artifact under Flow's canonical `.agents/specs/` directory. You only need to enable planning + model routing yourself:

```json
{
  "general": {
    "plan": {
      "enabled": true,
      "modelRouting": true
    }
  }
}
```

Do not rely on undocumented `autoEnter` behavior for model routing.

</details>

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

Claude Code does not let plugin authors pre-declare a plan-artifact directory the way Gemini does. To get the equivalent behavior — plan-mode artifacts written under Flow's canonical `.agents/specs/` directory — set this in your project `.claude/settings.json`:

```json
{
  "plansDirectory": ".agents/specs"
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

Codex CLI has no plugin-author hook for a plan-artifact directory. The closest Gemini-equivalent knob is reasoning effort for plan mode — set in your `~/.codex/config.toml`:

```toml
plan_mode_reasoning_effort = "high"
```

</details>

<!-- markdownlint-disable -->
<details>
<summary>Manual / repo-scoped install (legacy)</summary>
<!-- markdownlint-restore -->

If you can't use the native marketplace command (e.g. team policy, private fork), clone Flow and register a personal or repo-scoped marketplace entry pointing at the checkout:

```bash
git clone https://github.com/cofin/flow.git ~/.codex/plugins/flow
```

Create `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "personal-plugins",
  "interface": { "displayName": "Personal Plugins" },
  "plugins": [
    {
      "name": "flow",
      "source": { "source": "local", "path": "~/.codex/plugins/flow" },
      "policy": { "installation": "AVAILABLE" },
      "category": "Development"
    }
  ]
}
```

Restart Codex and run `/plugins` to verify Flow appears. See `.codex/INSTALL.md` in this repo for repo-scoped variants.

</details>

### OpenCode

OpenCode's plugin model is local-plugin-files or npm packages. Flow ships a local plugin entrypoint and project-local skills:

```bash
git clone https://github.com/cofin/flow.git ~/.config/opencode/flow
mkdir -p ~/.config/opencode/plugins
ln -sf ~/.config/opencode/flow/.opencode/plugins/flow.js ~/.config/opencode/plugins/flow.js
```

Restart OpenCode after installing or updating plugin files. OpenCode also discovers skills from `.opencode/skills/`, `.claude/skills/`, and `.agents/skills/`, so Flow-compatible project-local skills do not require a global plugin install.

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

### Other hosts

<!-- markdownlint-disable -->
<details>
<summary>Cursor IDE</summary>
<!-- markdownlint-restore -->

In Cursor, run `/add-plugin` and search for **flow** in the marketplace ([cursor.com/marketplace](https://cursor.com/marketplace)). Cursor's marketplace went live in 2.4+ and supports private team marketplaces on Team/Enterprise plans.

For local development against a checkout, drop the repo into `~/.cursor/plugins/local/flow/` and restart Cursor — Cursor auto-discovers `.cursor-plugin/plugin.json` from there.

</details>

<!-- markdownlint-disable -->
<details>
<summary>Google Antigravity</summary>
<!-- markdownlint-restore -->

Prefer workspace-local `.agents` customizations when possible:

- `.agents/skills/`
- `.agents/rules/`
- `.agents/workflows/`

Use a global skill install only as a fallback for environments that do not yet use project-local agent assets consistently.

</details>

<!-- markdownlint-disable -->
<details>
<summary>Multi-host installer (`tools/install.sh`)</summary>
<!-- markdownlint-restore -->

For installing Flow across several CLIs in one pass, the script auto-detects installed hosts and runs the same native commands listed above:

```bash
git clone https://github.com/cofin/flow.git
cd flow
./tools/install.sh
```

Or run it directly:

```bash
curl -fsSL https://raw.githubusercontent.com/cofin/flow/main/tools/install.sh | bash
```

The script is a convenience orchestrator. Prefer the per-host native commands above when installing into a single CLI.

</details>

## Quick Start

### Initialize a project

```bash
# Claude Code
/flow-setup

# Gemini CLI / OpenCode
/flow:setup
```

In Codex CLI, ask: `Use Flow to set up this project`

Flow will:

1. Detect the preferred persistence mode: official Beads (`bd`), `br` compatibility, or no-Beads degraded mode
2. Initialize the selected backend in low-admin mode
3. Default local-only ignores to `.git/info/exclude`
4. Create project context files
5. Guide you through product, tech stack, and workflow setup
6. Create your first flow

### Create a flow

```bash
# Claude Code
/flow-prd "Add user authentication"

# Gemini CLI / OpenCode
/flow:prd "Add user authentication"
```

In Codex CLI, ask: `Use Flow to create a PRD for add user authentication`

This creates `spec.md` (unified spec + plan), `learnings.md` (pattern capture log), `.agents/skills/flow-memory-keeper/SKILL.md` (project-local sync/archive/learnings/refinement skill), and a Beads epic with tasks for cross-session persistence.

> Flow uses a unified `spec.md` (no separate `plan.md`). Beads is the source of truth for task status. Use `/flow:sync` to export Beads state to `spec.md` (MANDATORY after every state change).

### Implement

```bash
# Claude Code
/flow-implement auth

# Gemini CLI / OpenCode
/flow:implement auth
```

In Codex CLI, ask: `Use Flow to implement auth`

Flow follows a TDD workflow with a backend adapter: detect persistence mode, select the next task, write failing tests → implement → refactor → verify coverage → commit (conventional format) → record completion → capture learnings → `/flow-sync`.

> **CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers directly to `spec.md`. Beads is the source of truth. After ANY Beads state change, agents MUST run `/flow-sync` to update `spec.md`.

## Commands

| Purpose | Claude Code | Gemini CLI / OpenCode |
|---------|-------------|-----------------------|
| Initialize project | `/flow-setup` | `/flow:setup` |
| Create PRD (Saga) | `/flow-prd` | `/flow:prd` |
| Plan single flow | `/flow-plan` | `/flow:plan` |
| Sync Beads to spec | `/flow-sync` | `/flow:sync` |
| Pre-PRD research | `/flow-research` | `/flow:research` |
| Documentation workflow | `/flow-docs` | `/flow:docs` |
| Implement tasks | `/flow-implement` | `/flow:implement` |
| Check status | `/flow-status` | `/flow:status` |
| Refresh context | `/flow-refresh` | `/flow:refresh` |
| Revert changes | `/flow-revert` | `/flow:revert` |
| Validate integrity | `/flow-validate` | `/flow:validate` |
| Revise spec/plan | `/flow-revise` | `/flow:revise` |
| Archive completed | `/flow-archive` | `/flow:archive` |
| Ephemeral task | `/flow-task` | `/flow:task` |
| Code review | `/flow-review` | `/flow:review` |
| Finish flow | `/flow-finish` | `/flow:finish` |

> Claude Code uses `/flow-command` (hyphen). Gemini CLI and OpenCode use `/flow:command` (colon). Codex CLI currently uses the installed Flow skill through plain-language requests instead of plugin-defined slash commands.

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
│   ├── flows.md             # Flow registry with status
│   ├── patterns.md          # Consolidated learnings
│   ├── beads.json           # Beads configuration
│   ├── index.md             # File resolution index
│   ├── code-styleguides/    # Language style guides
│   ├── knowledge/           # Persistent knowledge base
│   │   ├── index.md          # Quick reference index
│   │   └── {flow_id}.md      # Per-flow detailed learnings
│   ├── skills/
│   │   └── flow-memory-keeper/
│   │       └── SKILL.md      # Local memory/refinement skill
│   ├── specs/
│   │   └── <flow_id>/       # e.g., user-auth/
│   │       ├── spec.md       # Unified spec + plan
│   │       ├── learnings.md
│   │       └── metadata.json
│   └── archive/             # Completed flows
└── .beads/                  # Beads data (local-only)
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
| `[!]` | Blocked | Cannot proceed (logged in `blockers.md`) |
| `[-]` | Skipped | Intentionally bypassed (logged in `skipped.md`) |

</details>

<!-- markdownlint-disable -->
<details>
<summary>Beads integration (modes, init, ignore policy)</summary>
<!-- markdownlint-restore -->

Flow supports three persistence modes:

- **Official Beads (`bd`)**: preferred default
- **beads_rust (`br`)**: compatibility mode for older repos and command docs
- **No Beads**: degraded mode for docs, planning, and lightweight local work

**Default initialization.** Flow defaults to stealth mode and derives a slugged prefix from the repo name:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
bd init --stealth --prefix "$repo_slug"
# or, for br compatibility:
br init --prefix "$repo_slug"
```

**Install paths.**

```bash
# Official Beads (bd)
brew install beads
# or:
curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# beads_rust compatibility (br)
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```

**Local-only ignore policy.** Prefer `.git/info/exclude`:

```bash
printf '\n# Flow local-only artifacts\n.beads/\n.agents/\n' >> .git/info/exclude
```

Only update `.gitignore` when the user explicitly wants a shared repo policy.

**Session protocol.** Start: detect active backend and load workspace state. Work: update task status as you progress. Learn: add notes for important discoveries. End: persist backend state when enabled, or rely on `.agents/specs/` + git history in degraded mode.

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

## Documentation

- [CLAUDE.md](CLAUDE.md) — Claude Code context and reference
- [GEMINI.md](GEMINI.md) — Gemini CLI context and reference

## Resources

- [GitHub Issues](https://github.com/cofin/flow/issues) — Report bugs or request features
- [Beads CLI](https://github.com/steveyegge/beads) — Official `bd` task persistence layer
- [beads_rust](https://github.com/Dicklesworthstone/beads_rust) — `br` compatibility backend

## License

[Apache License 2.0](LICENSE)
