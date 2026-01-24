# Flow

**Measure twice, code once.**

Flow is a unified toolkit for **Context-Driven Development** that works with both **Claude Code** and **Gemini CLI**. It combines spec-first planning with **Beads** for persistent cross-session memory, enabling AI-assisted development with deep, persistent project awareness.

## Philosophy

Control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction. Flow ensures a consistent, high-quality lifecycle for every task:

**Context → Spec & Plan → Implement → Learn**

## Key Features

- **Beads Integration**: Persistent task memory that survives context compaction
- **Multi-CLI Support**: Works with Claude Code (primary) and Gemini CLI (primary)
- **Spec-First Development**: Create specs and plans before writing code
- **TDD Workflow**: Red-Green-Refactor with >80% coverage requirements
- **Knowledge Flywheel**: Capture and elevate patterns across tracks (Ralph-style)
- **Track Management**: Block, skip, revise, archive with full audit trail
- **Git-Aware Revert**: Understands logical units of work, not just commits
- **Parallel Execution**: Phase-level task parallelism via sub-agents

## Quick Start

### Installation

#### Beads (Required)

```bash
npm install -g beads-cli
```

#### Claude Code

```bash
# Copy commands to your project or global config
cp -r templates/claude/commands/* ~/.claude/commands/

# Copy skills (optional - for auto-activation)
cp -r templates/skills/* ~/.claude/skills/
```

#### Gemini CLI

```bash
# Install as extension
gemini extensions install https://github.com/cofin/flow --auto-update

# Or copy manually
cp -r templates/gemini/commands/* ~/.gemini/extensions/flow/commands/
```

### Initialize a Project

```bash
# In Claude Code
/flow-setup

# In Gemini CLI
/flow:setup
```

Flow will:
1. Check/install Beads
2. Initialize Beads in stealth mode
3. Create project context files
4. Guide you through product, tech stack, and workflow setup
5. Create your first track

### Create a PRD (Track)

```bash
# Claude Code
/flow-prd "Add user authentication"

# Gemini CLI
/flow:prd "Add user authentication"
```

This creates:
- `spec.md` - Requirements specification
- `plan.md` - Phased implementation plan
- `learnings.md` - Pattern capture log
- Beads epic with tasks for cross-session persistence

### Implement

```bash
# Claude Code
/flow-implement auth_20260124

# Gemini CLI
/flow:implement auth_20260124
```

Flow follows TDD workflow:
1. Select task (or use `bd ready` for Beads-aware selection)
2. Write failing tests
3. Implement to pass
4. Refactor
5. Verify coverage
6. Commit with conventional format
7. Sync to Beads
8. Capture learnings

## Commands

| Purpose | Claude Code | Gemini CLI |
|---------|-------------|------------|
| Initialize project | `/flow-setup` | `/flow:setup` |
| Create PRD (track) | `/flow-prd` | `/flow:prd` |
| Pre-PRD research | `/flow-research` | `/flow:research` |
| Documentation workflow | `/flow-docs` | `/flow:docs` |
| Implement tasks | `/flow-implement` | `/flow:implement` |
| Check status | `/flow-status` | `/flow:status` |
| Revert changes | `/flow-revert` | `/flow:revert` |
| Validate integrity | `/flow-validate` | `/flow:validate` |
| Block task | `/flow-block` | `/flow:block` |
| Skip task | `/flow-skip` | `/flow:skip` |
| Revise spec/plan | `/flow-revise` | `/flow:revise` |
| Archive track | `/flow-archive` | `/flow:archive` |
| Export summary | `/flow-export` | `/flow:export` |
| Session handoff | `/flow-handoff` | `/flow:handoff` |
| Sync context | `/flow-refresh` | `/flow:refresh` |
| Manage templates | `/flow-formula` | `/flow:formula` |
| Ephemeral track | `/flow-wisp` | `/flow:wisp` |
| Extract template | `/flow-distill` | `/flow:distill` |

## Directory Structure

```
project/
├── .agent/
│   ├── product.md           # Product vision and goals
│   ├── product-guidelines.md # Brand/style guidelines
│   ├── tech-stack.md        # Technology choices
│   ├── workflow.md          # Development workflow (TDD, commits)
│   ├── tracks.md            # Track registry with status
│   ├── patterns.md          # Consolidated learnings
│   ├── beads.json           # Beads configuration
│   ├── index.md             # File resolution index
│   ├── code-styleguides/    # Language style guides
│   ├── specs/
│   │   └── <track_id>/      # e.g., user-auth_20260124/
│   │       ├── spec.md
│   │       ├── plan.md
│   │       ├── learnings.md
│   │       └── metadata.json
│   └── archive/             # Completed tracks
└── .beads/                  # Beads data (stealth mode)
```

## Track Naming

Tracks use format: `shortname_YYYYMMDD`

Examples:
- `user-auth_20260124`
- `dark-mode_20260124`
- `api-v2_20260124`

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
bd sync
bd prime

# During work
bd ready              # Show unblocked tasks
bd update <id> --status in_progress
bd close <id> --note "commit: abc123"

# At session end
bd sync
# Notes survive context compaction!
```

### Session Protocol

1. **Start**: `bd sync && bd prime` loads context
2. **Work**: Update task status as you progress
3. **Learn**: Add notes for important discoveries
4. **End**: `bd sync` persists everything

## Knowledge System (Ralph-style)

### Per-Track Learnings

Each track has `learnings.md`:

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

### Knowledge Flywheel

1. Implement → discover patterns
2. Log in `learnings.md`
3. Phase completion → prompt for elevation
4. Archive → extract to `patterns.md`
5. New tracks → inherit patterns

## Skills Library

Flow includes 50+ technology-specific skills in `templates/skills/`:

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
