# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Flow** is a unified toolkit for **Context-Driven Development** that combines:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Beads Integration**: Dependency-aware task graph, cross-session memory, agent-optimized output

It works with **Claude Code** (primary), **Gemini CLI** (primary), and **Google Antigravity** (primary) with support for **OpenAI Codex** and **OpenCode** (secondary).

## Architecture

### Repository Structure

```
flow/
├── templates/
│   ├── claude/
│   │   └── commands/       # Claude Code commands (20 commands)
│   ├── codex/
│   │   ├── skills/         # Codex Agent Skills (flow-*/SKILL.md)
│   │   └── AGENTS.md       # Codex global instructions
│   ├── opencode/
│   │   ├── commands/       # OpenCode commands
│   │   ├── agents/         # OpenCode agents
│   │   └── opencode.json   # OpenCode config
│   ├── antigravity/
│   │   └── skills/         # Antigravity Workflow Skills (flow-*/SKILL.md)
│   ├── skills/             # Consolidated skills library (50+ skills)
│   │   ├── flow/           # Flow workflow skill
│   │   ├── beads/          # Beads integration skill
│   │   └── ...             # Technology-specific skills
│   ├── styleguides/        # Code style guides
│   │   ├── languages/      # Python, TypeScript, Rust, etc.
│   │   ├── frameworks/     # React, Litestar, etc.
│   │   └── databases/      # PostgreSQL, MongoDB, etc.
│   └── agent/              # Templates for user .agent/ directory
│       ├── beads.json      # Beads config template
│       ├── patterns.md     # Project patterns template
│       ├── learnings.md    # Per-flow learnings template
│       └── workflow.md     # Workflow template
├── commands/flow/          # Gemini commands
├── scripts/
│   └── install.sh          # Intelligent multi-CLI installer
├── ref/                    # Reference implementations
├── CLAUDE.md               # This file
├── GEMINI.md               # Gemini CLI context
└── README.md               # Project documentation
```

### Commands

| Gemini CLI | Claude Code | Purpose |
|------------|-------------|---------|
| `/flow:setup` | `/flow-setup` | Initialize project with context files, Beads, and first flow |
| `/flow:prd` | `/flow-prd` | Create PRD (flow) with unified spec |
| `/flow:plan` | `/flow-plan` | Plan single flow with unified spec.md |
| `/flow:sync` | `/flow-sync` | Export Beads state to spec.md |
| `/flow:research` | `/flow-research` | Conduct pre-PRD research |
| `/flow:docs` | `/flow-docs` | Five-phase documentation workflow |
| `/flow:implement` | `/flow-implement` | Execute tasks from flow's spec (TDD workflow) |
| `/flow:status` | `/flow-status` | Display progress overview with Beads status |
| `/flow:revert` | `/flow-revert` | Git-aware revert of flows, phases, or tasks |
| `/flow:validate` | `/flow-validate` | Validate project integrity and fix issues |
| `/flow:block` | `/flow-block` | Mark task as blocked with reason |
| `/flow:skip` | `/flow-skip` | Skip current task with justification |
| `/flow:revise` | `/flow-revise` | Update spec/plan when implementation reveals issues |
| `/flow:archive` | `/flow-archive` | Archive completed flows + elevate patterns |
| `/flow:export` | `/flow-export` | Generate project summary export |
| `/flow:handoff` | `/flow-handoff` | Create context handoff for session transfer |
| `/flow:refresh` | `/flow-refresh` | Sync context docs with current codebase state |
| `/flow:formula` | `/flow-formula` | List and manage flow templates |
| `/flow:wisp` | `/flow-wisp` | Create ephemeral exploration flow (no audit trail) |
| `/flow:distill` | `/flow-distill` | Extract reusable template from completed flow |

### Skills

| Skill | Location | Purpose |
|-------|----------|---------|
| **flow** | `skills/flow/` | Auto-activates when `.agent/` exists. Provides intent mapping and workflow guidance. |
| **beads** | `skills/beads/` | Auto-activates when `.beads/` exists. Provides persistent memory across sessions. |
| **50+ tech skills** | `skills/*/` | Technology-specific skills (React, Rust, Litestar, SQLSpec, etc.) |

### Generated Artifacts (in user projects)

When users run Flow, it creates:

