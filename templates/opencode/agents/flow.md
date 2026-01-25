# Flow Agent

You are working in a project using the **Flow Framework** for context-driven development.

## Key Concepts

### Tracks
A track is a logical unit of work (feature, bug fix, refactor). Each track has:
- **Unique ID format:** `shortname_YYYYMMDD` (e.g., `user-auth_20260124`)
- **Status markers:** `[ ]` pending, `[~]` in progress, `[x]` completed, `[!]` blocked, `[-]` skipped
- **Own directory** at `.agent/specs/{track_id}/` with spec, plan, metadata, learnings

### Beads Integration
Beads provides persistent cross-session memory:
```bash
bd init --stealth          # Initialize (stealth mode)
bd ready                   # Show tasks ready to work on
bd update <id> --status in_progress  # Start task
bd close <id> --reason "..." # Complete task
bd prime                   # Load context for session
```

### Task Workflow (TDD)
1. Select task from plan.md (or use `bd ready`)
2. Mark `[~]` in progress → `bd update <id> --status in_progress`
3. **Write failing tests** (Red)
4. **Implement to pass** (Green)
5. **Refactor** while green
6. Commit with conventional format
7. Mark `[x]` complete → `bd close <id> --reason "commit: <sha>"`
8. Log learnings in learnings.md

### Directory Structure
```
.agent/
├── product.md           # Product vision
├── tech-stack.md        # Technology choices
├── workflow.md          # Development workflow
├── patterns.md          # Consolidated learnings
├── tracks.md            # Master track list
└── specs/{track_id}/    # Track-specific files
    ├── spec.md          # Requirements
    ├── plan.md          # Phased task list
    └── learnings.md     # Patterns discovered
```

## Flow Commands
- `/flow:setup` - Initialize project
- `/flow:prd` - Create new track
- `/flow:implement` - Execute tasks from plan
- `/flow:status` - Display progress overview
- `/flow:block` - Mark task as blocked
- `/flow:skip` - Skip task with justification
- `/flow:archive` - Archive completed track

## Critical Rules
1. **Read patterns.md** before starting work
2. **Log learnings** as you discover them
3. **Use TDD** - tests first, then implementation
4. **Beads sync** - Keep task status in sync
5. **Local commits** - Never push automatically
