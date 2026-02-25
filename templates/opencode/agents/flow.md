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
br init --stealth          # Initialize (stealth mode)
br ready                   # Show tasks ready to work on
br blocked                 # Show blocked tasks
br update <id> --status in_progress  # Start task
br close <id> --reason "..." # Complete task
br prime                   # Load context for session
br show <id> --children --json  # Export epic with tasks
br compact                 # Compact database
```

### Task Workflow (TDD) - Beads-First
1. **Select task** from `br ready` (Beads is source of truth)
2. **Mark in progress** → `br update <id> --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Commit with conventional format
7. **Sync to Beads** → `br close <id> --reason "commit: <sha>"`
8. Log learnings in learnings.md

**CRITICAL:** Never write `[x]` or `[~]` markers to spec.md. Beads is the source of truth.

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
- `/flow:setup` - Initialize project
- `/flow:prd` - Create PRD (Saga)
- `/flow:plan` - Plan single flow with unified spec.md
- `/flow:sync` - Export Beads state to spec.md
- `/flow:implement` - Execute tasks from Beads
- `/flow:status` - Display progress overview
- `/flow:block` - Mark task as blocked
- `/flow:skip` - Skip task with justification
- `/flow:archive` - Archive completed flow

## Critical Rules
1. **Read patterns.md** before starting work
2. **Log learnings** as you discover them
3. **Use TDD** - tests first, then implementation
4. **Beads is source of truth** - Never write markers to spec.md
5. **Local commits** - Never push automatically
