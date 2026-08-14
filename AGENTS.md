# Flow Context

This file provides guidance to AI coding agents working with code in this repository.

> **Flow is a skill, not a CLI.** There is no `flow` executable. Never run `flow`, `flow sync`, `flow prd`, `flow status`, etc. as shell commands — they will fail. Invoke the Flow skill, or use the `/flow:*` slash commands (e.g. `/flow:sync`, `/flow:prd`).

## Overview

**Flow** is a unified toolkit for **Context-Driven Development** combining:

- **Flow Framework**: Spec-first planning, human-readable context, TDD workflow
- **Open Knowledge Format (OKF) bundles**: Local specifications (`spec.md`), task files (`tasks/*.md`), and knowledge chapters with YAML frontmatter under `.agents/bundles/`.

## The Task-First Mandate

**CRITICAL:** Every task, discovery, and decision MUST be recorded in the local specification folder.

- **Flow Specs**: A unified `spec.md` outlining the roadmap and implementation checklists.
- **Task Files**: Individual markdown files under `tasks/*.md` tracking status, dependencies, target files, and tests.
- **Notes & Discoveries**: Captured directly in the corresponding task file under the `## Notes & Discoveries` heading to preserve context.
- **Spec Reconciler**: Invoke `/flow:sync` where supported, or apply the `reconcile` operation from `skills/flow/references/state.md` inline with ordinary file tools. No consumer runtime helper is required.

The normative plan identity, lifecycle fields, operation transitions, continuity snapshot, and file-tool transaction/recovery protocol are defined once in [`skills/flow/references/state.md`](skills/flow/references/state.md). Task files remain authoritative for task state. Consumer agents apply that Markdown contract with ordinary file tools; maintainer Python is validation/generation/test support, not a Flow runtime dependency.

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
| **Product Definition** | `.agents/bundles/product/product.md` |
| **Tech Stack** | `.agents/bundles/product/tech-stack.md` |
| **Workflow** | `.agents/bundles/knowledge/workflow.md` |
| **Flow Directory** | `.agents/bundles/specs/` |
| **Template Directory** | `.agents/templates/` |
| **Patterns** | `.agents/bundles/knowledge/patterns.md` (style guides live in `knowledge/` as sibling chapters) |
| **Knowledge Base** | `.agents/bundles/knowledge/` |
| **Bundle Root Index** | `.agents/bundles/index.md` |
| **Project Skills** | `.agents/bundles/skills/` (legacy fallback: `.agents/skills/`) |
| **Layout Overrides** | `.agents/config.json` (`bundles_dir`, `knowledge_dir`) |
| **Research Directory** | `.agents/bundles/research/` |
| **Task Directory** | `.agents/tasks/` (ephemeral scratch, never tracked) |

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

## Open Knowledge Format (OKF) Bundles

Flow stores all planning metadata, task state, and curated knowledge as **OKF v0.2 bundles**: directories of Markdown files with YAML frontmatter, per the [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md). No database, no CLI, no service — any agent or human that can read files can read a bundle.

### Bundle Layout

```text
.agents/bundles/
  index.md                      # bundle root index; carries okf_version: "0.2"
  log.md                        # date-grouped change history (newest first, ISO dates)
  product/                      # identity docs: product.md, tech-stack.md (product-guidelines.md optional)
  knowledge/                    # THE synthesized current-state chapters, flat:
    workflow.md                 #   canonical commands + development workflow
    patterns.md                 #   elevated conventions and gotchas
    <topic>.md                  #   architecture.md, <lang>-style.md, ... as chapters
  research/                     # pre-PRD research documents (type: Research)
  specs/<flow_id>/              # PLANNED and ACTIVE flows only (see Archive Lifecycle)
    spec.md                     # the flow's design + Implementation Plan checklist
    tasks/<short_id>.md         # one file per task (e.g. tasks/1.1.md)
    learnings.md                # per-flow discoveries awaiting synthesis (optional)
  skills/                       # project-local skills (<name>/SKILL.md)
```

`.agents/config.json` may override `bundles_dir` and `knowledge_dir` (defaults: `.agents/bundles`, `.agents/bundles/knowledge`). It is the only layout knob. Do not invent additional top-level categories or scatter loose files at the bundle root — every document belongs to exactly one category above.

### Frontmatter Rules

Every non-reserved `.md` file in a bundle carries YAML frontmatter with a non-empty `type` — the only OKF-required key. Reserved files (`index.md`, `log.md`) need none. Flow's type vocabulary (consumers must tolerate unknown types):

| `type` | Used for |
|--------|----------|
| `Spec` | `specs/<flow_id>/spec.md` |
| `Task` | `specs/<flow_id>/tasks/*.md` |
| `Guide` | `product/` docs and `knowledge/workflow.md` |
| `Pattern` | `knowledge/patterns.md` and style/convention chapters |
| `Research` | `research/` documents |
| `Learnings` | `learnings.md` (transient, until synthesized) |
| `Skill` | `skills/<name>/SKILL.md` |

**Workflow state lives in `state:`.** The OKF `status:` key keeps its spec meaning — document lifecycle (`draft`, `stable`, `deprecated`) — and stays optional. Never store workflow state in `status`. Never add `generated:` model attribution.

### Spec File Schema (`spec.md`)

