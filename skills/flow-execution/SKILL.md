---
name: flow-execution
description: "Use when implementing an approved Flow chapter's task worksheets or reporting live spec and branch status. Don't use for drafting or revising specs (use flow-planning), initializing bundles (use flow-setup), or final review and closeout (use flow-completion)."
disable-model-invocation: true
---

# Flow Execution

<!-- lifecycle-ownership: owner=flow-execution; operations=implement,status -->

## Trigger

Use for `implement` ([`../flow/references/implement.md`](../flow/references/implement.md)) and `status` ([`../flow/references/status.md`](../flow/references/status.md)).

## Workflow

1. **Worktree Resolution, Active Chapter, & Preflight**:
   - Resolve the effective `.agents/` bundle root across linked Git worktrees (`shared` worktree `.agents/` vs. `local-only` primary checkout `.agents/`). Reuse symlinked `.venv`/`node_modules` with `uv run --no-sync` rather than re-running dependency installers.
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), and only the active `current_chapter`'s `spec.md` and `tasks/*.md` ([`../flow/references/state.md`](../flow/references/state.md)). Surface a warning if `planning_quality == "degraded"`.
   - Verify `depends_on_chapters` are `completed` with non-null `last_reviewed_commit` and `planning_status == "complete"`. If `planning_status == "empirical_dependent"`, stop without editing production files and route to `/flow:revise <flow_id> <chapter_id>`.
   - Run preflight (`dependencies_closed`, `worksheet_complete` for `full` or `compact` worksheets, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`). On mismatch, mark the task `state: blocked` (`[!]`) without editing production files and route to `/flow:revise`.
2. **Model Routing & Parallel Steps (`1..N` Tasks)**:
   - Execute one active chapter per `/flow:implement` run by default, or consecutive ready non-`empirical_dependent` chapters when `--all` is passed. See [`../flow/references/orchestration.md`](../flow/references/orchestration.md) for `strong`/`standard`/`fast`/`light` model routing.
   - **Task Plans & Briefs (`flow tasks plan --flow <flow_id> --briefs --json`)**: Group ready tasks on separate files into steps (`workers` up to `4`, `<= 250` LOC and `<= 3` files per task with compact briefs):
     - **Google Antigravity (`small_swarm`)**: When `>= 2` ready tasks touch separate files and worker quota allows, spawn `1..3` writer workers (`workspace: "share"`, tagged `[Flow Swarm Worker]`, no `.agents/bundles/` edits) and `1` independent verifier (`workspace: "inherit"`). Cherry-pick commits in task order, run `flow sync` between steps, verify `chapter_base_commit..HEAD`, and kill workers.
     - **Claude Code, Codex CLI, Cursor, & OpenCode V2 (`parallel_tasks`)**: Dispatch up to `4` isolated parallel `@executor` subagents over separate files (isolated worktrees or separate paths) and merge before closing.
   - **Workflow Fallback (`flow-chapter-pipeline`)**: Run `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={...})` for parallel or sequential execution with `flow sync` between steps.
   - Each writer stays inside its brief and `read_set`, writes tests against the real module under test, and uses bug diagnosis on non-obvious failures. It runs `< 60s` lint and targeted tests, then creates signed code+test commits (`<CODE_SHA>`, or `commit_deferred_to_coordinator: true`).
3. **Chapter Closeout Sequence**:
   - **Commit Code First & Sync Markdown/OKF**: Record `<CODE_SHA>` in each completed `tasks/<id>-<slug>.md` and `chapters/<ch_id>/spec.md`, update `.agents/bundles/knowledge/**` and `docs/**` in present tense, rewrite `chapters/index.md` and root `specs/<flow_id>/spec.md`, run `/flow:validate`, and commit the synced docs.
   - **Independent Closeout Review**: Dispatch isolated reviewers planned by `flow review plan --json` (`single` for small changes, `dual` or `committee` with another vendor for higher-risk diffs). Fix adopted findings and re-verify once.
   - **Completion Check, Review Stamp, & Pointer Advance**: Verify zero tasks remain `pending`/`open`/`in_progress`/`blocked`, any `deferred` item carries `deferred_by: "user"` + `deferred_reason`, and completed task commits modified a declared path in `files:` or `tests:`. Stamp `last_reviewed_commit` and `state: completed` in `chapters/<ch_id>/spec.md`, advance root `spec.md` pointers, commit closeout metadata, and stop at the chapter boundary unless `--all` has another ready chapter.

## Guardrails

- Execute one active chapter per run by default (or consecutive ready chapters with `--all`). Never skip remaining chapters or child specs so partial work cannot pose as done.
- Keep each worker inside its brief and `read_set`, test the real module without mocking it, and stop if preflight fails so changes stay isolated and reviewable.
- Never mark a task or chapter `deferred` or `skipped` without explicit user confirmation (`deferred_by: "user"` and non-empty `deferred_reason`).
- Never use `git commit --amend` to back-fill a task `commit:` SHA because amending changes the hash referenced by worksheets. Commit code and tests first (`<CODE_SHA>`), then record `<CODE_SHA>` in the sync commit.
- Run the `< 60s` chapter check once per chapter so iteration stays quick. Reserve slow (`> 60s`) full repository suites for `/flow:finish` or CI.
- Sync present-tense Markdown and pass chapter review before stopping so the Stop hook verifies a clean state. Never push or mutate Git tags without explicit instruction.

## Example

```bash
flow tasks plan --flow <flow_id> --briefs --json
flow sync --flow <flow_id>
```

## Output

Return the completed chapter/task summary, check exit codes, task and sync commit SHAs, review summary, `last_reviewed_commit`, remaining chapters from the full plan, and `/compact` + next `/flow:implement <flow_id>` (or `/flow:finish <flow_id>`) handoff.

## Validation

Confirm all chapter checks exited `0`, every `tasks/<id>-<slug>.md` `state`/`commit` matches its `spec.md` checklist, root `spec.md` + `chapters/index.md` + `knowledge/**` + `docs/**` are synced in present tense, and `last_reviewed_commit` covers every completed task commit in the chapter.
