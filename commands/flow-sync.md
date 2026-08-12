---
description: Synchronize flow specifications and task files (OKF bundle)
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Sync

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Syncing active flow state on disk: **$ARGUMENTS**

## The Sync Mandate

**CRITICAL:** `/flow:sync` reconciles the markdown task checklist in `spec.md` with the individual task files under `.agents/bundles/specs/<flow_id>/tasks/`.

---

## Phase 1: Reconcile Task Checklists and Task Files

As the AI agent, you must execute the reconciliation algorithm directly using your file tools:

1. **Locate Active Flow**:
   - Scan `.agents/bundles/specs/` to find the active flow (look for a spec.md whose frontmatter has `state: active`). If a flow ID argument is provided, target that flow ID.
2. **Read Spec File**:
   - Read `.agents/bundles/specs/{flow_id}/spec.md`. Extract `flow_id` from the YAML frontmatter.
3. **Parse Tasks**:
   - Find all task checklist lines in the spec body using regex. A task checklist line matches:
     `^(\s*-\s*\[([ ~x!-])\]\s*Task\s+([a-zA-Z0-9._-]+)\s*:\s*)(.*?)(?:\s*\[([a-fA-F0-9]{7,})\])?$`
     Where:
     - Group 2 is the status marker: ` ` (open), `~` (in_progress), `x` (closed), `!` (blocked), `-` (skipped).
     - Group 3 is the Task ID (e.g. `1.1`).
     - Group 4 is the task description.
     - Group 5 is the optional commit SHA.
4. **Reconcile Tasks**:
   - For each parsed task:
     - Check if `.agents/bundles/specs/{flow_id}/tasks/{task_id}.md` exists.
     - **If it does NOT exist**: Scaffold it with default YAML frontmatter:

       ```yaml
       ---
       type: Task
       id: {flow_id}:{task_id}
       title: {task_description}
       state: open
       depends_on: []
       files: []
       tests: []
       created_at: <current_iso_timestamp>
       updated_at: <current_iso_timestamp>
       commit: null
       ---
       ```

     - **If it DOES exist**: Read its YAML frontmatter. Check the `state` field:
       - `open` -> Map checklist marker to `[ ]`
       - `in_progress` -> Map checklist marker to `[~]`
       - `closed` -> Map checklist marker to `[x]` (and append `[<commit_sha>]` using the `commit` value from frontmatter)
       - `blocked` -> Map checklist marker to `[!]`
       - `skipped` -> Map checklist marker to `[-]`
5. **Update Spec File**:
   - Rewrite `.agents/bundles/specs/{flow_id}/spec.md` with the updated checklist markers and commit SHAs, preserving the rest of the file.

## Phase 2: Integrity Validation

Execute the repository integrity checks manually:

1. **Verify Orphaned Task Files**:
   - Scan `.agents/bundles/specs/{flow_id}/tasks/*.md`.
   - Ensure that every task file has a corresponding checklist task in `.agents/bundles/specs/{flow_id}/spec.md`.
   - If any task file is orphaned (not defined in `spec.md`), report a validation violation.
2. **Verify File and Test Paths**:
   - For each task file in state `closed`, read `files:` and `tests:` arrays.
   - Verify that all listed paths exist in the workspace. If any path does not exist, report a validation violation.
3. **Verify Markdown Links**:
   - Scan all relative links in `spec.md`.
   - Verify that all relative links resolve to existing files or directories in the workspace.

## Phase 3: Context Drift Check

Verify if any core project configuration or dependencies have drifted since the last execution:

1. Compare dependency files (`package.json`, `pyproject.toml`, etc.) with `.agents/tech-stack.md`.
2. Inspect workflow drift across `Makefile`, `justfile`, `tasks.json`, etc.
3. If drift is detected, report to the developer and request validation of `.agents/workflow.md`.
