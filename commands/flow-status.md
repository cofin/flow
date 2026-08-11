---
description: Display progress overview dashboard for active flows
allowed-tools: Read, Glob, Grep, Bash
---

# Flow Status

> Lifecycle skill: use `flow-sync-status` through the `flow` router.

Displaying progress dashboard for active flows.

## The Dashboard Mandate

**CRITICAL:** `/flow:status` is the developer dashboard. It aggregates status metrics and notes from local task markdown files under `.agents/bundles/specs/*/tasks/*.md`.

---

## Phase 1: Aggregate Flow Status Dashboard

As the AI agent, you must execute the status dashboard aggregation directly:

1. **Scan Specs Directory**:
   - List all directories under `.agents/bundles/specs/`.
   - For each directory, read `spec.md` and check the YAML frontmatter.
   - Filter to find specs that are in status `planned` or `active` (and read their `flow_id`).

2. **Scan Tasks and Extract Notes**:
   - For each active/planned flow:
     * List all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`.
     * Read each task file, extract `status` (open, in_progress, closed, blocked, skipped), `depends_on`, and task notes.
     * Task notes are extracted from the `## Notes & Discoveries` heading to the next heading or end of file. Extract the note lines (e.g. `- [timestamp] note text`).
     * Count metrics: `total_tasks`, `closed_count`, `skipped_count`. Calculate progress percentage: `closed_count / (total_tasks - skipped_count) * 100.0` (if denominator > 0).

3. **Resolve Queues**:
   - Sort tasks into queues:
     * **Active Tasks**: task status is `in_progress`.
     * **Ready Queue**: task status is `open` AND all dependency tasks (in `depends_on`) are in status `closed`.
     * **Blocked Queue**: task status is `blocked`, OR task status is `open` and at least one dependency is NOT `closed`.

4. **Sort and Format Recent Notes**:
   - Gather all extracted notes, sort them by timestamp descending, and take the 5 most recent notes.

5. **Print Status Dashboard**:
   - Format and print the consolidated status dashboard:
     ```text
     ================================================================================
                                DEVELOPER STATUS DASHBOARD                           
     ================================================================================
     Active Flows: {active_flows_count}

     Flow: {flow_id} [██████████░░░░░░░░░░] {progress}%
       Tasks: {closed_count}/{total_tasks} closed (skipped: {skipped_count})
       Active Task(s): {active_tasks} (if any)
       Ready Queue (next up): {ready_queue} (if any)
       Blocked Queue: {blocked_queue} (if any)

     --------------------------------------------------------------------------------
     Recent Notes & Discoveries:
       [{timestamp}] ({task_id}): {note_text}
     --------------------------------------------------------------------------------

     Next Recommendations:
       [{flow_id}]: Continue working on active task(s): {active_tasks}
       [{flow_id}]: Claim and start next ready task: {first_ready_task}
     ================================================================================
     ```

If the dashboard shows any out-of-sync indicators or if you have recently modified task files directly, run `/flow:sync` to reconcile them first.
