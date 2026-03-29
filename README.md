# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Context-Driven Development** that works with **Claude Code**, **Gemini CLI**, **Codex CLI**, **OpenCode**, and **Google Antigravity**. It combines spec-first planning with **Beads** for persistent cross-session memory, enabling AI-assisted development with deep, persistent project awareness.

## Philosophy

Control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction. Flow ensures a consistent, high-quality lifecycle for every task:

**Context → Spec & Plan → Implement → Learn**

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
- **Google Antigravity** (`~/.gemini/antigravity/skills/`)

**Note:** Gemini CLI now uses native extension installation: `gemini extensions install flow`

## Installation

Flow can be installed as a native plugin or extension on supported AI CLI platforms.

### Gemini CLI

```bash
gemini extensions install https://github.com/cofin/flow
```

To update:
```bash
gemini extensions update flow
```

### Claude Code

Install Flow from its plugin marketplace:

```bash
/plugin marketplace add cofin/flow-marketplace
/plugin install flow@flow-marketplace
```

Or directly from GitHub:
```bash
/plugin install flow@git+https://github.com/cofin/flow.git
```

### OpenCode

Add Flow to your global or project-level `opencode.json`:

```json
{
  "plugin": ["flow@git+https://github.com/cofin/flow.git"]
}
```

Restart OpenCode to auto-register all skills and commands.

### Cursor IDE

Install Flow from the plugin system:
```
/add-plugin flow
```

Or add to your `.cursor-plugin` configuration manually.

### Codex CLI

Install Flow as a Codex plugin:

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

### Legacy Installation (bash)

For manual installation or custom environments:

```bash
curl -fsSL https://raw.githubusercontent.com/cofin/flow/main/tools/install.sh | bash
```

### Initialize a Project

```bash
# Claude Code
/flow-setup

# Gemini CLI / Codex CLI / OpenCode
/flow:setup
```

Flow will:

1. Check/install Beads
2. Initialize Beads
3. Create project context files
4. Guide you through product, tech stack, and workflow setup
5. Create your first flow

### Create a Flow

```bash
# Claude Code
/flow-prd "Add user authentication"

# Gemini CLI
/flow:prd "Add user authentication"
```

This creates:

- `spec.md` - Unified specification (requirements AND implementation plan)
- `learnings.md` - Pattern capture log
- Beads epic with tasks for cross-session persistence

**Note:** Flow uses a unified spec.md (no separate plan.md). Beads is the source of truth for task status. Use `/flow:sync` to export Beads state to spec.md (MANDATORY after every state change).

### Implement

```bash
# Claude Code
/flow-implement auth

# Gemini CLI
/flow:implement auth
```

Flow follows TDD workflow (Beads-first):

1. Select task from `br ready` (Beads is source of truth)
2. Mark in progress: `br update <id> --status in_progress`
3. Write failing tests
4. Implement to pass
5. Refactor
6. Verify coverage
7. Commit with conventional format
8. Sync to Beads: `br close <id> --reason "commit: <sha>"`
9. Capture learnings
10. Sync to markdown: run `/flow-sync` (MANDATORY)

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers directly to spec.md. Beads is the source of truth. After ANY Beads state change, agents MUST run `/flow-sync` to update spec.md.

## Commands

| Purpose | Claude Code | Others |
|---------|-------------|--------|
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

> **Note**: Claude Code uses `/flow-command` (hyphen); Gemini CLI, OpenCode, and Codex CLI use `/flow:command` (colon).

## Directory Structure

```
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

Beads provides persistent memory across sessions:

```bash
# At session start
br status                          # Workspace overview
br ready                           # List unblocked tasks
br list --status in_progress       # Resume active work

# During work
br ready              # Show unblocked tasks
br update <id> --status in_progress
br close <id> --reason "commit: abc123"

# At session end
br sync --flush-only
git add .beads/
# You can commit beads state manually or alongside your features
# Notes survive context compaction!
```

### Session Protocol

1. **Start**: `br status` + `br ready` to load context and find unblocked tasks
2. **Work**: Update task status as you progress
3. **Learn**: Add notes for important discoveries
4. **End**: `br sync --flush-only && git add .beads/` persists everything

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
- [Beads CLI](https://github.com/withzombies/beads) - Task persistence layer

## License

[Apache License 2.0](LICENSE)