```
project/
├── .agent/
│   ├── product.md           # Product vision and goals
│   ├── product-guidelines.md # Brand/style guidelines
│   ├── tech-stack.md        # Technology choices
│   ├── workflow.md          # Development workflow (TDD, commits)
│   ├── flows.md             # Master flow list with status
│   ├── patterns.md          # Consolidated learnings (Ralph-style)
│   ├── beads.json           # Beads integration config
│   ├── index.md             # File resolution index
│   ├── setup-state.json     # Resume state for setup
│   ├── refresh_state.json   # Context refresh tracking
│   ├── code-styleguides/    # Language-specific style guides
│   ├── research/            # Research documents
│   ├── wisps/               # Ephemeral exploration flows
│   ├── templates/           # Project-specific templates
│   ├── knowledge/              # Persistent knowledge base
│   │   ├── index.md            # Quick reference index
│   │   └── {flow_id}.md        # Per-flow detailed learnings
│   ├── archive/             # Archived flows
│   └── specs/
│       └── <flow_id>/
│           ├── metadata.json     # Flow config + Beads epic ID
│           ├── spec.md           # Unified spec + plan (requirements AND tasks)
│           ├── learnings.md      # Patterns/gotchas discovered
│           ├── implement_state.json # Resume state (if in progress)
│           ├── blockers.md       # Block history log
│           ├── skipped.md        # Skipped tasks log
│           └── revisions.md      # Revision history log
└── .beads/                  # Beads data (created by br init)
```

## Key Concepts

### Flows

A flow is a logical unit of work (feature, bug fix, refactor). Each flow has:

- **Unique ID format:** `shortname_YYYYMMDD` (e.g., `user-auth_20260124`)
- **Status markers:** `[ ]` pending, `[~]` in progress, `[x]` completed, `[!]` blocked, `[-]` skipped
- **Own directory** with spec, metadata, learnings, and state files

### Task Workflow (TDD)

1. Select task via `br ready` (Beads is source of truth; fall back to spec.md)
2. Mark in Beads: `br update <id> --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Verify >80% coverage
7. Commit: `<type>(<scope>): <description>`
8. Sync to Beads: `br close <id> --reason "commit: <sha>"`
9. **Log learnings** in learnings.md
10. **Sync to markdown:** run `/flow-sync` (MANDATORY — keeps spec.md readable)

**CRITICAL:** After ANY Beads state change (close, block, skip, revert, revise), agents MUST run `/flow-sync` to update spec.md. Never write markers (`[x]`, `[~]`, `[!]`, `[-]`) directly to spec.md.

**Important:** All commits stay local. Flow never pushes automatically.

### Beads Integration (Required)

**Note:** `br` is non-invasive and never executes git commands. After `br sync --flush-only`, you must manually run `git add .beads/ && git commit`.

Beads provides persistent cross-session memory:

- **Local-only by default** (`.beads/` added to `.gitignore`)
- Each flow becomes a Beads epic
- Tasks sync for dependency tracking: `br ready` finds unblocked tasks
- **Notes survive context compaction** - critical for multi-session work
- Graceful degradation if `br` unavailable

**Key Beads Commands:**

```bash
br init                               # Initialize Beads
br create "Flow: name" -t epic -p 1 \
  --description="Flow purpose and goals"
# Then add context notes (br create does NOT support --notes):
br update <id> --notes "Created by /flow-prd on YYYY-MM-DD"

br create "Task" --parent <epic> -p 2 \
  --description="What needs to be done and why"
br update <id> --notes "Phase N, Task M. Files: affected_files"

