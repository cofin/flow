# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Context-Driven Development** that works with **Claude Code**, **Gemini CLI**, **Codex CLI**, **OpenCode**, and **Google Antigravity**. It combines spec-first planning with **Beads** for persistent cross-session memory, enabling AI-assisted development with deep, persistent project awareness.

## Philosophy

Control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction. Flow ensures a consistent, high-quality lifecycle for every task:

### Lifecycle

- **Context → Spec & Plan → Implement → Learn**

## Key Features

- **Beads Integration**: Persistent task memory that survives context compaction
- **Multi-CLI Support**: Works with Claude Code, Gemini CLI, Codex CLI, OpenCode, and Google Antigravity
- **Spec-First Development**: Create specs and plans before writing code
- **TDD Workflow**: Red-Green-Refactor with >80% coverage requirements
- **Knowledge Flywheel**: Capture and elevate patterns across flows (Ralph-style)
- **Flow Management**: Revise, archive, and revert with full audit trail
- **Git-Aware Revert**: Understands logical units of work, not just commits
- **Parallel Execution**: Phase-level task parallelism via sub-agents

## Quick Start

### Installation

#### Intelligent Installer (Recommended)

The install script detects your CLIs, backs up existing configs, and merges intelligently:

```bash
# Clone the repo
git clone https://github.com/cofin/flow.git
cd flow

# Run installer
./tools/install.sh
```

The installer supports:

- **Claude Code** (`~/.claude/`)
- **Codex CLI** (`~/.codex/`)
- **OpenCode** (`~/.config/opencode/`)
- **Google Antigravity** (workspace-local `.agents/` preferred, global fallback available)

Flow now prefers official host-native install flows where they exist, and reserves local links/wrappers for development-oriented hosts.

## Installation

Flow can be installed as a native plugin or extension on supported AI CLI platforms.

### Gemini CLI

```bash
gemini extensions install https://github.com/cofin/flow --auto-update
```

To update:

```bash
gemini extensions update flow
```

Use `gemini extensions link .` only for local development against a checkout. Gemini copies installed extensions, so linked development and installed releases are different workflows.

### Claude Code

Install Flow via marketplace (recommended for reliability):

```bash
claude plugin marketplace add cofin/flow
claude plugin install flow@flow-marketplace
```

This installs Flow at user scope (`~/.claude/plugins/...`).

To update explicitly:

```bash
claude plugin marketplace update flow-marketplace
claude plugin update flow@flow-marketplace
```

Claude supports git-based marketplaces directly. Prefer the marketplace flow over ad-hoc local config edits.

### OpenCode

OpenCode's official plugin model is local-plugin-files or npm packages. Flow currently ships a local plugin entrypoint and project-local skills, so the recommended path is:

```bash
git clone https://github.com/cofin/flow.git ~/.config/opencode/flow
mkdir -p ~/.config/opencode/plugins
ln -sf ~/.config/opencode/flow/.opencode/plugins/flow.js ~/.config/opencode/plugins/flow.js
```

Restart OpenCode after installing or updating plugin files.

OpenCode also discovers skills from `.opencode/skills/`, `.claude/skills/`, and `.agents/skills/`, so Flow-compatible project-local skills do not require a global plugin install.

### Cursor IDE

Install Flow from the plugin system:

```text
/add-plugin flow
```

Or add to your `.cursor-plugin` configuration manually.

### Codex CLI

Install Flow as a Codex plugin with a local linked source and a marketplace entry:

1. Clone Flow:

   ```bash
   git clone https://github.com/cofin/flow.git ~/.codex/plugins/flow
   ```

2. Create marketplace entry at `~/.agents/plugins/marketplace.json`:

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

3. Restart Codex. Run `/plugins` to verify Flow appears.

Codex plugins use `.codex-plugin/plugin.json` plus `.agents/plugins/marketplace.json`. Treat the marketplace metadata as the catalog and the installed plugin as a cached copy that may refresh independently of the source checkout.

Current Codex plugin support does not expose plugin-defined `/flow:*` slash commands. Use Flow through the installed Flow skill with natural-language requests such as `Use Flow to set up this project`.

### Google Antigravity

Prefer workspace-local `.agents` customizations when possible:

- `.agents/skills/`
- `.agents/rules/`
- `.agents/workflows/`

Use a global skill install only as a fallback for environments that do not yet use project-local agent assets consistently.

### Legacy Installation (bash)

For manual installation or custom environments:

```bash
curl -fsSL https://raw.githubusercontent.com/cofin/flow/main/tools/install.sh | bash
```

### Initialize a Project

```bash
# Claude Code
/flow-setup

# Gemini CLI / OpenCode
/flow:setup
```

In Codex CLI, ask:
`Use Flow to set up this project`

Flow will:

1. Detect the preferred persistence mode: official Beads (`bd`), `br` compatibility, or no-Beads degraded mode
2. Initialize the selected backend in low-admin mode
3. Default local-only ignores to `.git/info/exclude`
4. Create project context files
5. Guide you through product, tech stack, and workflow setup
6. Create your first flow

### Create a Flow

```bash
# Claude Code
/flow-prd "Add user authentication"

# Gemini CLI / OpenCode
/flow:prd "Add user authentication"
```

In Codex CLI, ask:
`Use Flow to create a PRD for add user authentication`

This creates:

