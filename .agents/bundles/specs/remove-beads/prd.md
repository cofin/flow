# Master PRD: Transition to OKF Bundles & Remove Beads

## Context & Objectives
The Flow framework has historically relied on Beads (`bd` CLI) as its primary source of truth for task state and context tracking. While Beads provides robust task memory, it introduces a binary dependency, local SQLite databases, and remote Dolt synchronization, which increases setup complexity and limits portability across developer environments.

This project transitions the Flow framework to a **Beads-free, OKF (Open Knowledge Format) bundle-centric architecture**. The filesystem will become the primary database. Flows and tasks will be represented as self-contained OKF bundles containing Markdown files with YAML frontmatter.

**Archive & Rewrite Strategy:** We will NOT incrementally refactor the codebase. Instead, we will move the entire current codebase (all code, tests, templates, configs, EXCEPT the active `.agents/` folder) into `archive/v1/` at the root of the repository. We will then perform a clean, from-scratch rewrite of the Flow framework.

**No Backward Compatibility Constraint:** We are not maintaining backward compatibility with the old Beads configuration or specs structures. The focus is entirely on a clean, optimal implementation of the new OKF structure.

**Dogfooding Separation Constraint:** Flow is used to develop Flow. We must maintain a strict separation between:
1. **Product Templates** (located in `templates/agent/`): The templates that the Flow framework distributes/installs when a user runs `/flow:setup`.
2. **Development Metadata** (located in `.agents/`): The metadata used by the AI agent to track the development of this repository.

Detailed research on harness integration and hook mechanisms is documented in [Harness Integration Research](./harness_research.md).

### North Star Outcomes
1. **Zero External Dependencies**: Complete removal of Beads CLI command calls, configurations, and metadata.
2. **First-Class OKF Support**: Standardization of planning, specifications, and task state tracking around the OKF bundle format.
3. **Relative File Links**: All generated specifications, task concepts, and documentation use relative path links rather than absolute `file:///` paths.
4. **Harness-Native hooks**: Validation and context injection are handled via harness-native hooks (Claude, Antigravity, Codex, OpenCode), driven by a single `.agents/config.json` configuration file, avoiding global git commit hooks.
5. **Knowledge Flywheel Optimization**: Archiving flows will focus on synthesizing task notes and results into structured, topic-based articles under the `.agents/bundles/knowledge/` directory.

---

## Architecture Design

### 1. Unified Directory Layout
All Flow-related active plans and curated project knowledge reside under `.agents/bundles/` to keep the `.agents/` root clean. Active flows live under `specs/`, and curated long-term project information lives under `knowledge/` in structured subfolders:

```
.agents/
├── config.json                 # Workspace-local configuration
└── bundles/
    ├── specs/                  # Active flow and saga specs
    │   ├── remove-beads/       # Saga bundle
    │   └── flow-archive-v1/    # Chapter 1 bundle
    └── knowledge/              # Curated long-term project knowledge (no history/archives)
        ├── product/            # Product definitions
        ├── workflow/           # Developer workflow rules
        ├── code-styleguides/   # Language and framework styleguides
        └── patterns/           # Synthesized implementation patterns
```

### 2. The OKF Flow Bundle Structure
Every active flow or saga is represented as a directory under `.agents/bundles/specs/<flow_id>/`.
The bundle consists of the following structure:

```
.agents/bundles/specs/<flow_id>/
├── spec.md           # Unified spec, plan, and flow metadata (YAML frontmatter)
├── tasks/            # Directory containing individual task markdown files
│   ├── 001-setup.md  # Task 1
│   ├── 002-impl.md   # Task 2
│   └── 003-test.md   # Task 3
└── research/         # Research documents (moved here once associated with the flow)
```

