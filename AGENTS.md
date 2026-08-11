# Flow Context

This file provides guidance to AI coding agents working with code in this repository.

> **Flow is a skill, not a CLI.** There is no `flow` executable. Never run `flow`, `flow sync`, `flow prd`, `flow status`, etc. as shell commands — they will fail. Invoke the Flow skill, or use the `/flow:*` slash commands (e.g. `/flow:sync`, `/flow:prd`).

## Overview

**Flow** is a unified toolkit for **Context-Driven Development** combining:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Task-Centric Filesystem Engine (OKF)**: Local specifications (`spec.md`) and task files (`tasks/*.md`) with YAML frontmatter.

## The Task-First Mandate

**CRITICAL:** Every task, discovery, and decision MUST be recorded in the local specification folder.

- **Flow Specs**: A unified `spec.md` outlining the roadmap and implementation checklists.
- **Task Files**: Individual markdown files under `tasks/*.md` tracking status, dependencies, target files, and tests.
- **Notes & Discoveries**: Captured directly in the corresponding task file under the `## Notes & Discoveries` heading to preserve context.
- **Spec Reconciler**: Run `python3 tools/sync.py` to automatically reconcile the task checklist in `spec.md` with individual task file statuses.

## Auto-Activation

...

When the `.agents/` directory exists in the project root, the Flow skill MUST be activated at session start. Detect the Flow specifications directory and load active specs and tasks before beginning work.

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

## Subagent-Driven Superpowers Protocol (MANDATORY)

To ensure high-reasoning model routing and automated verification, all complex Flow operations MUST delegate to dedicated subagents when the active harness exposes the shipped Flow agents:

- **Planning Phase**: Commands `/flow:prd` and `/flow:plan` delegate to `@prd-orchestrator` and `@plan-generator` respectively. These agents inherit harness model/tool settings and MUST invoke `superpowers:brainstorming` or `superpowers:writing-plans`.
- **Implementation Phase**: Command `/flow:implement` delegates to `@executor`. This agent inherits harness model/tool settings and MUST invoke `superpowers:test-driven-development` and `superpowers:verification-before-completion`.
- **Validation**: All planning artifacts MUST be validated by `code-reviewer` (via `superpowers:requesting-code-review`) before being presented to the user.

## Spec & Design Documents

All spec and design documents (including those created by superpowers brainstorming) MUST be written to the Flow spec directory:

- Default: `.agents/bundles/specs/<flow_id>/`
- Check `.agents/setup-state.json` for custom `root_directory`
- Do NOT use `docs/superpowers/specs/` — Flow manages all specs in `.agents/`

## Context Injection & Required Truths

To maintain context efficiency, Flow uses surgical extraction for session-start priming.

### Required Truths Markers

Documents such as `workflow.md`, `patterns.md`, and `tech-stack.md` SHOULD use markers to identify the most critical information for AI agents.

- **Start Marker:** `<!-- truth: start -->`
- **End Marker:** `<!-- truth: end -->`

The `SessionStart` hook (`detect-env.sh`) prioritized content between these markers. If missing, it falls back to basic extraction (e.g., first 10 list items).

### Project Identity & Index

- **Identity:** The first 5 lines of `product.md` (excluding headers) are used to prime the agent's purpose.
- **Index:** A structured "Project Context Index" is provided at the start of every session with links to all core Flow documents.

## Universal File Resolution Protocol

**PROTOCOL: How to locate files.**

To find a file (e.g., "**Product Definition**") within a specific context:

1. **Identify Index:** Determine the relevant index file:
    - **Project Context:** `.agents/index.md`
    - **Flow Context:**
        a. Locate active flows by scanning the `<Flow Directory>` dynamically for `<flow_id>/spec.md`
        b. Follow the spec's directory link. Index file is `<flow_folder>/spec.md`

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
| **Flow Directory** | `.agents/bundles/specs/` |
| **Template Directory** | `.agents/templates/` |
| **Code Styleguides Directory** | `.agents/code-styleguides/` |
| **Patterns** | `.agents/patterns.md` |
| **Knowledge Base** | `.agents/bundles/knowledge/` |
| **Knowledge Index** | `.agents/bundles/knowledge/index.md` |
| **Project Skills** | `.agents/skills/` |
| **Beads Config** | `.agents/beads.json` |
| **Research Directory** | `.agents/research/` |
| **Task Directory** | `.agents/tasks/` |

