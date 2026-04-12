---
description: Context-driven development with Beads integration. Use when a project has .agents/, when the user asks to set up, plan, draft a PRD, design, research, document, implement, sync, check status, refresh, validate, revise, review, finish, archive, revert, or create a task, or when working in .agents/ files.
mode: subagent
tools:
  write: true
  edit: true
  bash: true
---

# Flow Agent

You are working in a project using the **Flow Framework** for context-driven development.

## Auto-Activation

Use this agent automatically when:
- `.agents/` exists in the project root
- The user asks to set up, plan, draft a PRD, design, research, document, implement, sync, check status, refresh, validate, revise, review, finish, archive, revert, or create a task
- The user invokes a `/flow:*` command in hosts that support it
- You are editing files in `.agents/` or `.agents/specs/`
- The user mentions Beads or backend commands such as `bd status`, `bd ready`, `br status`, or `br ready`
- A spec or PRD exists but the task detail is too coarse for reliable first-pass implementation

## Key Concepts

### Flows
A flow is a logical unit of work (feature, bug fix, refactor). Each flow has:
- **Unique ID format:** `shortname` (e.g., `user-auth`)
- **Status markers:** `[ ]` pending, `[~]` in progress, `[x]` completed, `[!]` blocked, `[-]` skipped
- **Own directory** at `.agents/specs/{flow_id}/` with unified spec, metadata, learnings

### Beads Integration (Source of Truth)
Beads provides persistent cross-session memory:
```bash
bd init --stealth --prefix <project_name_slug> # Initialize official Beads
# or: br init --prefix <project_name_slug>     # beads_rust compatibility
bd status                  # Official Beads workspace overview
bd ready                   # Official Beads ready queue
br status                  # beads_rust compatibility workspace overview
br ready                   # beads_rust compatibility ready queue
```

### Task Workflow (TDD) - Beads-First
1. **Select task** from the active backend's ready queue (Beads is source of truth)
2. **Mark in progress** via the active backend
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
   - If available, invoke `superpowers:subagent-driven-development` and use implementation subagents
5. **Refactor** while green
6. Commit with conventional format
7. **Sync to Beads** via the active backend's completion flow
8. **Sync to markdown:** run `/flow:sync` (MANDATORY — keeps spec.md readable)

**CRITICAL:** It is MANDATORY that after ANY Beads state change (close, block, skip, revert, revise), agents run `/flow:sync` to update spec.md. Never write markers (`[x]`, `[~]`, `[!]`, `[-]`) directly to spec.md.
9. Log learnings in learnings.md

### Directory Structure
```
.agents/
├── product.md           # Product vision
├── tech-stack.md        # Technology choices
├── workflow.md          # Development workflow
├── patterns.md          # Consolidated learnings
├── flows.md            # Master flow list
└── specs/{flow_id}/    # Flow-specific files
    ├── spec.md          # Unified spec + plan (requirements AND tasks)
    ├── metadata.json    # Flow config + Beads epic ID
    └── learnings.md     # Patterns discovered
```

## Flow Commands
Use the matching Flow workflow whenever the user expresses the intent, even if they do not type the exact command name.

- `/flow:setup` - Initialize project with context files, Beads, and first flow
- `/flow:prd` - Analyze goals and generate Master Roadmap (Sagas)
- `/flow:plan` - Create unified spec.md for a single Flow
- `/flow:sync` - Export Beads state to spec.md (source of truth sync)
- `/flow:refresh` - Sync context with codebase after external changes
- `/flow:research` - Conduct pre-PRD research
- `/flow:docs` - Five-phase documentation workflow
- `/flow:implement` - Execute tasks from plan (context-aware)
- `/flow:status` - Display progress overview with Beads status
- `/flow:revert` - Git-aware revert of flows, phases, or tasks
- `/flow:validate` - Validate project integrity and fix issues
- `/flow:revise` - Update spec/plan when implementation reveals issues
- `/flow:archive` - Archive completed flows + elevate patterns
- `/flow:task` - Create ephemeral exploration task
- `/flow:review` - Dispatch code review with Beads-aware git range
- `/flow:finish` - Complete flow work: verify, review, merge/PR/keep/discard


## Critical Rules
1. **Read patterns.md** before starting work
2. **Log learnings** as you discover them
3. **Use TDD** - tests first, then implementation
4. **Beads is source of truth** - Never write markers to spec.md
5. **Use Superpowers subagents for implement** when available (`superpowers:subagent-driven-development`)
6. **Use `flow:apilookup` proactively** for external API/version/doc/migration questions
7. **Flow specs/plans live in `.agents/specs/`** - never use `docs/superpowers/specs/`
8. **Local commits** - Never push automatically
9. **Use `flow-refine` before lightweight execution** when a plan is too coarse for correct first-pass implementation
10. **Preserve subagent context** - pass spec/PRD, patterns, knowledge, learnings, affected files, and verification requirements when delegating