#### 2.1 Specification Worksheet (`spec.md`)
The specification worksheet is the entry point of the bundle. It contains the flow's metadata in its YAML frontmatter, followed by the technical requirements, design decisions, and implementation plan.
```yaml
---
type: flow
id: user-auth
title: User Authentication
description: Implement email/password login and JWT sessions
status: planned  # planned | in_progress | completed | blocked
parent_prd: auth-system
created_at: 2026-07-08T23:10:36Z
updated_at: 2026-07-08T23:10:36Z
tags: [auth, security]
---

# Flow: User Authentication

## Specification
...
```

#### 2.2 Task Concept (`tasks/*.md`)
Each task is a standalone markdown file. Discoveries and learnings are captured locally inside the task file itself.
```yaml
---
type: task
id: user-auth:001-setup
title: Configure authentication database schemas
status: open  # open | in_progress | closed | blocked
priority: P2
depends_on: []
created_at: 2026-07-08T23:10:36Z
updated_at: 2026-07-08T23:10:36Z
assigned_to: executor
files:
  - src/auth/db.py
tests:
  - tests/test_auth_db.py
commit: null
---

# Description
Define database schema for storing users and user sessions.

# Verification Steps
1. Run `pytest tests/test_auth_db.py`

# Notes & Discoveries
- Note 1 (Added by executor)
- Note 2 (Added by executor)
```


### 3. Hook Consolidation (`tools/priming.py`)
To prevent duplicate hook logic across harnesses, all session start context extraction, validation, and priming is consolidated into a single Python script: `tools/priming.py`.
- Harness-specific wrappers (such as `hooks/hooks-agy.json`, `hooks-claude.json`, and `.opencode/plugins/flow.js`) simply invoke `tools/priming.py`.
- The rule engines (`.cursor/rules/flow.mdc`, `.github/agents/*.agent.md`) are updated to load context based on the output of this priming script.
- The priming script dynamically scans `.agents/skills/` for custom project-specific skills and appends an index of these skills (names, descriptions, and relative paths) to the session start output, enabling the agent to locate and lazy-load them on-demand via `view_file`.
- There are no Git pre-commit hooks.

### 3.5 Workspace Rules for Non-Plugin Harnesses (Self-Contained Rule Scaffolding)
For harnesses that do not support global plugins (such as Cursor and VS Code/Copilot), `/flow:setup` will scaffold workspace-local rule/prompt files in the project root:
- **Cursor**: Generates `.cursor/rules/flow.mdc`
- **VS Code / Copilot**: Generates `.github/agents/flow.agent.md`
These files contain the instructions detailing the OKF bundle structure, task claiming workflow, and how to query the registry. They also instruct the agent to discover and lazy-load project-specific custom skills from `.agents/skills/`. This allows any developer agent working in the repository to natively comply with the Flow framework without needing a globally installed plugin.


### 4. Configuration (`.agents/config.json`)
A single, unified configuration file:
```json
{
  "bundles_dir": ".agents/bundles",
  "default_priority": "P2",
  "auto_sync": true,
  "knowledge_dir": ".agents/bundles/knowledge"
}
```

---

## Master Roadmap

### Chapter 1: Codebase Archiving & Setup (`flow-archive-v1`)
- **Objectives**: Move the entire current codebase into `archive/v1/` at the root of the repo (except the `.agents/` folder). Set up the new directory structures and initialize the workspace configuration.
- **Deliverables**:
  - Codebase archived to `/archive/v1/`.
  - Workspace `.agents/config.json` created.
  - Workspace `.agents/bundles/specs/` and `.agents/bundles/knowledge/` directories initialized.

### Chapter 2: Hook Consolidation & Environment Priming (`flow-hooks-consolidate`)
- **Objectives**: Implement the unified Python priming hook (`tools/priming.py`) that reads `.agents/config.json`, performs validation, and generates session start context. Update all harness wrappers to call it.
- **Deliverables**:
  - Creation of `tools/priming.py`.
  - Refactoring of Antigravity `hooks/hooks-agy.json`, Claude `hooks/hooks-claude.json`, Codex hooks, and OpenCode `.opencode/plugins/flow.js` to execute `tools/priming.py` using correct flat JSON hook structures.
  - Refactoring of `tools/validate.py` and `tests/test_antigravity_hooks.py` to support flat JSON structures and path changes.
  - Rule files `.cursor/rules/flow.mdc` and `.github/agents/*.agent.md` updated to reference new bundles layout.