**Standard Default Paths (Flow):**

| Key | Default Path |
|-----|--------------|
| **Specification** | `.agents/bundles/specs/<flow_id>/spec.md` (unified spec + plan) |
| **Learnings** | `.agents/bundles/specs/<flow_id>/learnings.md` |

## Flow ID Naming Convention

**Format:** `shortname` (e.g., `user-auth`)

- **Active Flows:** Simple slug (e.g., `dark-mode`)
  - Derived from description: lowercase, hyphens for spaces, max 3-4 words
- **Archived Flows:** Logged to `.agents/bundles/knowledge/log.md` and deleted from the filesystem.

## Supported Harnesses

Every harness falls into one of three tiers:

- **First-class** — the repo ships maintained harness-specific manifests, agents, and install guidance; changes to the shared skills tree are verified against the harness.
- **Compatible bundle** — the harness consumes the repo through standard manifests or generic skill-discovery paths; no native wrapper is promised.
- **Free ride** — the harness discovers generic Agent Skills / `AGENTS.md` content; the repo ships no dedicated integration.

| Harness | Tier | Entry Point | Notes |
| --- | --- | --- | --- |
| **Antigravity** | first-class | `plugin.json` + `hooks.json` + `agents/*.md` + `skills/` | Primary plugin surface with skills, hooks, and shared Markdown subagents. |
| **Claude Code** | first-class | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + `agents/*.md` | Full plugin with skills, commands, hooks, and shared Markdown subagents. |
| **Codex CLI** | first-class | `.codex-plugin/plugin.json` + `.codex/agents/*.toml` + `.codex/config.toml` | Custom agents ship as pure TOML (tools inherited from session). |
| **OpenCode** | compatible bundle | `.opencode/plugins/flow.js` + `.opencode/agents/*.md` + native `.claude/skills/` / `.agents/skills/` reads | Project files and skills; no global install is advertised until an npm plugin is published. |
| **Cursor** | compatible bundle | `.cursor/rules/*.mdc` + `AGENTS.md` | Rules and project instructions only; no repository Cursor plugin manifest. |
| **VS Code / Copilot** | compatible bundle | `.github/agents/*.agent.md` + `.agents/skills/` | Workspace custom agents plus Agent Skills-compatible project skills. |
| **OpenClaw** | compatible bundle | Runtime `sessions_spawn` + skills discovery | Consumes Flow through runtime subagents and generic Agent Skills, not a static repo manifest. |

## File Resolution

| Resource | Location |
| --- | --- |
| Skills | `skills/<skill-name>/SKILL.md` |
| Shared slash-command prompt sources | `commands/flow/<command>.toml` |
| Claude Code slash commands | `commands/flow-<command>.md` |
| OpenCode command templates | `templates/opencode/commands/flow-<command>.md` |
| Subagents (Codex CLI) | `.codex/agents/<agent-name>.toml` (pure TOML; `developer_instructions` holds the prompt; no top-level `tools` — inherited from session `config.toml`) |
| Subagents (Antigravity / Claude Code plugin) | `agents/<agent-name>.md` (portable Markdown, slug `name`, required `description`, harness-specific tool lists omitted) |
| Subagents (OpenCode) | `.opencode/agents/<agent-name>.md` (`tools` as dict mapping + `mode: subagent`) |
| Subagents (VS Code / Copilot) | `.github/agents/<agent-name>.agent.md` |
| MCP servers | `mcp-servers/<server-name>/` |
| Hooks | `hooks/*.json` + `hooks/session-start` |
| Templates | `templates/skill-template/` |

