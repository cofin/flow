
# Flow Sync

Reconciles the flow specification (`spec.md`) and the task files under `.agents/bundles/specs/<flow_id>/tasks/`.

---

## Phase 1: Reconcile Task Statuses and Commits

The sync reconciler operates directly on local markdown files:

1. **Auto-Discovery of Active Flow**:
   - If no `flow_id` is provided as an argument, scan `.agents/bundles/specs/*/spec.md` for active flows (`status` is `planned` or `active`).
   - If multiple exist, resolve to the one with the most recently modified files.
2. **Reconciliation Loop**:
   - Parse the `Implementation Plan` section of `spec.md` (lines matching `- [ ] Task <id>: <title>`).
   - Match the short task ID (e.g., `1.1` or `001-setup`) to a task file under `tasks/<id>.md`.
   - If the task file does not exist, **auto-scaffold** it:
     - Set frontmatter with `id: <flow_id>:<id>`, `status: open`, `depends_on: []`, `files: []`, `tests: []`, `created_at` and `updated_at` timestamps.
     - Add description and notes headings.
   - If the task file exists:
     - Parse task status from frontmatter and map to `spec.md` checklist status markers:
       - `open` -> `[ ]`
       - `in_progress` -> `[~]`
       - `closed` -> `[x]`
       - `blocked` -> `[!]`
       - `skipped` -> `[-]`
     - If the task status is `closed` and the frontmatter `commit` field has a SHA, append it to the task checklist line in `spec.md`: `[<sha>]`.
3. **Write spec.md**:
   - Save the updated spec file to disk and update its `updated_at` frontmatter timestamp.

---

## Phase 2: Run Integrity Validation

Validate spec/task schemas and link resolution directly using your file-manipulation tools:

- Verify YAML frontmatter schemas for both specs and tasks.
- Verify referenced files and tests in task files exist in the repository (enforced strictly only for `closed` tasks).
- Verify relative Markdown links exist (enforced strictly only for `completed` and `archived` flows).
- Verify task IDs match `<flow_id>:<short_id>` format.

---

## Phase 3: Context Drift Check

Verify if codebase settings or dependencies have drifted:

1. Compare dependency files (`package.json`, `pyproject.toml`, etc.) with `.agents/tech-stack.md`.
2. Inspect workflow drift across `Makefile`, `justfile`, `tasks.json`, etc.
3. Compare commands with `.agents/workflow.md`.
4. If drift is detected, notify the developer and request re-validation of `.agents/workflow.md`.