### Chapter 3: Core Flow Router & Setup Skills (`flow-router-setup-rewrite`)
- **Objectives**: Rewrite setup commands and the core flow router skill. On `/flow:setup`, initialize `.agents/config.json`, initialize OKF directories under `bundles/specs/` and `bundles/knowledge/`, and generate workspace-local rule files for Cursor and VS Code to enable native Flow integration.
- **Deliverables**:
  - Core router skill `skills/flow/SKILL.md` rewritten to route to global plugin resources and resolve local custom skills.
  - Setup skill `skills/flow-setup/SKILL.md` rewritten to initialize configuration, create OKF folders, and scaffold workspace rules (`.cursor/rules/flow.mdc` and `.github/agents/flow.agent.md`).

### Chapter 4: Planning & PRD Skills (`flow-planning-rewrite`)
- **Objectives**: Redesign the planning commands (`/flow:prd`, `/flow:plan`, `/flow:refine`) to generate OKF flow bundles under `.agents/bundles/specs/<flow_id>/` with relative path links.
- **Deliverables**:
  - Refactored `/flow:prd`, `/flow:plan`, and `/flow:refine` commands.
  - New planning skills generating unified requirements/technical `spec.md` (with flow metadata in frontmatter), and individual task markdown files in `tasks/*.md`.

### Chapter 5: Executor Implementation Skills (`flow-execution-rewrite`)
- **Objectives**: Rewrite implementation workflows (`/flow:implement`). Read ready tasks from `tasks/*.md`, claim a task by setting `status: in_progress`, allow recording notes in the task file, and close by setting `status: closed` and adding the commit SHA.
- **Deliverables**:
  - Refactored `/flow:implement` and `skills/flow-execution/SKILL.md`.
  - Task selection and claiming logic reading from `tasks/*.md`.
  - Note recording logic appending directly to task markdown files.

### Chapter 6: Reconciler, Sync & Status Skills (`flow-sync-status-rewrite`)
- **Objectives**: Rewrite status tracking and sync commands (`/flow:sync`, `/flow:status`) to dynamically scan active flow specs under `.agents/bundles/specs/*/spec.md`, validate YAML frontmatter, check relative link integrity, and report active status.
- **Deliverables**:
  - Refactored `/flow:sync`, `/flow:status`, and `/flow:cleanup`.
  - OKF Bundle validation script checking YAML frontmatter, dependencies, and relative links.

### Chapter 7: Flow Completion & Knowledge Base Synthesis (`flow-completion-rewrite`)
- **Objectives**: Rewrite `/flow:finish` and `/flow:archive`. When completing a flow, parse the notes in the task files and synthesize them into structured, topic-based articles in the curated Knowledge Base under `.agents/bundles/knowledge/<topic>/` (e.g. workflow, product, styleguides), and then delete the active flow spec folder (the archive is no longer tracked on disk).
- **Deliverables**:
  - Refactored `/flow:finish` (and `/flow:revert` if necessary).
  - Knowledge extraction and catalog synthesis engine producing curated articles.

### Chapter 8: Test Suite Realignment (`flow-test-suite-rewrite`)
- **Objectives**: Implement a comprehensive, unified validation test suite in `tools/validate.py` that verifies OKF bundle schema structure, relative path references, and configuration integrity.
- **Deliverables**:
  - Test suite validating YAML frontmatter structure, relative link resolution, and configuration defaults.
  - Consolidated validator at `tools/validate.py`.

### Chapter 9: Optional Query CLI / Database Layer (`flow-query-db-optional`)
- **Objectives**: Low-priority task. Implement a Python-based query CLI layer using Litestar-like structure, `sqlspec`, and `duckdb` to query and catalog the bundles.
- **Deliverables**:
  - Optional CLI queries for flows, tasks, and knowledge.

