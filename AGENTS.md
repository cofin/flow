# Flow Context

This file provides guidance to AI coding agents working with code in this repository.

## Overview

**Flow** is a unified toolkit for **Context-Driven Development** combining:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Beads Integration**: Dependency-aware task graph, cross-session memory, agent-optimized output

Beads is a **required dependency**. Flow will offer to install it and configures it for **local-only mode** by default.

## Auto-Activation

When the `.agents/` directory exists in the project root, the Flow skill MUST be activated at session start. Run `br status` and `br ready` to load context before beginning work.

## Configuration

The root directory for Flow artifacts defaults to `.agents/`. This can be customized during `/flow:setup`.

To find the configured root directory:

1. Check for `.agents/setup-state.json`
2. Read the `root_directory` value from the found file
3. If no file found, use `.agents/` as default

## Spec & Design Documents

All spec and design documents (including those created by superpowers brainstorming) MUST be written to the Flow spec directory:
- Default: `.agents/specs/<flow_id>/`
- Check `.agents/setup-state.json` for custom `root_directory`
- Do NOT use `docs/superpowers/specs/` — Flow manages all specs in `.agents/`

## Universal File Resolution Protocol

**PROTOCOL: How to locate files.**

To find a file (e.g., "**Product Definition**") within a specific context:

1. **Identify Index:** Determine the relevant index file:
    - **Project Context:** `.agents/index.md`
    - **Flow Context:**
        a. Resolve and read the **Flow Registry** (via Project Context)
        b. Find the entry for the specific `<flow_id>`
        c. Follow the link to locate the flow's folder. Index file is `<flow_folder>/index.md`
        d. **Fallback:** If not yet registered, use `<Flow Directory>/<flow_id>/index.md`

2. **Check Index:** Read the index file and look for a link with a matching label.

3. **Resolve Path:** Resolve path **relative to the directory containing the `index.md` file**.

4. **Fallback:** If index missing, use **Default Path** keys below.

5. **Verify:** Confirm the resolved file exists on disk.

**Standard Default Paths (Project):**

| Key | Default Path |
|-----|--------------|
| **Product Definition** | `.agents/product.md` |
| **Tech Stack** | `.agents/tech-stack.md` |
| **Workflow** | `.agents/workflow.md` |
| **Product Guidelines** | `.agents/product-guidelines.md` |
| **Flow Registry** | `.agents/flows.md` |
| **Flow Directory** | `.agents/specs/` |
| **Archive Directory** | `.agents/archive/` |
| **Template Directory** | `.agents/templates/` |
| **Code Styleguides Directory** | `.agents/code-styleguides/` |
| **Patterns** | `.agents/patterns.md` |
| **Knowledge Base** | `.agents/knowledge/` |
| **Knowledge Index** | `.agents/knowledge/index.md` |
| **Beads Config** | `.agents/beads.json` |
| **Research Directory** | `.agents/research/` |
| **Task Directory** | `.agents/tasks/` |

**Standard Default Paths (Flow):**

| Key | Default Path |
|-----|--------------|
| **Specification** | `.agents/specs/<flow_id>/spec.md` (unified spec + plan) |
| **Metadata** | `.agents/specs/<flow_id>/metadata.json` |
| **Learnings** | `.agents/specs/<flow_id>/learnings.md` |

## Flow ID Naming Convention

**Format:** `shortname` (e.g., `user-auth`)

- **Active Flows:** Simple slug (e.g., `dark-mode`)
  - Derived from description: lowercase, hyphens for spaces, max 3-4 words
- **Archived Flows:** Keep same ID, moved to `.agents/archive/`

## Task Status Markers

| Marker | Status | Beads Status | Beads Command |
|--------|--------|-------------|---------------|
| `[ ]` | Pending | `open` | (default) |
| `[~]` | In Progress | `in_progress` | `br update {id} --status in_progress` |
| `[x]` | Completed | `closed` | `br close {id} --reason "commit: {sha}"` |
| `[!]` | Blocked | `blocked` | `br update {id} --status blocked --notes "BLOCKED: {reason}"` |
| `[-]` | Skipped | `closed` | `br close {id} --reason "Skipped: {reason}"` |

## Commands

| Command | Purpose |
|---------|---------|
| `/flow:setup` | Initialize project with context files, Beads, and first flow |
| `/flow:prd` | **Orchestrator**: Analyze goals and generate Master Roadmap (Sagas) |
| `/flow:plan` | **Planner**: Create unified spec.md for a single Flow |
| `/flow:sync` | **Syncer**: Synchronize context docs, Beads state, and export summaries |
| `/flow:research` | Conduct pre-PRD research |
| `/flow:docs` | Five-phase documentation workflow |
| `/flow:implement` | **Executor**: Execute tasks from plan (context-aware) |
| `/flow:status` | Display progress overview with Beads status |
| `/flow:revert` | Git-aware revert of flows, phases, or tasks |
| `/flow:validate` | Validate project integrity and fix issues |
| `/flow:revise` | Update spec/plan when implementation reveals issues |
| `/flow:archive` | Archive completed flows + elevate patterns |
| `/flow:refresh` | **Refresher**: Sync context with codebase after external changes |
| `/flow:task` | Create ephemeral exploration task |
| `/flow:finish` | Complete flow: verify, review, merge/PR/keep/discard |
| `/flow:review` | Dispatch code review with Beads-aware git range |

## Beads Integration

