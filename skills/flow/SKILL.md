---
name: flow
description: "Context-driven development workflow with Beads integration. Auto-activates when .agent/ directory exists. Provides spec-first planning, TDD workflow, knowledge capture, and cross-session memory via Beads."
---

# Flow - Context-Driven Development

## Auto-Activation

This skill activates when:
- `.agent/` directory exists in the project root
- User mentions "flow", "spec", "plan", or "implement"
- User invokes `/flow-*` commands

## Core Concepts

### Flows (formerly PRDs)
A flow is a logical unit of work (feature or bug fix). Each flow has:
- **ID format**: `shortname_YYYYMMDD` (e.g., `auth_20260124`)
- **Location**: `.agent/specs/{flow_id}/`
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

1. **Project Index**: `.agent/index.md`
2. **Flow Registry**: `.agent/flows.md`
3. **Flow Index**: `.agent/specs/{flow_id}/index.md`

**Default Paths:**
- Product: `.agent/product.md`
- Tech Stack: `.agent/tech-stack.md`
- Workflow: `.agent/workflow.md`
- Patterns: `.agent/patterns.md`
- Knowledge Index: `.agent/knowledge/index.md`
- Knowledge Entries: `.agent/knowledge/{flow_id}.md`
- Beads Config: `.agent/beads.json`

## Workflow Commands

| Claude Code | Gemini CLI | Purpose |
|-------------|------------|---------|
| `/flow-setup` | `/flow:setup` | Initialize project with context files |
| `/flow-prd` | `/flow:prd` | Create feature/bug flow |
| `/flow-plan` | `/flow:plan` | Plan flow with unified spec.md |
| `/flow-sync` | `/flow:sync` | Sync Beads state to spec.md |
| `/flow-implement` | `/flow:implement` | Execute tasks (TDD workflow) |
| `/flow-status` | `/flow:status` | Display progress overview |
| `/flow-revert` | `/flow:revert` | Git-aware revert |
| `/flow-validate` | `/flow:validate` | Validate project integrity |
| `/flow-block` | `/flow:block` | Mark task blocked |
| `/flow-skip` | `/flow:skip` | Skip task with reason |
| `/flow-revise` | `/flow:revise` | Update spec/plan mid-work |
| `/flow-archive` | `/flow:archive` | Archive completed flow |
| `/flow-export` | `/flow:export` | Generate summary export |
| `/flow-handoff` | `/flow:handoff` | Context handoff for sessions |
| `/flow-refresh` | `/flow:refresh` | Sync context with codebase |
| `/flow-formula` | `/flow:formula` | Manage flow templates |
| `/flow-wisp` | `/flow:wisp` | Ephemeral exploration flow |
| `/flow-distill` | `/flow:distill` | Extract reusable template |
| `/flow-docs` | `/flow:docs` | Documentation workflow |

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
10. **Sync to markdown**: run `/flow-sync` (MANDATORY — keeps spec.md readable)

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers to spec.md. Beads is the source of truth. After ANY Beads state change, agents MUST run `/flow-sync` to update spec.md.

## Knowledge Flywheel (Three-Tier)

1. **Capture** - After each task, append learnings to flow's `learnings.md`
2. **Sync** - Auto-sync to Beads notes
3. **Elevate** - At phase/flow completion, move reusable patterns to `patterns.md`
4. **Extract** - At archive, persist full learnings to `knowledge/{flow_id}.md`
5. **Inherit** - New flows read `patterns.md` + scan `knowledge/index.md`

## Phase Completion Protocol

When a phase completes:
1. Run full test suite
2. Verify coverage for phase files
3. Propose manual verification steps
4. Await user confirmation
5. Create checkpoint commit
6. Attach verification report as git note
7. Record checkpoint in Beads: `br comments add {epic_id} "Phase {N} checkpoint: {sha}"`
8. Sync to markdown: run `/flow-sync` (MANDATORY)

## Proactive Behaviors

When Flow skill is active:
- Check for resume state at session start
- Run `br status` and `br ready` for context
- Scan `knowledge/index.md` for relevant past learnings when starting a new flow
- Prompt for learnings capture after tasks
- Suggest pattern elevation at phase completion
- Warn if tech-stack changes without documentation
- Enforce mandatory `/flow-sync` after any Beads state change

## References

- `references/workflows.md` - Detailed command workflows
- `references/structure.md` - Directory structure reference
- `references/beads-integration.md` - Beads session protocols
- `references/learnings-system.md` - Knowledge capture patterns

## Official References

- https://github.com/cofin/flow
- https://raw.githubusercontent.com/cofin/flow/main/README.md
- https://github.com/Dicklesworthstone/beads_rust
- https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/README.md
- https://docs.rs/beads_rust/latest/beads_rust/
- https://geminicli.com/docs/extensions/reference/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
