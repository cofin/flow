---
name: flow
description: "Context-driven development workflow with Beads integration. Auto-activates when .agent/ directory exists. Provides spec-first planning, TDD workflow, knowledge capture, and cross-session memory via Beads."
---

# Flow - Context-Driven Development

## Auto-Activation

This skill activates when:
- `.agent/` directory exists in the project root
- User mentions "flow", "track", "spec", "plan", or "implement"
- User invokes `/flow-*` commands

## Core Concepts

### Tracks (formerly PRDs)
A track is a logical unit of work (feature or bug fix). Each track has:
- **ID format**: `shortname_YYYYMMDD` (e.g., `auth_20260124`)
- **Location**: `.agent/specs/{track_id}/`
- **Files**: spec.md, plan.md, metadata.json, learnings.md

### Status Markers
- `[ ]` - Pending/New
- `[~]` - In Progress
- `[x]` - Completed (with commit SHA: `[x] abc1234`)
- `[!]` - Blocked (logged in blockers.md)
- `[-]` - Skipped (logged in skipped.md)

### Beads Integration (Required)
Flow requires Beads for persistent cross-session memory:
- Each track becomes a Beads epic
- Tasks sync bidirectionally
- Notes survive context compaction
- Run `bd prime` at session start

## Universal File Resolution Protocol

**To locate files within Flow context:**

1. **Project Index**: `.agent/index.md`
2. **Specs Registry**: `.agent/prds.md` (or tracks.md)
3. **Track Index**: `.agent/specs/{track_id}/index.md`

**Default Paths:**
- Product: `.agent/product.md`
- Tech Stack: `.agent/tech-stack.md`
- Workflow: `.agent/workflow.md`
- Patterns: `.agent/patterns.md`
- Beads Config: `.agent/beads.json`

## Workflow Commands

| Claude Code | Gemini CLI | Purpose |
|-------------|------------|---------|
| `/flow-setup` | `/flow:setup` | Initialize project with context files |
| `/flow-newtrack` | `/flow:newtrack` | Create feature/bug track |
| `/flow-implement` | `/flow:implement` | Execute tasks (TDD workflow) |
| `/flow-status` | `/flow:status` | Display progress overview |
| `/flow-revert` | `/flow:revert` | Git-aware revert |
| `/flow-validate` | `/flow:validate` | Validate project integrity |
| `/flow-block` | `/flow:block` | Mark task blocked |
| `/flow-skip` | `/flow:skip` | Skip task with reason |
| `/flow-revise` | `/flow:revise` | Update spec/plan mid-work |
| `/flow-archive` | `/flow:archive` | Archive completed track |
| `/flow-export` | `/flow:export` | Generate summary export |
| `/flow-handoff` | `/flow:handoff` | Context handoff for sections |
| `/flow-refresh` | `/flow:refresh` | Sync context with codebase |
| `/flow-formula` | `/flow:formula` | Manage Beads templates |
| `/flow-wisp` | `/flow:wisp` | Ephemeral exploration track |
| `/flow-distill` | `/flow:distill` | Extract reusable template |

## Task Workflow (TDD)

1. **Select task** from plan.md (or `bd ready`)
2. **Mark `[~]`** in progress
3. **Write failing tests** (Red phase) - CRITICAL: confirm failure first
4. **Implement** to pass (Green phase)
5. **Refactor** with test safety
6. **Verify coverage** (>80% target)
7. **Commit** with format: `<type>(<scope>): <description>`
8. **Attach git notes** with task summary
9. **Record SHA** in plan.md
10. **Sync to Beads**: `bd close {id} --note "commit: {sha}"`

## Knowledge Flywheel

1. **Implement** - Discover patterns while coding
2. **Log** - Record in track's `learnings.md`
3. **Sync** - Auto-sync to Beads notes
4. **Elevate** - At phase/track completion, elevate to `patterns.md`
5. **Prime** - New tracks inherit from `patterns.md`

## Phase Completion Protocol

When a phase completes:
1. Run full test suite
2. Verify coverage for phase files
3. Propose manual verification steps
4. Await user confirmation
5. Create checkpoint commit
6. Attach verification report as git note
7. Record checkpoint SHA in plan.md

## Proactive Behaviors

When Flow skill is active:
- Check for resume state at session start
- Offer to run `bd prime` for context
- Prompt for learnings capture after tasks
- Suggest pattern elevation at phase completion
- Warn if tech-stack changes without documentation

## References

- `references/workflows.md` - Detailed command workflows
- `references/structure.md` - Directory structure reference
- `references/beads-integration.md` - Beads session protocols
- `references/learnings-system.md` - Knowledge capture patterns
