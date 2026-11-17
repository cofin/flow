---
name: flow-execution
description: "Use when executing a single Flow chapter's task blueprints in isolated subagent turns with pre-review Markdown sync (/flow:implement) or reporting chapter and task status (/flow:status)."
disable-model-invocation: true
---

# Flow Execution (Chapter-Batch Pipeline, Fast Chapter Gate, & Public-Seam TDD)

<!-- lifecycle-ownership: owner=flow-execution; operations=implement,status -->

## Trigger

Use for `implement` ([`../flow/references/implement.md`](../flow/references/implement.md)) and `status` ([`../flow/references/status.md`](../flow/references/status.md)).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - one-chapter-per-implement-run
  - chapter-batch-editing-shared-files-once
  - worksheet-first-bounded-read-set
  - execution-preflight
  - public-seam-tdd-no-mocked-sut
  - fail-closed-no-production-mutation
  - fast-chapter-gate-once-per-chapter
  - commit-first-sha-sync
  - pre-review-present-tense-markdown-sync
  - chapter-code-and-doc-review-before-stop
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

## Workflow

1. **Worktree Resolution, Active Chapter Resolution, & Execution Preflight (`/flow:status` or `/flow:implement`)**:
   - Resolve the effective `.agents/` bundle root across linked Git worktrees (`shared` worktree `.agents/` vs. `local-only` primary checkout `.agents/`; use symlinked `.venv`/`node_modules` with `uv run --no-sync` rather than re-running dependency installers).
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), and **only** the active `current_chapter`'s `spec.md` + `tasks/*.md` ([`../flow/references/state.md`](../flow/references/state.md)). Surface an explicit warning if `planning_quality == "degraded"`.
   - Verify `depends_on_chapters` are `completed` with non-null `last_reviewed_commit` and `planning_status == "complete"`; if `planning_status == "empirical_dependent"`, stop cleanly with zero production edits and route to `/flow:revise <flow_id> <chapter_id>`.
   - Run the task preflight (`dependencies_closed`, `worksheet_complete` across `full` or `compact` `blueprint_tier`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`). On mismatch, mark the task `state: blocked` (`[!]`) with zero production edits and route to `/flow:revise`.
2. **Dynamic Model Routing & Cross-Harness Parallel Waves (`1..N` Tasks)**:
   - Execute **one active chapter** per `/flow:implement` run by default, or consecutive ready non-`empirical_dependent` chapters when `--all` is passed (closing out each chapter before advancing). See [`../flow/references/orchestration.md`](../flow/references/orchestration.md) for dynamic `(model, effort)` selection and upward Frontier delegation rules.
   - **Micro-Sliced Context Pack Waves (`flow-cli.mjs slices compile --packs`)**: Compile ready tasks into disjoint waves (`<= 4` workers/wave, `<= 250` LOC & `<= 3` files per slice with `< 4k`-token pre-extracted `ContextPack`s):
     - **Google Antigravity (`small_swarm`)**: When `>= 2` ready slices are disjoint and live worker capacity allows parallel waves, spawn `1..3` writer workers (`workspace: "share"`, tagged `[Flow Swarm Worker]`, forbidden from `.agents/bundles/`) plus `1` zero-context verifier (`workspace: "inherit"`). Cherry-pick commits in task order, run `flow-cli.mjs spec sync` between waves, verify `chapter_base_commit..HEAD`, and kill workers cleanly.
     - **Claude Code, Codex CLI, Cursor, & OpenCode V2 (`parallel_subagents`)**: Dispatch up to `4` isolated parallel `@executor` subagents over disjoint slices (isolated worktrees or disjoint paths) and merge before closing.
   - **Packaged Workflow Fallback (`flow-chapter-pipeline`)**: Run `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={...})` for wave or sequential `chapter_batch` execution with zero-token inter-wave `flow-cli.mjs spec sync`.
   - Each writer stays inside its Context Pack / `read_set`, implements vertical slices through the real System Under Test (applying the **Hypothesis-Driven Bug Diagnosis Loop** on non-obvious failures), validates with offline `< 60s` lint + targeted unit test file(s), and creates signed code+test commit(s) (`<CODE_SHA>`, or `commit_deferred_to_coordinator: true`).
3. **Chapter Closeout Sequence (Write-Time Sync &rarr; OKF Gate &rarr; Zero-Context Review &rarr; Clean Stop)**:
   - **Commit-First SHA Recording & Present-Tense Markdown/OKF Sync**: Record `<CODE_SHA>` in each completed `tasks/<id>-<slug>.md` and `chapters/<ch_id>/spec.md`, update affected `.agents/bundles/knowledge/**` and `docs/**` in present tense, rewrite `chapters/index.md` and root `specs/<flow_id>/spec.md`, run `/flow:validate`, and commit the synced docs.
   - **Consolidated Zero-Context Closeout Review (`ReviewRoster`)**: Dispatch isolated reviewers planned by `flow-cli.mjs review plan` (`single` for small slices, `dual` or `committee` with cross-vendor adversarial seats for higher-risk diffs); remediate any `ADOPT` findings and re-verify once cleanly.
   - **Anti-Skip Audit, Review Stamp, Pointer Advance, & Chapter Closeout**: Verify zero tasks in the chapter remain `pending`/`open`/`in_progress`/`blocked`, any `deferred` item carries `deferred_by: "user"` + `deferred_reason`, and completed task commits modified at least one declared path in `files:` or `tests:`. Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` and `state: completed` in `chapters/<ch_id>/spec.md`, advance `current_chapter` + `last_reviewed_chapter` + `last_reviewed_commit` in root `specs/<flow_id>/spec.md`, commit closeout metadata, and stop at the chapter boundary unless `--all` was requested and another ready non-`empirical_dependent` chapter remains.

## Guardrails

- Execute one active chapter per `/flow:implement` invocation by default (or consecutive ready chapters when `--all` is requested, completing closeout and review per chapter); never skip remaining chapters or child specs to declare root `spec.md` or PRD `completed`.
- Never mark any task or chapter `deferred` or `skipped` unless the user explicitly chose deferral (`deferred_by: "user"` and non-empty `deferred_reason`).
- Never use `git commit --amend` to back-fill a task `commit:` SHA; commit code+tests first (`<CODE_SHA>`) and record `<CODE_SHA>` in the pre-review sync commit.
- Reserve slow (`> 60s`) full repository test suites for `/flow:finish` (or CI), validating intermediate chapters once with the `< 60s` Fast Chapter Gate.
- Never create/mutate Git tags or push without explicit user instruction.

## Output

Return the completed chapter/task summary, verification exit codes, atomic task and sync commit SHAs, Chapter Review Adjudication summary, `last_reviewed_commit`, remaining chapters from the full plan, and `/compact` + next `/flow:implement <flow_id>` (or `/flow:finish <flow_id>`) handoff.

## Validation

Confirm all chapter verification commands exited `0`, every `tasks/<id>-<slug>.md` `state`/`commit` matches its `spec.md` checklist, root `spec.md` + `chapters/index.md` + `knowledge/**` + `docs/**` are synced in present tense without historical prose, and `last_reviewed_commit` covers every completed task commit in the chapter.