br status                             # Workspace overview
br ready                              # Show tasks ready to work on
br update <id> --status in_progress   # Start task
br close <id> --reason "commit: sha"  # Complete task with commit reference
br blocked                            # Show blocked tasks
br sync --flush-only                  # Sync with git
git add .beads/
git commit -m "sync beads"
```

**CRITICAL: `br create` supports `--description` but NOT `--notes`:**

- `--description`: WHY this issue exists and WHAT needs to be done (at creation)
- `--notes`: CONTEXT via `br update` — files affected, dependencies, origin command, timestamp
- Priority levels: P0=critical, P1=high, P2=medium, P3=low, P4=backlog

**beads-rust valid statuses:** `open`, `in_progress`, `blocked`, `deferred`, `closed`, `tombstone`, `pinned`

### When to Track in Beads

**Rule: If work takes >5 minutes, track it in Beads.**

| Duration | Action | Example |
|----------|--------|---------|
| <5 min | Just do it | Fix typo, update config |
| 5-30 min | Create task | Add validation, write test |
| 30+ min | Create task with subtasks | Implement feature |

**Why this matters:**

- Notes survive context compaction - critical for multi-session work
- `br ready` finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

### Learnings System (Three-Tier Knowledge)

| Tier | File | Loaded | Purpose |
|------|------|--------|---------|
| **Patterns** | `.agent/patterns.md` | Always | Elevated actionable rules for priming |
| **Knowledge Index** | `.agent/knowledge/index.md` | Always | Lightweight scan of all flow learnings |
| **Knowledge Entries** | `.agent/knowledge/{flow_id}.md` | On demand | Full detailed learnings per flow |

**Per-Flow (`learnings.md`):**

- Append-only log of discoveries during implementation
- Format: `[timestamp] - Phase/Task - Learning`
- Sections: Session Log, Patterns Discovered, Gotchas, Decisions Made

**Project-Level (`patterns.md`):**

- Consolidated patterns elevated from completed flows
- Categories: Code Conventions, Architecture, Gotchas, Testing, Context
- **Read before starting work** to prime context

**Persistent Knowledge Base (`knowledge/`):**

- Full verbatim learnings persisted independently of archives
- Survives archive cleanup — detailed learnings never lost
- Index provides lightweight topic-based lookup

**Knowledge Flywheel:**

1. **Capture** - After each task, append learnings to flow's `learnings.md`
2. **Elevate** - At phase/flow completion, move reusable patterns to `.agent/patterns.md`
3. **Extract** - At archive, persist full learnings to `knowledge/{flow_id}.md`
4. **Inherit** - New flows read `patterns.md` + scan `knowledge/index.md`

### Parallel Execution

Phases can execute tasks in parallel using sub-agents:

- Annotate phases: `<!-- execution: parallel -->`
- Task file ownership: `<!-- files: src/file.ts -->`
- Dependencies: `<!-- depends: task1 -->`
- State tracked in `parallel_state.json`

### Phase Checkpoints

At phase completion:

- Run full test suite
- Verify coverage requirements
- Ensure phase completion is committed
- Prompt for pattern elevation
- Manual verification with user

## Development Notes

- **Claude Code commands:** Markdown files in `templates/claude/commands/`
- **Gemini CLI commands:** TOML files in `commands/flow/`
- **Skills:** Use SKILL.md format with auto-activation patterns
- **Styleguides:** Code style guides in `templates/styleguides/`
- **Agent templates:** User project templates in `templates/agent/`
- **State tracking:** JSON files (setup-state.json, implement_state.json, metadata.json)
- **Audit trail:** Git notes for commit metadata
- **Antigravity skills:** SKILL.md files in `templates/antigravity/skills/`
- **Interoperability:** All CLIs use the same `.agent/` directory

## Installation

### Intelligent Installer (Recommended)

```bash
./tools/scripts/install.sh
```

The installer detects installed CLIs, backs up existing configs, and merges intelligently.

### Manual Installation

#### Claude Code

```bash
cp -r templates/claude/commands/* ~/.claude/commands/
cp -r skills/* ~/.claude/skills/
```

#### Codex CLI

```bash
cp -r templates/codex/skills/* ~/.codex/skills/
cat templates/codex/AGENTS.md >> ~/.codex/AGENTS.md
cp -r skills/flow ~/.codex/skills/
cp -r skills/beads ~/.codex/skills/
```

#### OpenCode

```bash
cp -r templates/opencode/commands/* ~/.config/opencode/commands/
cp -r templates/opencode/agents/* ~/.config/opencode/agents/
```

#### Gemini CLI

```bash
gemini extensions install flow
# Or: cp -r commands/* ~/.gemini/extensions/flow/commands/
```

#### Antigravity

```bash
cp -r templates/antigravity/skills/* ~/.gemini/antigravity/skills/
cp -r skills/* ~/.gemini/antigravity/skills/
```

#### Beads (Required)

```bash
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
br init
```

## Related Documentation

- [README.md](README.md) - Project overview and quick start
- [GEMINI.md](GEMINI.md) - Gemini CLI context and configuration
