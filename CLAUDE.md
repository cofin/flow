# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Flow** is a unified toolkit for **Context-Driven Development** that combines:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Beads Integration**: Dependency-aware task graph, cross-session memory, agent-optimized output

It works with both **Claude Code** (primary) and **Gemini CLI** (primary) with support for **OpenAI Codex** and **OpenCode** (secondary).

## Architecture

### Repository Structure

```
flow/
├── templates/
│   ├── claude/
│   │   └── commands/       # Claude Code commands (18 commands)
│   ├── codex/
│   │   ├── prompts/        # Codex CLI prompts
│   │   └── AGENTS.md       # Codex global instructions
│   ├── opencode/
│   │   ├── commands/       # OpenCode commands
│   │   ├── agents/         # OpenCode agents
│   │   └── opencode.json   # OpenCode config
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
│       ├── learnings.md    # Per-track learnings template
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
| `/flow:setup` | `/flow-setup` | Initialize project with context files, Beads, and first track |
| `/flow:prd` | `/flow-prd` | Create PRD (track) with spec and plan |
| `/flow:research` | `/flow-research` | Conduct pre-PRD research |
| `/flow:docs` | `/flow-docs` | Five-phase documentation workflow |
| `/flow:implement` | `/flow-implement` | Execute tasks from track's plan (TDD workflow) |
| `/flow:status` | `/flow-status` | Display progress overview with Beads status |
| `/flow:revert` | `/flow-revert` | Git-aware revert of tracks, phases, or tasks |
| `/flow:validate` | `/flow-validate` | Validate project integrity and fix issues |
| `/flow:block` | `/flow-block` | Mark task as blocked with reason |
| `/flow:skip` | `/flow-skip` | Skip current task with justification |
| `/flow:revise` | `/flow-revise` | Update spec/plan when implementation reveals issues |
| `/flow:archive` | `/flow-archive` | Archive completed tracks + elevate patterns |
| `/flow:export` | `/flow-export` | Generate project summary export |
| `/flow:handoff` | `/flow-handoff` | Create context handoff for session transfer |
| `/flow:refresh` | `/flow-refresh` | Sync context docs with current codebase state |
| `/flow:formula` | `/flow-formula` | List and manage track templates (Beads formulas) |
| `/flow:wisp` | `/flow-wisp` | Create ephemeral exploration track (no audit trail) |
| `/flow:distill` | `/flow-distill` | Extract reusable template from completed track |

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
│   ├── tracks.md            # Master track list with status
│   ├── patterns.md          # Consolidated learnings (Ralph-style)
│   ├── beads.json           # Beads integration config
│   ├── index.md             # File resolution index
│   ├── setup-state.json     # Resume state for setup
│   ├── refresh_state.json   # Context refresh tracking
│   ├── code-styleguides/    # Language-specific style guides
│   ├── research/            # Research documents
│   ├── wisps/               # Ephemeral exploration tracks
│   ├── templates/           # Project-specific templates
│   ├── archive/             # Archived tracks
│   └── specs/
│       └── <track_id>/
│           ├── metadata.json     # Track config + Beads epic ID
│           ├── spec.md           # Requirements specification
│           ├── plan.md           # Phased task list
│           ├── learnings.md      # Patterns/gotchas discovered
│           ├── implement_state.json # Resume state (if in progress)
│           ├── blockers.md       # Block history log
│           ├── skipped.md        # Skipped tasks log
│           └── revisions.md      # Revision history log
└── .beads/                  # Beads data (created by bd init --stealth)
```

## Key Concepts

### Tracks

A track is a logical unit of work (feature, bug fix, refactor). Each track has:

- **Unique ID format:** `shortname_YYYYMMDD` (e.g., `user-auth_20260124`)
- **Status markers:** `[ ]` pending, `[~]` in progress, `[x]` completed, `[!]` blocked, `[-]` skipped
- **Own directory** with spec, plan, metadata, learnings, and state files

### Task Workflow (TDD)

1. Select task from plan.md (or use `bd ready` for Beads-aware selection)
2. Mark `[~]` in progress → sync to Beads: `bd update <id> --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Verify >80% coverage
7. Commit: `<type>(<scope>): <description>`
8. Update plan.md with commit SHA: `[x]`
9. Sync to Beads: `bd close <id> --reason "commit: <sha>"`
10. **Log learnings** in learnings.md

**Important:** All commits stay local. Flow never pushes automatically.

### Beads Integration (Required)

Beads provides persistent cross-session memory:

- **Stealth mode by default** (local-only, not committed)
- Each track becomes a Beads epic
- Tasks sync for dependency tracking: `bd ready` finds unblocked tasks
- **Notes survive context compaction** - critical for multi-session work
- Graceful degradation if `bd` unavailable

**Key Beads Commands:**

```bash
bd init --stealth                     # Initialize Beads (stealth mode)
bd create "Track: name" -t epic -p 1 \
  --description="Track purpose and goals" \
  --notes="Created by /flow-prd on YYYY-MM-DD"
bd create "Task" --parent <epic> -p 2 \
  --description="What needs to be done and why" \
  --notes="Phase N, Task M. Files: affected_files"
bd ready                              # Show tasks ready to work on
bd update <id> --status in_progress   # Start task
bd close <id> --reason "commit: sha"  # Complete task with commit reference
bd blocked                            # Show blocked tasks
bd sync                               # Sync with git
bd prime                              # Load context for session
```

**CRITICAL: Always include `--description` and `--notes` with `bd create`:**

- `--description`: WHY this issue exists and WHAT needs to be done
- `--notes`: CONTEXT - files affected, dependencies, origin command, timestamp
- Priority levels: P0=critical, P1=high, P2=medium, P3=low, P4=backlog

### When to Track in Beads

**Rule: If work takes >5 minutes, track it in Beads.**

| Duration | Action | Example |
|----------|--------|---------|
| <5 min | Just do it | Fix typo, update config |
| 5-30 min | Create task | Add validation, write test |
| 30+ min | Create task with subtasks | Implement feature |

**Why this matters:**

- Notes survive context compaction - critical for multi-session work
- `bd ready` finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

### Learnings System (Ralph-style Knowledge Flywheel)

**Per-Track (`learnings.md`):**

- Append-only log of discoveries during implementation
- Format: `[timestamp] - Phase/Task - Learning`
- Sections: Session Log, Patterns Discovered, Gotchas, Decisions Made

**Project-Level (`patterns.md`):**

- Consolidated patterns elevated from completed tracks
- Categories: Code Conventions, Architecture, Gotchas, Testing, Context
- **Read before starting work** to prime context

**Knowledge Flywheel:**

1. Implement → discover patterns
2. Log in track `learnings.md` (auto-sync to Beads notes)
3. At phase/track completion → prompt for pattern elevation
4. Archive track → extract remaining patterns to `patterns.md`
5. New flows → inherit patterns from `patterns.md`

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
- Create git tag: `checkpoint/{track_id}/phase-{N}`
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
- **Interoperability:** Both Claude Code and Gemini CLI use the same `.agent/` directory

## Installation

### Intelligent Installer (Recommended)

```bash
./scripts/install.sh
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
cp -r templates/codex/prompts/* ~/.codex/prompts/
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
gemini install flow
# Or: cp -r commands/* ~/.gemini/extensions/flow/commands/
```

#### Beads (Required)

```bash
npm install -g beads-cli
bd init --stealth
```

## Related Documentation

- [README.md](README.md) - Project overview and quick start
- [GEMINI.md](GEMINI.md) - Gemini CLI context and configuration
