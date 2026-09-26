# /flow:refresh — Cross-Machine & Cross-Harness Session Reorientation

Refresh is the canonical **session reorientation** workflow when switching machines (`git pull` without untracked local journals), switching harnesses (Antigravity/Jetski, Claude Code, Codex CLI, OpenCode, Cursor), or resuming after external commits and dependency updates. It aligns code, specs, task worksheets, and local transactions, then emits an actionable status and handoff report.

<!-- flow-refresh-contract: start -->
```yaml
version: 1
operation: refresh
owner: flow-sync-status
state_skill: flow-state
state_operations:
  - status
  - recover
  - discover
  - release
  - revise
  - reconcile
completion_gates:
  - drift_inventory
  - transaction_reread
reorientation_axes:
  - journal_recovery_and_compaction
  - git_and_worktree_drift
  - cross_harness_claim_hygiene
  - revision_and_checklist_alignment
  - status_and_handoff_report
```
<!-- flow-refresh-contract: end -->

## Arguments

- `[flow_id]`: Optional target flow ID. Defaults to the active flow resolved via `.agents/setup-state.json` and `<configured-root>/bundles/index.md`.

## Reorientation Workflow

1. **Resolve Roots & Audit Local Transactions (`recover` + `transaction_reread`)**:
   - Read `.agents/setup-state.json` (default `<configured-root>` is `.agents/`), `<bundle-root>/index.md`, `.agents/bundles/product/tech-stack.md`, and `.agents/bundles/knowledge/workflow.md`.
   - Inspect `<configured-root>/transactions/*/journal.md`. Remember that `<configured-root>/transactions/` is untracked local recovery state:
     - If a nonterminal journal (`prepared`, `task_writes_started`, `recovery_required`, `rollback_in_progress`) exists locally, resolve it via `flow-state` `recover` before mutating or reporting.
     - If `<configured-root>/transactions/` is absent or empty (normal after `git pull` on another machine), treat tracked `spec.md`, `tasks/*.md`, and Git history as authority.
     - Prune superseded or obsolete terminal journals (`committed`, `rolled_back`, `superseded`) once live Markdown matches the committed `state_revision` so old transaction transcripts do not accumulate.

2. **Scan Codebase, Git History, & Workflow Drift (`drift_inventory`)**:
   - Inspect recent Git commits (`git log`), branch/HEAD state, and uncommitted working tree modifications (`git status --porcelain`, `git diff`).
   - Compare each task worksheet (`tasks/*.md`) against Git history and the working tree:
     - **Committed on another machine/session, task still open**: A commit in `HEAD` history lands the task's acceptance criteria or references its task ID while task `state` is still `open` or `in_progress`.
     - **Task closed, commit missing**: Task `state: closed` or `commit` points to a SHA missing from current branch history.
     - **Uncommitted work in progress**: Dirty working tree paths overlap a task's declared `files`/`tests` without a matching checkpoint.
     - **Tech-stack or workflow drift**: Dependency manifests (`pyproject.toml`, `package.json`, `Cargo.toml`) or command surfaces (`Makefile`, `justfile`, CI) changed relative to `product/tech-stack.md` and `knowledge/workflow.md`.

3. **Re-Anchor Cross-Harness & Cross-Machine Claims (`release`)**:
   - Inspect `claimed_by` and `claimed_at` across all `tasks/*.md` and `current_task` in `spec.md`:
     - `state: closed` or `skipped` with non-null `claimed_by`/`claimed_at` is a stale remnant.
     - `state: open` with non-null `claimed_by` is an orphaned claim.
     - `state: in_progress` claimed by a prior harness or another machine's session with no active local transaction and no matching dirty working tree activity is a stale cross-harness claim; release it via `flow-state` `release` (or re-bind to the current session) so work can be picked up cleanly.

4. **Align Specs, Tasks, and Context Files (`reconcile`, `discover`, `revise`)**:
   - Compare `spec.md` (`plan_revision`, `state_revision`, `plan_commit`, `current_task`, checklist markers, `Continuity Snapshot`) against all `tasks/*.md`.
   - Route deterministic alignment mutations through `flow-state`:
     - Mark externally completed tasks `state: closed` with their real Git `commit` SHA and run `reconcile` so `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`), `state_revision`, and `Continuity Snapshot` match `tasks/*.md`.
     - Use `discover` or `revise` (rewriting worksheets in-place in present tense without transcript bloat) when out-of-band commits altered file targets or task scope.
     - Refresh `product/tech-stack.md`, `knowledge/workflow.md`, and `knowledge/patterns/<topic>.md` when repo dependencies or commands changed.
   - Never guess on destructive conflicts (such as a `closed` task whose commit SHA is absent from `HEAD`); flag them explicitly in the handoff report.

5. **Emit Actionable Status & Handoff Dashboard (`status`)**:
   - Conclude every `/flow:refresh` with a scannable reorientation dashboard:
     - **Flow & Environment**: `flow_id`, lifecycle `state`, `plan_revision`, `state_revision`, ` branch @ HEAD`, working tree status, and local journal state.
     - **Alignment Summary**: Commits reconciled from other machines/sessions, stale cross-harness claims released, checklists synced, and context files refreshed.
     - **Task Queues**: Counts and IDs for `closed`, `in_progress`, `ready` (`open` with all `depends_on` closed, ordered by priority), `blocked`, and `skipped`.
     - **Next Exact Step**: The exact task worksheet to resume or claim next and the command to run (`/flow:implement <flow_id>`).

## Guardrails

- Never overwrite uncommitted user code changes; refresh updates bundle Markdown and transaction state only.
- Never fabricate `commit` SHAs or `verification_evidence`; bind reconciled tasks to real Git commits or leave them `open`/`in_progress` for verification.
- Never create or mutate Git tags.
