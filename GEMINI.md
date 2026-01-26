# Flow Context

This file provides guidance to Gemini CLI when working with code in this repository.

## Overview

**Flow** is a unified toolkit for **Context-Driven Development** combining:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Beads Integration**: Dependency-aware task graph, cross-session memory, agent-optimized output

Beads is a **required dependency**. Flow will offer to install it and initializes in **stealth mode** by default.

## Configuration

The root directory for Flow artifacts defaults to `.agent/`. This can be customized during `/flow:setup`.

To find the configured root directory:

1. Check for `.agent/setup-state.json`
2. Read the `root_directory` value from the found file
3. If no file found, use `.agent/` as default

## Universal File Resolution Protocol

**PROTOCOL: How to locate files.**

To find a file (e.g., "**Product Definition**") within a specific context:

1. **Identify Index:** Determine the relevant index file:
    - **Project Context:** `.agent/index.md`
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
| **Product Definition** | `.agent/product.md` |
| **Tech Stack** | `.agent/tech-stack.md` |
| **Workflow** | `.agent/workflow.md` |
| **Product Guidelines** | `.agent/product-guidelines.md` |
| **Flow Registry** | `.agent/flows.md` |
| **Flow Directory** | `.agent/specs/` |
| **Archive Directory** | `.agent/archive/` |
| **Template Directory** | `.agent/templates/` |
| **Code Styleguides Directory** | `.agent/code-styleguides/` |
| **Patterns** | `.agent/patterns.md` |
| **Beads Config** | `.agent/beads.json` |
| **Research Directory** | `.agent/research/` |
| **Wisps Directory** | `.agent/wisps/` |

**Standard Default Paths (Flow):**

| Key | Default Path |
|-----|--------------|
| **Specification** | `.agent/specs/<flow_id>/spec.md` |
| **Implementation Plan** | `.agent/specs/<flow_id>/plan.md` |
| **Metadata** | `.agent/specs/<flow_id>/metadata.json` |
| **Learnings** | `.agent/specs/<flow_id>/learnings.md` |

## Flow ID Naming Convention

**Format:** `shortname_YYYYMMDD` (e.g., `user-auth_20260124`)

- **Active Flows:** Slug + date (e.g., `dark-mode_20260124`)
  - Derived from description: lowercase, hyphens for spaces, max 3-4 words
  - Date suffix prevents collisions and aids chronological sorting
- **Archived Flows:** Keep same ID, moved to `.agent/archive/`

## Task Status Markers

| Marker | Status | Beads Equivalent |
|--------|--------|------------------|
| `[ ]` | Pending | `pending` |
| `[~]` | In Progress | `in_progress` |
| `[x]` | Completed | `completed` |
| `[!]` | Blocked | `blocked` |
| `[-]` | Skipped | `skipped` |

## Commands

| Command | Purpose |
|---------|---------|
| `/flow:setup` | Initialize project with context files, Beads, and first flow |
| `/flow:prd` | **Orchestrator**: Analyze goals and generate Master Roadmap (Sagas) |
| `/flow:plan` | **Planner**: Create Spec and Plan for a single Flow (formerly `prd`) |
| `/flow:research` | Conduct pre-PRD research |
| `/flow:docs` | Five-phase documentation workflow |
| `/flow:implement` | **Executor**: Execute tasks from plan (context-aware) |
| `/flow:status` | Display progress overview with Beads status |
| `/flow:revert` | Git-aware revert of flows, phases, or tasks |
| `/flow:validate` | Validate project integrity and fix issues |
| `/flow:block` | Mark task as blocked with reason |
| `/flow:skip` | Skip current task with justification |
| `/flow:revise` | Update spec/plan when implementation reveals issues |
| `/flow:archive` | Archive completed flows + elevate patterns |
| `/flow:export` | Generate project summary export |
| `/flow:handoff` | Create context handoff for session transfer |
| `/flow:refresh` | Sync context docs with current codebase state |
| `/flow:formula` | List and manage flow templates (Beads formulas) |
| `/flow:wisp` | Create ephemeral exploration flow (no audit trail) |
| `/flow:distill` | Extract reusable template from completed flow |

## Beads Integration

Beads provides persistent cross-session memory. It is **required** for Flow.

### Installation Check

```bash
command -v bd &> /dev/null && echo "BEADS_OK" || echo "BEADS_MISSING"
```

If missing, Flow offers to install:

```bash
npm install -g beads-cli
```

### Initialization (Stealth Mode Default)

```bash
bd init --stealth
```

Stealth mode keeps Beads data local-only (not committed to git).

### Configuration (`.agent/beads.json`)

```json
{
  "enabled": true,
  "mode": "stealth",
  "sync": "bidirectional",
  "epicPrefix": "flow",
  "autoCreateTasks": true,
  "autoSyncOnComplete": true,
  "compactOnArchive": false,
  "taskStatusMapping": {
    "pending": "[ ]",
    "in_progress": "[~]",
    "completed": "[x]",
    "blocked": "[!]",
    "skipped": "[-]"
  }
}
```

### Key Beads Commands

| Flow Action | Beads Command |
|-------------|---------------|
| Create flow | `bd create "Flow: {flow_id}" -t epic -p 1` |
| Create task | `bd create "{task}" --parent {epic_id} -p 1` |
| Start task | `bd update {id} --status in_progress` |
| Complete task | `bd close {id} --reason "commit: {sha}"` |
| Block task | `bd update {id} --status blocked --notes "{reason}"` |
| Get ready tasks | `bd ready` |
| Add notes | `bd update {id} --notes "{learning}"` |
| Sync to git | `bd sync` |
| Prime context | `bd prime` |
| Show blocked | `bd blocked` |

### Session Protocol

At session start:

```bash
bd sync
bd prime
```

At session end:

```bash
bd sync
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

1. Implement → discover patterns
2. Log in flow `learnings.md` (sync to Beads notes)
3. Phase completion → prompt pattern elevation
4. Flow completion → extract to `patterns.md`
5. New flows → pre-load `patterns.md` context

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

State tracked in `parallel_state.json`. Uses Claude's Task Tool to spawn sub-agents.

## Task Workflow (TDD)

1. Select task from plan.md (or `bd ready`)
2. Mark `[~]` in progress → `bd update {id} --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Verify >80% coverage
7. Commit: `<type>(<scope>): <description>`
8. Update plan.md: `[~]` → `[x]` with SHA
9. Sync: `bd close {id} --reason "commit: {sha}"`
10. Log learnings in `learnings.md`

**Important:** All commits stay local. Flow never pushes automatically.

## Phase Checkpoints

At phase completion:

1. Run full test suite
2. Verify coverage requirements
3. Create git tag: `checkpoint/{flow_id}/phase-{N}`
4. Prompt for pattern elevation
5. Manual verification with user

## Skills

Skills are available in `skills/` for copying to `.gemini/skills/`:

| Skill | Purpose |
|-------|---------|
| **flow** | Auto-activates when `.agent/` exists. Workflow guidance. |
| **beads** | Auto-activates when `.beads/` exists. Persistent memory. |
| **50+ tech skills** | React, Rust, Litestar, SQLSpec, testing, etc. |

## Installation

```bash
# Install as Gemini extension
gemini install flow

# Or copy manually
cp -r commands/* ~/.gemini/extensions/flow/commands/
cp -r skills ~/.gemini/skills/

# Install Beads (required)
npm install -g beads-cli
```
