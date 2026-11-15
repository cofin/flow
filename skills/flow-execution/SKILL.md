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
2. **Quota-Aware Model Selection & Cross-Harness Parallel Execution (`1..N` Tasks)**:
   - Execute **one active chapter** (`1..N` tasks; zero 4-task cap) per `/flow:implement` run by default, or consecutive ready non-`empirical_dependent` chapters when `--all` is passed (closing out each chapter before advancing). Maximize Frontier **Pro** quota strictly for planning while keeping implementation and routine review off Pro.
   - **Cross-Harness Disjoint Parallelism (`small_swarm` / `parallel_subagents`, `<= 3` Writers per Wave)**: Run `tools/model_router.py check-disjoint` on the active chapter (or single-chapter root `tasks/`):
     - **Google Antigravity (`small_swarm`)**: Probe live quotas (`swarm(action="models", all=True)`). When `>= 2` ready tasks have disjoint `files:`/`tests:` AND worker Flash quota is strictly `> 25%`, spawn `1..3` writer workers (`workspace: "share"`, up to `5` tasks per writer per wave on high/extra-high thinking Flash, tagged `[Flow Swarm Worker]`, forbidden from `.agents/bundles/`) plus `1` zero-context verifier (`workspace: "inherit"`). Cherry-pick commits in task order, run the Fast Chapter Gate once per wave/chapter, verify `chapter_base_commit..HEAD`, kill workers cleanly, and reconcile `.agents/bundles/`.
     - **Claude Code, Codex CLI, Cursor, & OpenCode V2 (`parallel_subagents`)**: When `>= 2` ready tasks have disjoint `files:`/`tests:`, dispatch `1..3` isolated parallel `@executor` subagents (using isolated worktrees such as Claude `isolation: "worktree"` or disjoint shared paths; `sonnet` on Claude Code, `medium` on Codex) with up to `5` tasks per worker per wave, then run the Fast Chapter Gate once after merging.
   - **Bounded Chapter-Batch Fallback (`chapter_batch`)**: On single-task chapters, overlapping write sets, Antigravity Flash quota `<= 25%`, or single-runner hosts, invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={...})` (Antigravity — chunking `> 5`-task chapters across bounded `<= 5`-task Flash worker batches) or sequential bounded `@executor` turns (`<= 5` tasks per batch; `sonnet` on Claude Code, `medium` on Codex; never `haiku` or `flash_lite`).
   - Each writer stays inside its slice's `read_set`, implements vertical slices through the real System Under Test (applying the **Hypothesis-Driven Bug Diagnosis Loop** on non-obvious failures), validates with offline `< 60s` lint + targeted unit test file(s)—**never** running slow `> 60s` full test suites mid-flow—and creates signed code+test commit(s) (`<CODE_SHA>`, or returns `commit_deferred_to_coordinator: true` when `.git/` is read-only inside a sandbox).
3. **Chapter Closeout Sequence (Write-Time Sync &rarr; OKF Gate &rarr; Zero-Context Review &rarr; Clean Stop)**:
   - **Commit-First SHA Recording & Present-Tense Markdown/OKF Sync**: Record `<CODE_SHA>` in each completed `tasks/<id>-<slug>.md` (`state: completed`, `commit: <CODE_SHA>`) and `[x] [<CODE_SHA>]` in `chapters/<ch_id>/spec.md` **without running `git commit --amend`**, update affected `.agents/bundles/knowledge/**` and user `docs/**` in present tense, rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` (`[k/N files documented]` and `## 6. Current State & Remaining Plan Snapshot`) in place with zero chronological history (logging only in `.agents/bundles/log.md`), run `/flow:validate` on `<flow_id>` (`exit 0`), and commit the synced docs.
   - **Zero-Context Chapter Code & Markdown-Sync Review**: Dispatch isolated `@code-reviewer` + `@quality-reviewer` across `chapter_base_commit..HEAD` (`review_mode="single"` for `Small` specs or chapters with `<= 3` tasks and `<= 400` changed lines; `dual` otherwise) using high/extra-high thinking Flash on Antigravity (reserving Pro quota strictly for planning) and `sonnet` on Claude Code (`medium` on Codex; **never** `flash_lite` / `haiku`); remediate any `ADOPT` findings and re-verify with the Fast Chapter Gate.
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
