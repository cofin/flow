# Flow Context

This file provides guidance to AI coding agents working with code in this repository.

## Overview

**Flow** is a unified toolkit for **Context-Driven Development** combining:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Beads Integration**: Dependency-aware task graph, cross-session memory, agent-optimized output

Beads is a **required dependency**. Flow will offer to install it and configures it for **local-only mode** by default.

## Auto-Activation

When the `.agents/` directory exists in the project root, the Flow skill MUST be activated at session start. Detect the active Beads backend (`bd`, `br`, or none) and load context before beginning work.

## Agent Conduct

Before planning or implementation, read `.agents/workflow.md` and prefer the repo's canonical commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package scripts, or pre-commit wrappers when they exist.

Be collaborative and constructive. Never use dismissive ownership-deflecting language such as "not my issue" or "not caused by my change." If unrelated blockers appear, describe them factually, offer the smallest helpful next step, and ask the user whether to handle them now or separately.

Make the minimum targeted changes needed for the task. Do not make opportunistic unrelated edits without approval. Do not silently descope or take shortcuts because a request is larger or messier than expected; refine the plan or ask the user how to prioritize.

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
| **Project Skills** | `.agents/skills/` |
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
| `[~]` | In Progress | `in_progress` | Use the active backend's in-progress command |
| `[x]` | Completed | `closed` | Use the active backend's completion command |
| `[!]` | Blocked | `blocked` | Use the active backend's blocking command |
| `[-]` | Skipped | `closed` | Use the active backend's skip/close command |

## Commands

**Host note:** Gemini CLI and OpenCode expose these as `/flow:*`. Claude Code uses `/flow-*`.
Codex currently runs the same workflows through the installed Flow skill and plain-language requests rather than plugin-defined slash commands.

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

Flow supports three persistence modes:

- **Official Beads (`bd`)** - preferred default
- **beads_rust (`br`)** - compatibility mode
- **No Beads** - degraded mode for docs/plans/lightweight local work

Use `choosing-beads-backend` for exact command mapping and migration guidance.

### Installation Check

```bash
if command -v bd >/dev/null 2>&1 && command -v br >/dev/null 2>&1; then
  echo "BEADS_BOTH"
elif command -v bd >/dev/null 2>&1; then
  echo "BD_OK"
elif command -v br >/dev/null 2>&1; then
  echo "BR_OK"
else
  echo "BEADS_MISSING"
fi
```

If `BEADS_BOTH` is found, Flow should offer a choice between `bd` and `br`.
If missing, Flow should offer a concise menu:

- **A) Install official Beads (`bd`)** (recommended)
- **B) Use beads_rust compatibility (`br`)**
- **C) Continue without Beads**

### Initialization

Official default:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
bd init --stealth --prefix "$repo_slug"
```

Compatibility default:

```bash
repo_slug="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//')"
br init --prefix "$repo_slug"
```

For local-only use, prefer `.git/info/exclude` instead of editing `.gitignore`.

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
| Create flow | Use the active backend's flow/epic creation command |
| Add context | Use the active backend's notes/comments command |
| Create task | Use the active backend's task creation command |
| Start task | Use the active backend's in-progress command |
| Complete task | Use the active backend's completion command |
| Block task | Use the active backend's blocking command |
| Get ready tasks | Use the active backend's ready queue |
| Add notes | Use the active backend's notes/comments command |
| Sync to git | Use the active backend's sync/export command if enabled |
| Show blocked | Use the active backend's blocked-view command |

**CRITICAL:** Keep purpose/description separate from context notes/comments:

- `description`: WHY this issue exists and WHAT needs to be done
- notes/comments: CONTEXT - files affected, dependencies, origin command, timestamp
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
- The active Beads backend finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

### Session Protocol

At session start:

```bash
# Official Beads (`bd`)
bd prime
bd ready --json

# beads_rust compatibility (`br`)
br status
br ready
br list --status in_progress
```

At session end:

Use the active backend's sync/export flow. For local-only setups, prefer `.git/info/exclude` over `.gitignore`.

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

Repeated user corrections or visible frustration are high-signal workflow gaps. Capture them in `learnings.md`, elevate them into `.agents/patterns.md`, and refine `.agents/skills/flow-memory-keeper/SKILL.md` when present so the same miss does not have to be corrected again.

Knowledge chapters in `.agents/knowledge/` survive archive cleanup and serve as the expert implementation details for the codebase.

If `.agents/skills/flow-memory-keeper/SKILL.md` exists, invoke it during sync, archive, finish, revise, and failure recovery so learnings, failures, and spec cleanup remain mandatory instead of ad hoc.

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

1. Select task via the active backend's ready/queue command (Beads is source of truth; fall back to spec.md)
2. Mark the task in progress with the active backend's claim/update command
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Verify >80% coverage
7. Commit: `<type>(<scope>): <description>`
8. Record completion in the active backend with the commit reference
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
gemini extensions install https://github.com/cofin/flow --auto-update

# Or copy manually (Run from repo root)
mkdir -p ~/.gemini/extensions/flow
cp -r . ~/.gemini/extensions/flow/

# Or link
gemini extensions link .

# Install official Beads (preferred)
brew install beads
# or
curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Install beads_rust compatibility (optional fallback)
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
```
