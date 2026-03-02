---
description: Context-driven development with Beads integration
mode: subagent
tools:
  write: true
  edit: true
  bash: true
---

# Flow Agent

You are working in a project using the **Flow Framework** for context-driven development.

## Key Concepts

### Flows
A flow is a logical unit of work (feature, bug fix, refactor). Each flow has:
- **Unique ID format:** `shortname_YYYYMMDD` (e.g., `user-auth_20260124`)
- **Status markers:** `[ ]` pending, `[~]` in progress, `[x]` completed, `[!]` blocked, `[-]` skipped
- **Own directory** at `.agent/specs/{flow_id}/` with unified spec, metadata, learnings

### Beads Integration (Source of Truth)
Beads provides persistent cross-session memory:
```bash
br init --prefix <project_name_slug> # Initialize Beads
br status                  # Workspace overview
br ready                   # Show tasks ready to work on
br list --status in_progress  # Resume active work
br blocked                 # Show blocked tasks
br update <id> --status in_progress  # Start task
br close <id> --reason "..." # Complete task
br show <id> --format json  # Export epic with tasks
```

### Task Workflow (TDD) - Beads-First
1. **Select task** from `br ready` (Beads is source of truth)
2. **Mark in progress** → `br update <id> --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Commit with conventional format
7. **Sync to Beads** → `br close <id> --reason "commit: <sha>"`
8. Markdown synced automatically via git pre-commit hook.
9. Log learnings in learnings.md

**CRITICAL:** Do not manually edit spec.md markers. Beads state is exported automatically upon commit.

### Directory Structure
```
.agent/
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
- `/flow:setup` - Initialize project with context files, Beads, and first flow
- `/flow:prd` - Analyze goals and generate Master Roadmap (Sagas)
- `/flow:plan` - Create unified spec.md for a single Flow
- `/flow:sync` - Export Beads state to spec.md (source of truth sync)
- `/flow:research` - Conduct pre-PRD research
- `/flow:docs` - Five-phase documentation workflow
- `/flow:implement` - Execute tasks from plan (context-aware)
- `/flow:status` - Display progress overview with Beads status
- `/flow:revert` - Git-aware revert of flows, phases, or tasks
- `/flow:validate` - Validate project integrity and fix issues
- `/flow:block` - Mark task as blocked with reason
- `/flow:skip` - Skip current task with justification
- `/flow:revise` - Update spec/plan when implementation reveals issues
- `/flow:archive` - Archive completed flows + elevate patterns
- `/flow:export` - Generate project summary export
- `/flow:handoff` - Create context handoff for session transfer
- `/flow:refresh` - Sync context docs with current codebase state
- `/flow:formula` - List and manage flow templates
- `/flow:wisp` - Create ephemeral exploration flow (no audit trail)
- `/flow:distill` - Extract reusable template from completed flow

## Critical Rules
1. **Read patterns.md** before starting work
2. **Log learnings** as you discover them
3. **Use TDD** - tests first, then implementation
4. **Beads is source of truth** - Never write markers to spec.md
5. **Local commits** - Never push automatically
