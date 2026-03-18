---
name: flow
description: "Context-driven development workflow with Beads integration. Auto-activates when .agents/ directory exists. Provides spec-first planning, TDD workflow, knowledge capture, and cross-session memory via Beads."
---

# Flow - Context-Driven Development

## Auto-Activation

This skill activates when:
- `.agents/` directory exists in the project root
- User mentions "flow", "spec", "plan", or "implement"
- User invokes `/flow-*` commands

## Core Concepts

### Flows (formerly PRDs)
A flow is a logical unit of work (feature or bug fix). Each flow has:
- **ID format**: `shortname_YYYYMMDD` (e.g., `auth_20260124`)
- **Location**: `.agents/specs/{flow_id}/`
- **Files**: spec.md (unified spec+plan), metadata.json, learnings.md

### Status Markers
- `[ ]` - Pending/New
- `[~]` - In Progress
- `[x]` - Completed (with commit SHA: `[x] abc1234`)
- `[!]` - Blocked (logged in blockers.md)
- `[-]` - Skipped (logged in skipped.md)

### Beads Integration (Required)
Flow requires Beads for persistent cross-session memory:
- Each flow becomes a Beads epic
- Tasks sync bidirectionally
- Notes survive context compaction
- Run `br status` + `br ready` at session start

## Universal File Resolution Protocol

**To locate files within Flow context:**

1. **Project Index**: `.agents/index.md`
2. **Flow Registry**: `.agents/flows.md`
3. **Flow Index**: `.agents/specs/{flow_id}/index.md`

**Default Paths:**
- Product: `.agents/product.md`
- Tech Stack: `.agents/tech-stack.md`
- Workflow: `.agents/workflow.md`
- Patterns: `.agents/patterns.md`
- Beads Config: `.agents/beads.json`

## Workflow Commands

| Command | Purpose |
|---------|---------|
| `flow-setup` | Initialize project with context files |
| `flow-prd` | Create feature/bug flow |
| `flow-plan` | Plan flow with unified spec.md |
| `flow-sync` | Sync Beads state to spec.md |
| `flow-implement` | Execute tasks (TDD workflow) |
| `flow-status` | Display progress overview |
| `flow-revert` | Git-aware revert |
| `flow-validate` | Validate project integrity |
| `flow-block` | Mark task blocked |
| `flow-skip` | Skip task with reason |
| `flow-revise` | Update spec/plan mid-work |
| `flow-archive` | Archive completed flow |
| `flow-export` | Generate summary export |
| `flow-handoff` | Context handoff for sessions |
| `flow-refresh` | Sync context with codebase |
| `flow-formula` | Manage flow templates |
| `flow-wisp` | Ephemeral exploration flow |
| `flow-distill` | Extract reusable template |
| `flow-docs` | Documentation workflow |
| `flow-research` | Conduct pre-PRD research |

## Task Workflow (TDD) - Beads-First

1. **Select task** from `br ready` (Beads is source of truth)
2. **Mark in progress**: `br update {id} --status in_progress`
3. **Write failing tests** (Red phase) - CRITICAL: confirm failure first
4. **Implement** to pass (Green phase)
5. **Refactor** with test safety
6. **Verify coverage** (>80% target)
7. **Commit** with format: `<type>(<scope>): <description>`
8. **Attach git notes** with task summary
9. **Sync to Beads**: `br close {id} --reason "commit: {sha}"`

**CRITICAL:** Never write `[x]` or `[~]` markers to spec.md. Beads is the source of truth.

## Knowledge Flywheel

1. **Implement** - Discover patterns while coding
2. **Log** - Record in flow's `learnings.md`
3. **Sync** - Auto-sync to Beads notes
4. **Elevate** - At phase/flow completion, elevate to `patterns.md`
5. **Prime** - New flows inherit from `patterns.md`

## Phase Completion Protocol

When a phase completes:
1. Run full test suite
2. Verify coverage for phase files
3. Propose manual verification steps
4. Await user confirmation
5. Create checkpoint commit
6. Attach verification report as git note
7. Record checkpoint in Beads: `br comments add {epic_id} "Phase {N} checkpoint: {sha}"`

## Proactive Behaviors

When Flow skill is active:
- Check for resume state at session start
- Run `br status` and `br ready` for context
- Prompt for learnings capture after tasks
- Suggest pattern elevation at phase completion
- Warn if tech-stack changes without documentation
