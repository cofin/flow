---
description: Execute tasks from plan (context-aware)
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch
---

# Flow Implement

> Lifecycle skill: use `flow-execution` through the `flow` router.

Implementing flow: **$ARGUMENTS**

## The Executor Mandate

**CRITICAL:** `/flow:implement` is the TDD engine. It uses local task files under `.agents/bundles/specs/<flow_id>/tasks/` as the authority for what to work on next. Every discovery and decision MUST be noted directly inside the active task markdown file.

---

## Phase 0: Environment Detection

**PROTOCOL: Check hook context for environment metadata.**

1. **Check Hook Context:** Scan `<hook_context>` for `## Flow Environment Context` to resolve the flow root.

---

## Phase 2: Task Selection

**PROTOCOL: Scan and select the next pending task from the filesystem.**

1. **Scan**: Scan task files under `.agents/bundles/specs/<flow_id>/tasks/*.md`.
2. **Parse & Resolve Dependencies**: Parse the YAML frontmatter of each task. A task is ready if its `state` is `"open"` and all dependencies listed in `depends_on` have `state` set to `"closed"`.
3. **Select**: Sort the ready tasks by priority (`P0` > `P1` > `P2` > `P3` > `P4`), then select the first one.
4. **Claim**: Update the selected task's frontmatter: set `state: in_progress` and `updated_at` to the current ISO-8601 timestamp.

---

## Phase 3: Task Execution Loop (TDD)

For the selected task:

1. **Investigate & Note**: Trace the code and append findings to the task markdown file under a `## Notes & Discoveries` heading, prefixed with a timestamp.
2. **Write Failing Tests (Red Phase)**: Write unit tests to confirm failure for the right reason.
3. **Implement (Green Phase)**: Write minimal code to pass the tests.
4. **Refactor**: Clean up code and test structure while remaining green.
5. **Commit**: Git commit the changes: `<type>(<scope>): <description>`. Retrieve the commit SHA.
6. **Close Task**: Update the task's frontmatter: set `state: closed`, `commit: <sha>`, and `updated_at` to the current ISO-8601 timestamp.

---

## Phase 4: Phase Completion Protocol

1. **Verify**: Run the full test suite and check coverage requirements.
2. **Commit**: Ensure all changes are committed.

---

## Critical Rules

1. **TDD MANDATORY** - Failing test first.
2. **TASK FILES AS SOURCE OF TRUTH** - Keep task status and SHAs in the task files frontmatter.
3. **NOTE IMMEDIATELY** - Record discoveries directly into the task file's `## Notes & Discoveries` section.
4. **NO DIRECT SPEC EDITS** - Status markers in `spec.md` should only be updated automatically or via synchronization.