## First-Party Skill Repositories

The following external repositories provide comprehensive, harness-verified skills and patterns that are fully compatible with Flow:

- **[litestar-skills](https://github.com/litestar-org/litestar-skills)** — Opinionated first-party skills for the Litestar framework ecosystem (advanced-alchemy, sqlspec, granian, saq, etc.).
- **[modular-skills](https://github.com/modular/skills)** — Official AI agent skills from Modular for **Mojo** and the **MAX** platform (`mojo-syntax`, `new-modular-project`, `mojo-python-interop`, `mojo-gpu-fundamentals`).
- **[railway-skills](https://github.com/railwayapp/railway-skills)** — Official Railway agent skills for project setup, deployment, and service management (`use-railway`).
- **[shadcn-ui](https://github.com/shadcn-ui/ui)** — Official shadcn/ui agent skills for component discovery, CLI mastery, and pattern enforcement.

## Task Status Markers (Synchronized via /flow:sync)

| Marker | Status | Task File Status |
|--------|--------|------------------|
| `[ ]` | Pending | `open` |
| `[~]` | In Progress | `in_progress` |
| `[x]` | Completed | `closed` |
| `[!]` | Blocked | `blocked` |
| `[-]` | Skipped | `skipped` |

**IMPORTANT:** Agents MUST NOT edit these markers manually. Use `/flow:sync` to reconcile `spec.md` with task files.

## Commands

**Harness note:** Claude Code exposes `commands/flow-*.md` as `/flow-*`. Antigravity derives slash commands from installed skills. Harnesses that consume `commands/flow/*.toml` use `/flow:<command>` semantics. OpenCode uses project command files or config-defined commands when installed, and otherwise receives Flow through the plugin context and skills. Codex currently runs the same workflows through the installed Flow skill and plain-language requests rather than plugin-defined slash commands.

**Lifecycle routing:** Keep `flow` as the small router skill. After it triggers, load the specific lifecycle skill: `flow-setup` for initialization and validation, `flow-planning` for PRD/spec/refine/revise/research/task work, `flow-execution` for implementation and TDD, `flow-sync-status` for sync/status/refresh/cleanup, and `flow-completion` for review/finish/archive/revert/docs.

| Lifecycle | Claude command | Shared command key | Purpose |
|---------|---------|---------|---------|
| Setup | `/flow-setup` | `flow/setup` | Initialize project with context files and first flow |
| PRD | `/flow-prd` | `flow/prd` | Analyze goals and generate Master Roadmap (Sagas) |
| Plan | `/flow-plan` | `flow/plan` | Create unified spec.md for a single Flow |
| Refine | `/flow-refine` | `flow/refine` | Expand coarse tasks into implementation-ready plan |
| Sync | `/flow-sync` | `flow/sync` | Reconcile spec.md task checklists with individual task files |
| Research | `/flow-research` | `flow/research` | Conduct pre-PRD research |
| Docs | `/flow-docs` | `flow/docs` | Five-phase documentation workflow |
| Implement | `/flow-implement` | `flow/implement` | Execute tasks from plan (context-aware) |
| Status | `/flow-status` | `flow/status` | Display progress overview dashboard for active flows |
| Revert | `/flow-revert` | `flow/revert` | Git-aware revert of flows, phases, or tasks |
| Validate | `/flow-validate` | `flow/validate` | Validate project integrity and fix issues |
| Revise | `/flow-revise` | `flow/revise` | Update spec/plan when implementation reveals issues |
| Archive | `/flow-archive` | `flow/archive` | Archive completed flows + elevate patterns |
| Refresh | `/flow-refresh` | `flow/refresh` | Sync context with codebase after external changes |
| Task | `/flow-task` | `flow/task` | Create ephemeral exploration task |
| Finish | `/flow-finish` | `flow/finish` | Complete flow: verify, review, merge/PR/keep/discard |
| Review | `/flow-review` | `flow/review` | Dispatch code review for completed work |

## Task-Centric Filesystem Engine (OKF)

In Flow, task states and planning metadata are tracked entirely inside local Markdown files inside the `.agents/bundles/specs/<flow_id>/` directory:

- **Unified Specification (`spec.md`)**: The root design and plan. The `Implementation Plan` section contains the checklist of tasks.
- **Task Files (`tasks/<short_id>.md`)**: Detailed metadata for each task in the plan.

### Task File Schema

Each task file under `tasks/<short_id>.md` (where `<short_id>` matches the ID in `spec.md`, e.g., `1.1.md`) MUST start with a YAML frontmatter block:

```yaml
---
id: flow-id:1.1
status: open
depends_on: []
files:
  - src/auth.py
tests:
  - tests/test_auth.py
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: null
---
```

Fields:

- **`id`**: Unique string in the format `<flow_id>:<short_id>`.
- **`status`**: Current lifecycle state: `open`, `in_progress`, `closed`, `blocked`, or `skipped`.
- **`depends_on`**: List of parent task IDs that this task depends on.
- **`files`**: List of repository-relative paths to source files affected by this task.
- **`tests`**: List of repository-relative paths to test files verified by this task.
- **`created_at` / `updated_at`**: Valid ISO-8601 timestamps.
- **`commit`**: The commit SHA when the task is resolved (optional, only for `closed` status).

### Task Notes & Discoveries

To capture learnings and debug findings, append notes to the bottom of the task file under a `## Notes & Discoveries` heading:

```markdown
# Task 1.1

## Notes & Discoveries
- [2026-08-11 12:00] Discovered that Zod form validation handles this case automatically.
- [2026-08-11 12:15] Refined regex pattern to match ISO-8601 timezone offsets.
```

---

## Spec & Tasks Reconciler

The reconciler matches the checklist in `spec.md` with the task files:

1. **Checklist Status Mapping**: `spec.md` checklist status markers are updated by `/flow:sync` to match the `status` of their task files:
   - `open` -> `[ ]`
   - `in_progress` -> `[~]`
   - `closed` -> `[x]` (and the commit SHA is appended if present: `[<sha>]`)
   - `blocked` -> `[!]`
   - `skipped` -> `[-]`
2. **Auto-Scaffolding**: If a task is listed in `spec.md` but has no file in `tasks/`, `/flow:sync` auto-generates the task file with default frontmatter.

---

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

## Task Workflow (TDD) - Beads-First

1. **Select task** from `bd ready` (Beads is source of truth).
2. **Claim task** with `bd update <id> --claim`.
3. **Investigate & Note**: Record findings with `bd note <id> "..."`.
4. **Write failing tests** (Red).
5. **Implement to pass** (Green).
6. **Refactor** while green.
7. **Commit**: `<type>(<scope>): <description>`.
8. **Close task** in Beads with the commit SHA: `bd close <id> --reason "[abc1234]..."`.
9. **Sync to markdown**: Run `/flow:sync` when `syncPolicy.flowSyncAfterMutation` is enabled (default).

**CRITICAL:** After Beads state changes, agents MUST follow `syncPolicy.flowSyncAfterMutation` in `.agents/beads.json`. Never write markers (`[x]`, `[~]`, etc.) directly to spec.md.

**Important:** All commits stay local. Flow never pushes automatically.

## Phase Checkpoints

At phase completion:

1. Run full test suite
2. Verify coverage requirements
3. Ensure phase completion is committed
4. Prompt for pattern elevation
5. Manual verification with user

## Skills

Skills are available in `skills/` for harnesses that consume Agent Skills:

| Skill | Purpose |
|-------|---------|
| **flow** | Auto-activates when `.agents/` exists. Workflow guidance. |
| **50+ tech skills** | React, Rust, Litestar, SQLSpec, testing, etc. |

## Installation

```bash
# Claude Code
claude plugin marketplace add cofin/flow
claude plugin install flow@flow-marketplace

# Codex CLI
codex plugin marketplace add cofin/flow

# Install official Beads
curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash
```
