---
description: Execute tasks from plan (context-aware)
---

# Flow Implement

Execute tasks from a flow's plan using TDD workflow.

**CRITICAL:** `/flow-implement` is the TDD engine. It uses local task files under `.agents/bundles/specs/{flow_id}/tasks/` as the authority for what to work on next. Every discovery and decision MUST be noted directly inside the active task markdown file.

## Usage

`/flow-implement {flow_id}` or `/flow-implement` (uses current flow)

## Phase 1: Load Context

**PROTOCOL: Load Flow, Project, and Parent Context.**

1. **Resolve Flow:** Use the argument, or auto-discover by scanning `.agents/bundles/specs/*/spec.md` frontmatter for `state: active` (or `planned`).
2. **Read Artifacts:**
    - `.agents/bundles/specs/{flow_id}/spec.md` (unified spec+plan)
    - `.agents/bundles/specs/{flow_id}/learnings.md`
3. **Read Project Context:** `.agents/bundles/knowledge/patterns/patterns.md` and `.agents/bundles/knowledge/workflow/workflow.md`
4. **Read Parent Context:**
    - Check if this flow has a parent PRD/Saga (a roadmap spec bundle referencing this flow).
    - If yes, read the roadmap `spec.md` under `.agents/bundles/specs/<prd_id>/`.

**CRITICAL:** Before starting, check whether `.agents/` artifacts are ignored by `.gitignore`, `.git/info/exclude`, or global git ignores. If they are ignored, do NOT commit those artifacts. Update them on disk only.

## Phase 2: Select Task (Task-Files-First)

**CRITICAL:** Task files are the source of truth for task status. Do NOT hand-edit spec.md markers.

1. **Scan**: Scan task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
2. **Parse & Resolve Dependencies**: Parse the YAML frontmatter of each task. A task is ready if its `state` is `open` and all dependencies listed in `depends_on` have `state` set to `closed`.
3. **Select**: Sort the ready tasks by priority (`P0` > `P1` > `P2` > `P3` > `P4`), then select the first one.
4. **Claim**: Update the selected task's frontmatter: set `state: in_progress` and `updated_at` to the current ISO-8601 timestamp.

If no task files exist yet, run `/flow-sync` first to scaffold them from the `spec.md` Implementation Plan checklist.

## Phase 3: Task Execution (TDD)

### 3.0 Subagent Execution Preference

If `superpowers:subagent-driven-development` is available in this harness, invoke it before implementation and use its implementation-subagent workflow for task execution and review checkpoints.

- Before delegating, ask: "Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?"
- If not, invoke `flow-refine` first and update the plan before dispatch.
- Preserve subagent context by passing the relevant spec or PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements.
- Do not silently descope if the task is larger than expected. Refine it or ask the user how to prioritize.

Fallback: if the skill is unavailable, continue with the single-agent TDD workflow below.
In fallback mode, preserve the same task context bundle, refine coarse tasks first, and keep the same review checkpoints.

### 3.0.1 API Lookup Preference

If task execution depends on external framework/API behavior, versions, migrations, or release changes, invoke `flow:apilookup` before implementation decisions.

### 3.1 Investigate & Note

Trace the code and append findings to the task markdown file under a `## Notes & Discoveries` heading, prefixed with a timestamp:

```markdown
## Notes & Discoveries
- [2026-08-11 12:00] Discovered existing validator covers this case.
```

### 3.2 Red Phase - Write Failing Tests

1. Create/update test file
2. Write tests that define expected behavior
3. Run the canonical test command from `.agents/bundles/knowledge/workflow/workflow.md` when present to confirm they fail for the right reason

### 3.3 Green Phase - Implement

1. Write minimum code to pass tests
2. Run tests until green
3. Make the minimum targeted change set needed for the task. Do not add unrelated cleanup without approval.

### 3.4 Refactor Phase

1. Clean up while tests pass
2. Apply patterns from `knowledge/patterns/patterns.md`

### 3.5 Verify Coverage

Target: 80% minimum
Prefer the repo's canonical verification or coverage command from `.agents/bundles/knowledge/workflow/workflow.md` when present.

## Phase 4: Commit

```bash
git add <implementation_files> <non_ignored_context_files>
git commit -m "<type>(<scope>): <description>"
```

Retrieve the commit SHA.

Never use `git add -A` or `git add -f` for Flow work. If a file is ignored, leave it local-only.
Never force-add ignored Flow artifacts.

## Phase 5: Close Task & Sync

1. **Close Task**: Update the task file's frontmatter: set `state: closed`, `commit: <sha>`, and `updated_at` to the current ISO-8601 timestamp.
2. **Markdown Sync**: Do NOT hand-edit markers in spec.md. Run `/flow-sync` so the `spec.md` checklist markers match task-file state (closed tasks render as `[x]` with the commit SHA appended).
3. **Log Learnings**: Record discoveries in the task file's `## Notes & Discoveries` section as you go; promote durable patterns to `.agents/bundles/specs/{flow_id}/learnings.md`.

## Phase 6: Continue or Stop

After each task:
> Task complete. Continue to next task? [Y/n]

At phase completion: run the full test suite, check coverage requirements, and ensure all changes are committed.

## Critical Rules

1. **TDD ALWAYS** - Write tests before implementation
2. **SMALL COMMITS** - One task = one commit
3. **TASK FILES ARE SOURCE OF TRUTH** - Keep task status and commit SHAs in the task files' frontmatter; never hand-edit spec.md markers
4. **NOTE IMMEDIATELY** - Record discoveries directly into the task file's `## Notes & Discoveries` section
5. **PREFER SUPERPOWERS SUBAGENTS** - Use `superpowers:subagent-driven-development` when available, otherwise follow the same protocol inline
6. **PREFER API LOOKUP** - Use `flow:apilookup` for external API/version/doc questions before coding
7. **LOCAL ONLY** - Never push automatically
8. **USE THE READY QUEUE** - Select the next task by scanning task files for open tasks with closed dependencies
9. **USE CANONICAL REPO COMMANDS** - Prefer the commands documented in `knowledge/workflow/workflow.md`
10. **BE COLLABORATIVE** - Describe unrelated blockers factually and constructively; never use dismissive ownership-deflecting language