The examples below are introductory OKF shapes. Executable Flow specs and tasks add the complete continuity fields and invariants defined by [`skills/flow/references/state.md`](skills/flow/references/state.md).

```yaml
---
type: Spec
flow_id: user-auth              # must equal the directory name
title: User Authentication
state: planned                  # planned | active | completed
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
---
```

Optional keys: `description`, `tags`, `status` (OKF lifecycle), `stale_after`. A resident spec's `state` enum is exactly `planned`, `active`, or `completed` — a spec is never `blocked` or `archived`. Archive is a committed contraction that deletes the spec directory.

### Task File Schema (`tasks/<short_id>.md`)

```yaml
---
type: Task
id: user-auth:1.1               # <flow_id>:<short_id>
title: Add login endpoint
state: open                     # open | in_progress | closed | blocked | skipped
depends_on: []                  # SHORT ids within the same flow, e.g. ["1.1"]
files:
  - src/auth.py
tests:
  - tests/test_auth.py
created_at: 2026-08-11T12:00:00Z
updated_at: 2026-08-11T12:00:00Z
commit: null                    # 7+ hex commit SHA once closed
---
```

- **`id`**: Unique string in the format `<flow_id>:<short_id>`; `<short_id>` matches the filename and the checklist ID in `spec.md`.
- **`state`**: Task workflow state: `open`, `in_progress`, `closed`, `blocked`, or `skipped`.
- **`depends_on`**: Short ids of tasks in the same flow that must close first.
- **`files`** / **`tests`**: Repository-relative paths this task touches / verifies.
- **`created_at` / `updated_at`**: Valid ISO-8601 timestamps.
- **`commit`**: The commit SHA once the task is `closed`.

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

1. **Checklist State Mapping**: `spec.md` checklist markers are updated by `/flow:sync` to match the `state` of their task files:
   - `open` -> `[ ]`
   - `in_progress` -> `[~]`
   - `closed` -> `[x]` (and the commit SHA is appended if present: `[<sha>]`)
   - `blocked` -> `[!]`
   - `skipped` -> `[-]`
2. **Task file wins**: on conflict between a checklist marker and a task file's `state`, the task file is authoritative.
3. **Auto-Scaffolding**: If a task is listed in `spec.md` but has no file in `tasks/`, `/flow:sync` auto-generates the task file with default frontmatter.

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
2. **Elevate** - At phase/flow completion, move reusable patterns to `.agents/bundles/knowledge/patterns.md`
3. **Synthesize** - During sync and archive, RE-SYNTHESIZE: read the affected chapter in `.agents/bundles/knowledge/`, integrate the new learning into the existing prose where it belongs, and rewrite the chapter as coherent current-state documentation. NEVER append a dated entry, a "completed X" note, or a changelog line to a knowledge chapter — history goes in `log.md`, knowledge chapters describe only how the codebase works now. Delete the source `learnings.md` content once synthesized.
4. **Inherit** - New flows read `knowledge/patterns.md` + scan the other `.agents/bundles/knowledge/` chapters.

Repeated user corrections or visible frustration are high-signal workflow gaps. Capture them in `learnings.md`, elevate them into `.agents/bundles/knowledge/patterns.md`, and refine `.agents/bundles/skills/flow-memory-keeper/SKILL.md` when present so the same miss does not have to be corrected again.

Knowledge chapters in `.agents/bundles/knowledge/` survive archive cleanup and serve as the expert implementation details for the codebase.

### Archive Lifecycle

`specs/` holds `planned` and `active` flows plus a short-lived `completed` flow awaiting archive. Completing and archiving a flow is a three-step contraction, not an accumulation:

1. **Synthesize** the flow's learnings and task notes into the knowledge chapters (re-synthesis rules above).
2. **Log** one entry in `.agents/bundles/log.md`: date, flow_id, one-line outcome, and the final commit SHA.
3. **Delete** the spec directory. Git history is the archive — `git log -- .agents/bundles/specs/<flow_id>` recovers everything, and tracked bundles make restoration a `git checkout` away.

Never keep `completed` spec directories piling up in the bundle, and never create a resident `archived` spec state. If a completed backlog exists, `/flow:cleanup` consolidates and removes it in one pass.

If `.agents/bundles/skills/flow-memory-keeper/SKILL.md` exists, invoke it during sync, archive, finish, revise, and failure recovery so learnings, failures, and spec cleanup remain mandatory instead of ad hoc.

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

1. **Select task**: a task is ready when its `state` is `open` and every `depends_on` task is `closed`.
2. **Claim task**: set `state: in_progress` (and bump `updated_at`) in the task file.
3. **Investigate & Note**: Record findings under the task file's `## Notes & Discoveries`.
4. **Write failing tests** (Red).
5. **Implement to pass** (Green).
6. **Refactor** while green.
7. **Commit**: `<type>(<scope>): <description>`.
8. **Close task**: set `state: closed` and record the commit SHA in the task file's `commit:` field.
9. **Sync to spec**: run `/flow:sync` (or apply the reconciler rules inline) so the `spec.md` checklist reflects task-file state.

**CRITICAL:** Task files are the source of truth. Update the task file first, then reconcile the `spec.md` checklist — never flip checklist markers without the matching task-file change. Reconciliation is NOT optional or deferred: the checklist must be updated **immediately after every task state change** (claim, block, skip, close), so the markdown task list is always current for humans and other agents.

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
```
