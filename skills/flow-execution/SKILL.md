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
2. **Chapter-Batch Execution (`1–4` Tasks in Active Chapter Only)**:
   - Execute strictly **one chapter** (`1–4` tasks) per `/flow:implement` run. On Google Antigravity, invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={...})` (`execution_mode: "chapter_batch"` by default, or `"per_task"` when tasks touch disjoint subsystems) passing `templates/agent/executor-schema-card.md` and `agents/executor.md` (`type_name="self"`, quota-aware `inherit` &rarr; `flash` fallback). On Claude Code / Cursor / Codex / OpenCode, dispatch **one warm `@executor` turn** (`sonnet` on Claude Code when the parent session is Opus; never `haiku` or `flash_lite`) across the active chapter's `1–4` task blueprints so shared files are read and edited once.
   - Each `@executor` stays inside the union of the chapter's `Bounded Read Manifests`, implements vertical slices through the real System Under Test (applying the **Hypothesis-Driven Bug Diagnosis Loop** on non-obvious failures), runs the **Fast Chapter Gate** (`< 60s`: offline lint/typecheck + targeted unit test file(s)—**never** running slow `> 60s` full test suites between steps or mid-flow), and creates signed code+test commit(s) (`<CODE_SHA>`) **first** (or returns `commit_deferred_to_coordinator: true` when `.git/` is read-only inside a background sandbox so the coordinator commits on its behalf).
3. **Chapter Closeout Sequence (Write-Time Sync &rarr; OKF Gate &rarr; Zero-Context Review &rarr; Hard Stop)**:
   - **Commit-First SHA Recording & Present-Tense Markdown/OKF Sync**: Record `<CODE_SHA>` in each completed `tasks/<id>-<slug>.md` (`state: completed`, `commit: <CODE_SHA>`) and `[x] [<CODE_SHA>]` in `chapters/<ch_id>/spec.md` **without running `git commit --amend`**, update affected `.agents/bundles/knowledge/**` and user `docs/**` in present tense, rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` (`[k/N files documented]` and `## 6. Current State & Remaining Plan Snapshot`) in place with zero chronological history (logging only in `.agents/bundles/log.md`), run `/flow:validate` on `<flow_id>` (`exit 0`), and commit the synced docs.
   - **Zero-Context Chapter Code & Markdown-Sync Review**: Dispatch isolated `@code-reviewer` + `@quality-reviewer` on the frontier review tier (**Opus** on Claude Code when available, else `sonnet`; **Gemini Pro** / Pro-Next on Antigravity when available, else `flash` on quota fallback; `high` on Codex—**never** `flash_lite` / `haiku`) across `chapter_base_commit..HEAD` (`review_mode="single"` for `Small` single-chapter `<= 2`-task flows; `dual` otherwise); remediate any `ADOPT` findings and re-verify with the Fast Chapter Gate.
   - **Anti-Skip Audit, Review Stamp, Pointer Advance, & Hard Stop**: Verify zero tasks in the chapter remain `pending`/`open`/`in_progress`/`blocked`, any `deferred` item carries `deferred_by: "user"` + `deferred_reason`, and completed task commits modified at least one declared path in `files:` or `tests:`. Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` and `state: completed` in `chapters/<ch_id>/spec.md`, advance `current_chapter` + `last_reviewed_chapter` + `last_reviewed_commit` in root `specs/<flow_id>/spec.md`, commit closeout metadata, and **stop cleanly at the chapter boundary**.

## Guardrails

- Execute at most **one chapter** (`1–4` tasks) per `/flow:implement` invocation; never chain multiple chapters in one turn or skip remaining chapters to declare root `spec.md` `completed`.
- Never mark any task or chapter `deferred` or `skipped` unless the user explicitly chose deferral (`deferred_by: "user"` and non-empty `deferred_reason`).
- Never use `git commit --amend` to back-fill a task `commit:` SHA; commit code+tests first (`<CODE_SHA>`) and record `<CODE_SHA>` in the pre-review sync commit.
- Reserve slow (`> 60s`) full repository test suites for `/flow:finish` (or CI), validating intermediate chapters once with the `< 60s` Fast Chapter Gate.
- Never create/mutate Git tags or push without explicit user instruction.

## Output

Return the completed chapter/task summary, verification exit codes, atomic task and sync commit SHAs, Chapter Review Adjudication summary, `last_reviewed_commit`, remaining chapters from the full plan, and `/compact` + next `/flow:implement <flow_id>` (or `/flow:finish <flow_id>`) handoff.

## Validation

Confirm all chapter verification commands exited `0`, every `tasks/<id>-<slug>.md` `state`/`commit` matches its `spec.md` checklist, root `spec.md` + `chapters/index.md` + `knowledge/**` + `docs/**` are synced in present tense without historical prose, and `last_reviewed_commit` covers every completed task commit in the chapter.