**Note:** `br` is non-invasive and never executes git commands. After `br sync --flush-only`, you must manually run `git add .beads/ && git commit`.

Beads provides persistent cross-session memory. It is **required** for Flow.

### Installation Check

```bash
command -v br &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
```

If missing, Flow offers to install:

```bash
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```

### Initialization

```bash
br init
```

For local-only use, add `.beads/` to `.gitignore` after initialization.

### Configuration (`.agents/beads.json`)

```json
{
  "enabled": true,
  "sync": "bidirectional",
  "epicPrefix": "flow",
  "autoCreateTasks": true,
  "autoSyncOnComplete": true,
  "taskStatusMapping": {
    "open": "[ ]",
    "in_progress": "[~]",
    "closed": "[x]",
    "blocked": "[!]"
  }
}
```

### Key Beads Commands

| Flow Action | Beads Command |
|-------------|---------------|
| Create flow | `br create "Flow: {flow_id}" -t epic -p 1 --description="{purpose}"` |
| Add context | `br update {id} --notes "{context}"` |
| Create task | `br create "{task}" --parent {epic_id} -p 2 --description="{what_and_why}"` |
| Start task | `br update {id} --status in_progress` |
| Complete task | `br close {id} --reason "commit: {sha}"` |
| Block task | `br update {id} --status blocked --notes "BLOCKED: {reason}"` |
| Get ready tasks | `br ready` |
| Add notes | `br update {id} --notes "{learning}"` |
| Sync to git | `br sync --flush-only` |
| Show blocked | `br blocked` |

**CRITICAL: `br create` supports `--description` but NOT `--notes`.** Use `br update` to add notes after creation:

- `--description`: WHY this issue exists and WHAT needs to be done (set at creation)
- `--notes`: CONTEXT - files affected, dependencies, origin command, timestamp (set via `br update`)
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
- `br ready` finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

### Session Protocol

At session start:

```bash
br status                          # Workspace overview
br ready                           # List unblocked tasks
br list --status in_progress       # Resume active work
```

At session end:

```bash
br sync --flush-only
git add .beads/
# You can commit beads state manually or alongside your features
# Notes survive context compaction!
```

## Learnings System (Ralph-style)

### Per-Flow (`learnings.md`)

Append-only log of discoveries:

```markdown
## [2026-01-24 14:30] - Phase 1 Task 2: Add auth middleware
- **Files changed:** src/auth/middleware.ts
- **Commit:** abc1234
- **Learning:** Codebase uses Zod for all validation
- **Pattern:** Import order: external → internal → types
- **Gotcha:** Must update index.ts barrel exports
```

### Project-Level (`patterns.md`)

Consolidated patterns from all flows:

```markdown
# Code Conventions
- Import order: external → internal → types
- Use barrel exports in index.ts

# Architecture
- Validation with Zod schemas
- Repository pattern for data access

# Gotchas
- Always update barrel exports
- Run `npm run typecheck` before commit
```

### Knowledge Flywheel

1. **Capture** - After each task, append learnings to flow's `learnings.md`
2. **Elevate** - At phase/flow completion, move reusable patterns to `.agents/patterns.md`
3. **Synthesize** - During sync and archive, integrate learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`). Update the current state, do NOT outline history.
4. **Inherit** - New flows read `patterns.md` + scan `.agents/knowledge/` chapters.

Knowledge chapters in `.agents/knowledge/` survive archive cleanup and serve as the expert implementation details for the codebase.

## Parallel Execution

Phases can annotate parallel execution:

```markdown
## Phase 2: Core Implementation
<!-- execution: parallel -->

- [ ] Task 3: Create auth module
  <!-- files: src/auth/index.ts, src/auth/index.test.ts -->

- [ ] Task 4: Create config module
  <!-- files: src/config/index.ts -->
  <!-- depends: task3 -->
```

State tracked in `parallel_state.json`. Uses the `invoke_subagent` tool to spawn sub-agents.

## Task Workflow (TDD)

1. Select task via `br ready` (Beads is source of truth; fall back to spec.md)
2. Mark in Beads: `br update {id} --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Verify >80% coverage
7. Commit: `<type>(<scope>): <description>`
8. Sync to Beads: `br close {id} --reason "commit: {sha}"`
9. Log learnings in `learnings.md`
10. **Sync to markdown:** run `/flow:sync` (MANDATORY — keeps spec.md readable)

**CRITICAL:** After ANY Beads state change (close, block, skip, revert, revise), agents MUST run `/flow:sync` to update spec.md. Never write markers (`[x]`, `[~]`, `[!]`, `[-]`) directly to spec.md.

**Important:** All commits stay local. Flow never pushes automatically.

## Phase Checkpoints

At phase completion:

1. Run full test suite
2. Verify coverage requirements
3. Ensure phase completion is committed
4. Prompt for pattern elevation
5. Manual verification with user

## Skills

Skills are available in `skills/` for copying to `.gemini/skills/`:

| Skill | Purpose |
|-------|---------|
| **flow** | Auto-activates when `.agents/` exists. Workflow guidance. |
| **50+ tech skills** | React, Rust, Litestar, SQLSpec, testing, etc. |

## Installation

```bash
# Install as Gemini extension
gemini extensions install https://github.com/cofin/flow

# Or copy manually (Run from repo root)
mkdir -p ~/.gemini/extensions/flow
cp -r . ~/.gemini/extensions/flow/

# Or link
gemini extensions link .

# Install Beads (required)
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```
