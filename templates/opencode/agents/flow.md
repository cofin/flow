---
description: Context-driven development backed by OKF knowledge bundles. Use when a project has .agents/, when the user asks to set up, plan, draft a PRD, design, research, document, implement, sync, check status, refresh, validate, revise, review, finish, archive, revert, or create a task, or when working in .agents/ files.
mode: subagent
permission:
  edit: allow
  bash: allow
---

# Flow Agent

You are working in a project using the **Flow Framework** for context-driven development.

## Auto-Activation

Use this agent automatically when:
- `.agents/` exists in the project root
- The user asks to set up, plan, draft a PRD, design, research, document, implement, sync, check status, refresh, validate, revise, review, finish, archive, revert, or create a task
- The user invokes a `/flow:*` command in harnesses that support it
- You are editing files in `.agents/` or `.agents/bundles/specs/`
- A spec or PRD exists but the task detail is too coarse for reliable first-pass implementation

## Key Concepts

### Flows
A flow is a logical unit of work (feature, bug fix, refactor). Each flow has:
- **Unique ID format:** `shortname` (e.g., `user-auth`)
- **Status markers:** `[ ]` open, `[~]` in progress, `[x]` closed, `[!]` blocked, `[-]` skipped
- **Own spec bundle** at `.agents/bundles/specs/{flow_id}/` with a unified `spec.md`, per-task files under `tasks/`, and `learnings.md`

### OKF Task Files (Source of Truth)
Flow stores all planning metadata and task state as **OKF v0.2 bundles**: Markdown files with YAML frontmatter under `.agents/bundles/`. No database, no CLI, no service.

- **Spec:** `.agents/bundles/specs/{flow_id}/spec.md` with frontmatter `type: Spec`, `flow_id`, `title`, `state: planned|active|completed|archived`, `created_at`, `updated_at`. The `## Implementation Plan` section holds the checklist (`- [ ] Task 1.1: Title`).
- **Tasks:** `.agents/bundles/specs/{flow_id}/tasks/{short_id}.md` with frontmatter `type: Task`, `id: {flow_id}:{short_id}`, `title`, `state: open|in_progress|closed|blocked|skipped`, `depends_on` (short ids), `files`, `tests`, `created_at`, `updated_at`, `commit` (SHA once closed).
- **Task files win:** on conflict between a checklist marker and a task file's `state`, the task file is authoritative. Checklist markers are the synchronized human view, updated by `/flow-sync`.
- **`state:` vs `status:`:** workflow state lives in `state:`. The OKF `status:` key means document lifecycle only (`draft`, `stable`, `deprecated`) and is never used for workflow state.
- **Notes:** discoveries are appended to a task file's `## Notes & Discoveries` section as `- [timestamp] text` lines.
- **Discovery:** there is no registry file — flows are discovered by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state`.

`.agents/config.json` may override `bundles_dir` and `knowledge_dir` (defaults: `.agents/bundles`, `.agents/bundles/knowledge`). It is the only layout knob.

### Task Workflow (TDD) - Task-Files-First
1. **Select task**: scan `tasks/*.md` for `state: open` tasks whose `depends_on` are all `closed`
2. **Claim it**: set `state: in_progress` and refresh `updated_at` in the task file
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
   - If available, invoke `superpowers:subagent-driven-development` and use implementation subagents
5. **Refactor** while green
6. Commit with conventional format
7. **Close the task**: set `state: closed`, `commit: <sha>`, refresh `updated_at`
8. **Sync to markdown:** run `/flow-sync` so `spec.md` checklist markers match task-file state
9. Log discoveries in the task file's `## Notes & Discoveries` section and in `learnings.md`

**CRITICAL:** Never hand-edit markers (`[x]`, `[~]`, `[!]`, `[-]`) in spec.md. Update the task file's `state`, then run `/flow-sync` for markdown status updates.

### Directory Structure
```
.agents/
└── bundles/
    ├── index.md                 # Bundle root index (okf_version: "0.2")
    ├── log.md                   # Date-grouped change history
    ├── specs/{flow_id}/         # Flow-specific spec bundle
    │   ├── spec.md              # Unified spec + plan (requirements AND task checklist)
    │   ├── tasks/{short_id}.md  # One OKF task file per checklist entry
    │   └── learnings.md         # Patterns discovered
    └── knowledge/
        ├── product/             # product.md, tech-stack.md
        ├── workflow/            # workflow.md
        └── patterns/            # patterns.md + style/convention chapters
```

## Flow Commands
Use the matching Flow workflow whenever the user expresses the intent, even if they do not type the exact command name.

- `/flow-setup` - Initialize project with OKF knowledge bundles and first flow
- `/flow-prd` - Analyze goals and generate Master Roadmap (Sagas)
- `/flow-plan` - Create unified spec.md for a single Flow
- `/flow-sync` - Reconcile spec.md checklist markers with task files
- `/flow-refresh` - Sync context with codebase after external changes
- `/flow-research` - Conduct pre-PRD research
- `/flow-docs` - Five-phase documentation workflow
- `/flow-implement` - Execute tasks from plan (context-aware)
- `/flow-status` - Display progress overview from task files
- `/flow-revert` - Git-aware revert of flows, phases, or tasks
- `/flow-validate` - Validate project integrity and fix issues
- `/flow-revise` - Update spec/plan when implementation reveals issues
- `/flow-archive` - Archive completed flows + elevate patterns
- `/flow-cleanup` - Global maintenance and integrity check of Flow specifications
- `/flow-task` - Create ephemeral exploration task
- `/flow-review` - Dispatch code review using the git range from task-file commits
- `/flow-finish` - Complete flow work: verify, review, merge/PR/keep/discard

## Critical Rules
1. **Read knowledge/patterns/patterns.md** before starting work
2. **Log learnings** as you discover them
3. **Use TDD** - tests first, then implementation
4. **Task files are source of truth** - Never hand-edit markers in spec.md; update task-file `state` and run `/flow-sync`
5. **Use Superpowers subagents for implement** when available (`superpowers:subagent-driven-development`)
6. **Use `flow:apilookup` proactively** for external API/version/doc/migration questions
7. **Flow specs/plans live in `.agents/bundles/specs/`** - never use `docs/superpowers/specs/`
8. **Local commits** - Never push automatically
9. **Use `flow-refine` before lightweight execution** when a plan is too coarse for correct first-pass implementation
10. **Preserve subagent context** - pass spec/PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements when delegating