- `spec.md` - Unified specification (requirements AND implementation plan)
- `learnings.md` - Pattern capture log
- `.agents/skills/flow-memory-keeper/SKILL.md` - Project-local sync/archive/learnings/failure-refinement skill
- Beads epic with tasks for cross-session persistence

**Note:** Flow uses a unified spec.md (no separate plan.md). Beads is the source of truth for task status. Use `/flow:sync` to export Beads state to spec.md (MANDATORY after every state change).

### Implement

```bash
# Claude Code
/flow-implement auth

# Gemini CLI / OpenCode
/flow:implement auth
```

In Codex CLI, ask:
`Use Flow to implement auth`

Flow follows TDD workflow with a backend adapter:

1. Detect the active persistence mode (`bd`, `br`, or no-Beads)
2. Select the next task from the active backend, or fall back to spec-driven execution
3. Write failing tests
4. Implement to pass
5. Refactor
6. Verify coverage
7. Commit with conventional format
8. Record completion in the active backend when available
9. Capture learnings
10. Sync to markdown: run `/flow-sync` (MANDATORY when Beads is active)

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers directly to spec.md. Beads is the source of truth. After ANY Beads state change, agents MUST run `/flow-sync` to update spec.md.

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

> **Note**: Claude Code uses `/flow-command` (hyphen). Gemini CLI and OpenCode use `/flow:command` (colon). Codex CLI currently uses the installed Flow skill through plain-language requests instead of plugin-defined slash commands.

## Directory Structure

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

## Flow Naming

Flows use format: `shortname`

Examples:

- `user-auth`
- `dark-mode`
- `api-v2`

## Task Status Markers

| Marker | Status | Description |
|--------|--------|-------------|
| `[ ]` | Pending | Not started |
| `[~]` | In Progress | Currently working |
| `[x]` | Completed | Done with commit SHA |
| `[!]` | Blocked | Cannot proceed (logged in blockers.md) |
| `[-]` | Skipped | Intentionally bypassed (logged in skipped.md) |

## Beads Integration

Flow supports three persistence modes:

- **Official Beads (`bd`)**: preferred default
- **beads_rust (`br`)**: compatibility mode for older repos and command docs
- **No Beads**: degraded mode for docs, planning, and lightweight local work

### Default Initialization

When Flow initializes official Beads, it should default to stealth mode and derive a slugged prefix from the repo name:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
bd init --stealth --prefix "$repo_slug"
```

When Flow initializes `br` compatibility mode, it should also derive the prefix from the repo slug:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
br init --prefix "$repo_slug"
```

### Install Paths

Official Beads (`bd`):

```bash
brew install beads
# or
curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

`beads_rust` compatibility (`br`):

```bash
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```

### Local-Only Ignore Policy

Prefer `.git/info/exclude` for local-only artifacts:

```bash
printf '\n# Flow local-only artifacts\n.beads/\n.agents/\n' >> .git/info/exclude
```

Only update `.gitignore` when the user explicitly wants a shared repo policy.

### Session Protocol

1. **Start**: detect the active backend and load its current workspace state
2. **Work**: Update task status as you progress
3. **Learn**: Add notes for important discoveries
4. **End**: persist backend state when enabled, or rely on `.agents/specs/` + git history in degraded mode

## Knowledge System (Three-Tier)

### Per-Flow Learnings

Each flow has `learnings.md`:

```markdown
## [2026-01-24 14:30] - Phase 1 Task 2: Add auth middleware
- **Files changed:** src/auth/middleware.ts
- **Commit:** abc1234
- **Learning:** Codebase uses Zod for validation
- **Pattern:** Import order: external → internal → types
```

### Project Patterns

Consolidated in `patterns.md`:

```markdown
# Code Conventions
- Import order: external → internal → types

# Gotchas
- Always update barrel exports
```

### Persistent Knowledge Base

Learnings are synthesized into cohesive, logically organized knowledge base chapters in `knowledge/` during sync and archival. Content is integrated directly into existing chapters to describe the current state of the codebase. It is structurally there to provide the implementation details needed to be an expert on the codebase.

### Knowledge Flywheel

1. **Capture** - After each task, append learnings to `learnings.md`
2. **Elevate** - At phase/flow completion, move patterns to `patterns.md`
3. **Synthesize** - During sync and archive, integrate learnings directly into cohesive, logically organized knowledge base chapters in `knowledge/` (e.g., `architecture.md`, `conventions.md`). Do NOT outline history; update the current state.
4. **Inherit** - New flows read `patterns.md` + scan `knowledge/` chapters.

If `.agents/skills/flow-memory-keeper/SKILL.md` exists, use it at sync, archive, finish, revise, and failure checkpoints so spec cleanup, learnings capture, and refinement stay mandatory.

## Skills Library

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

## Documentation

- [CLAUDE.md](CLAUDE.md) - Claude Code context and reference
- [GEMINI.md](GEMINI.md) - Gemini CLI context and reference

## Resources

- [GitHub Issues](https://github.com/cofin/flow/issues) - Report bugs or request features
- [Beads CLI](https://github.com/steveyegge/beads) - Official `bd` task persistence layer
- [beads_rust](https://github.com/Dicklesworthstone/beads_rust) - `br` compatibility backend

## Follow-Up Note

Review the current Beads git hooks and host/LLM integration hooks before finalizing deeper automation. Flow should prefer official Beads or host-native hooks when they already provide the needed sync or lifecycle behavior, and only keep Flow-specific hooks where they add real value instead of duplicating an upstream mechanism.

## License

[Apache License 2.0](LICENSE)
