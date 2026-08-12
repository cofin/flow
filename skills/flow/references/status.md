# Flow Status Reference

Displays the developer dashboard, including progress metrics, ready queues, blocked queues, and recent discoveries for all active flows.

---

## Phase 1: Dynamic Discovery

Active flows are discovered by scanning the specs directory:

1. Scan `.agents/bundles/specs/*/spec.md`.
2. Parse the frontmatter of each spec.
3. Filter for active flows (`state` is `planned` or `active`).

---

## Phase 2: Status Aggregation

For each active flow, scan all task files under `tasks/*.md` to collect metadata:

1. **Calculate Metrics**:
   - Total tasks = count of task files.
   - Closed tasks = count of tasks with `state: closed`.
   - Skipped tasks = count of tasks with `state: skipped`.
   - Progress percentage = `closed_count / (total_tasks - skipped_count) * 100`.
2. **Resolve Queues**:
   - **Active Task(s)**: List of tasks with `state: in_progress`.
   - **Ready Queue**: List of `open` tasks that have no dependencies, or whose dependencies (listed in `depends_on`) are all `state: closed`.
   - **Blocked Queue**: List of `blocked` tasks, or `open` tasks that have at least one dependency that is not yet `closed`.

---

## Phase 3: Recent Discoveries

Extract notes from task files to display a chronological list of recent findings:

1. For each task file, extract lines starting with `- [` under the `## Notes & Discoveries` heading.
2. Gather all notes, parse timestamps, and sort in descending order.
3. Take the top 5 most recent notes.

---

## Phase 4: Next Action Recommendations

Suggest logical next steps based on the queue state:

- If there are active tasks: recommend resuming work on them.
- If there are no active tasks but ready tasks exist: recommend claiming and starting the first ready task.
- If the ready queue is empty but there are blocked tasks: recommend investigating and resolving dependencies to unblock tasks.
- If all tasks are completed: recommend proposing documentation updates or archiving the flow.

---

## Execution

As the AI agent, you must execute the status dashboard aggregation directly inside your turn using the workflow detailed in Phase 1, 2, 3, and 4.
Do NOT call external python tools. Use directory listing and file-reading tools to gather the metadata from spec and task files.
