---
name: flow
description: "Context-driven dev workflow. Use when: /flow:plan, /flow:prd, editing spec.md, .agents/ directory exists, beads, cross-session memory, spec-first planning, or TDD workflow orchestration."
---

# Flow - Context-Driven Development

## Auto-Activation

This skill activates when:

- `.agents/` directory exists in the project root
- User mentions "flow", "spec", "plan", or "implement"
- User invokes `/flow:*` commands

## Core Concepts

### Flows (formerly PRDs)

A flow is a logical unit of work (feature or bug fix). Each flow has:

- **ID format**: `shortname` (e.g., `auth`)
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
- Knowledge Base: `.agents/knowledge/`
- Knowledge Index: `.agents/knowledge/index.md`
- Beads Config: `.agents/beads.json`

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
| `/flow-revise` | `/flow:revise` | Update spec/plan mid-work |
| `/flow-archive` | `/flow:archive` | Archive completed flow |
| `/flow-task` | `/flow:task` | Ephemeral exploration task |
| `/flow-docs` | `/flow:docs` | Documentation workflow |
| `/flow-refresh` | `/flow:refresh` | Sync context with codebase |

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
10. **Sync to markdown**: run `/flow:sync` to update spec.md.

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers to spec.md manually. Beads is the source of truth — after ANY Beads state change, you MUST run `/flow:sync` to keep spec.md in sync.

## Knowledge Flywheel

1. **Capture** - After each task, append learnings to flow's `learnings.md`
2. **Sync** - Auto-sync to Beads notes
3. **Elevate** - At phase/flow completion, move reusable patterns to `patterns.md`
4. **Synthesize** - During sync and archive, integrate learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/`.
5. **Inherit** - New flows read `patterns.md` + scan `.agents/knowledge/` chapters.

## Phase Completion Protocol

When a phase completes:

1. Run full test suite
2. Verify coverage for phase files
3. Propose manual verification steps
4. Await user confirmation
5. Create checkpoint commit
6. Attach verification report as git note
7. Record checkpoint in Beads: `br comments add {epic_id} "Phase {N} checkpoint: {sha}"`
8. Sync to markdown: run `/flow:sync` (MANDATORY)

## Proactive Behaviors

When Flow skill is active:

- Check for resume state at session start
- Run `br status` and `br ready` for context
- Scan `knowledge/index.md` for relevant past learnings when starting a new flow
- Prompt for learnings capture after tasks
- Suggest pattern elevation at phase completion
- Warn if tech-stack changes without documentation
- Enforce mandatory `/flow:sync` after any Beads state change

## References Index

For detailed instructions and directives for specific flow commands, refer to the following documents in `references/`:

- **[Setup](references/setup.md)** - `/flow:setup`
- **[PRD](references/prd.md)** - `/flow:prd`
- **[Plan](references/plan.md)** - `/flow:plan`
- **[Implement](references/implement.md)** - `/flow:implement`
- **[Sync](references/sync.md)** - `/flow:sync`
- **[Status](references/status.md)** - `/flow:status`
- **[Revert](references/revert.md)** - `/flow:revert`
- **[Validate](references/validate.md)** - `/flow:validate`
- **[Revise](references/revise.md)** - `/flow:revise`
- **[Archive](references/archive.md)** - `/flow:archive`
- **[Task](references/task.md)** - `/flow:task`
- **[Docs](references/docs.md)** - `/flow:docs`
- **[Research](references/research.md)** - `/flow:research`
- **[Refresh](references/refresh.md)** - `/flow:refresh`

## Official References

- <https://github.com/cofin/flow>
- <https://raw.githubusercontent.com/cofin/flow/main/README.md>
- <https://github.com/Dicklesworthstone/beads_rust>
- <https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/README.md>
- <https://docs.rs/beads_rust/latest/beads_rust/>
- <https://geminicli.com/docs/extensions/reference/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
