---
name: flow-execution
description: "Use when executing a single Flow chapter's task blueprints in isolated subagent turns with pre-review Markdown sync (/flow:implement) or reporting chapter and task status (/flow:status)."
disable-model-invocation: true
---

# Flow Execution (Single-Chapter Subagent Pipeline, Pre-Review Sync, & Public-Seam TDD)

<!-- lifecycle-ownership: owner=flow-execution; operations=implement,status -->

## Trigger

Use for `implement` ([`../flow/references/implement.md`](../flow/references/implement.md)) and `status` ([`../flow/references/status.md`](../flow/references/status.md)).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - one-chapter-per-implement-run
  - worksheet-first-bounded-read-set
  - execution-preflight
  - public-seam-tdd-no-mocked-sut
  - fail-closed-no-production-mutation
  - atomic-task-commit
  - pre-review-present-tense-markdown-sync
  - chapter-code-and-doc-review-before-stop
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

## Workflow

1. **Active Chapter Resolution & Execution Preflight (`/flow:status` or `/flow:implement`)**:
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), and only the active `current_chapter`'s `spec.md` + `tasks/*.md` ([`../flow/references/state.md`](../flow/references/state.md)).
   - Verify `depends_on_chapters` are `completed` with non-null `last_reviewed_commit` and `planning_status == "complete"`; if `planning_status == "empirical_dependent"`, stop cleanly with zero production edits and route to `/flow:revise <flow_id> <chapter_id>`.
   - Run the task preflight (`dependencies_closed`, `worksheet_complete`, `verification_strategy_declared`, `plan_identity_matches`, `target_symbols_exist`). On mismatch, mark the task `state: blocked` (`[!]`) with zero production edits and route to `/flow:revise`.
2. **Isolated Subagent Task Pipeline (`1–4` Tasks in Active Chapter Only)**:
   - Execute strictly **one chapter** (`1–4` tasks) per `/flow:implement` run, dispatching one fresh isolated `@executor` subagent per task worksheet (`model: inherit`; `run_workflow` `pipeline()` with `type_name="self"` and `agents/executor.md` on Google Antigravity).
   - Each `@executor` stays inside its worksheet's `Bounded Read Manifest` (`read_set <= 6` files), collects initial evidence (`behavior_tdd` / `regression_tdd` Red first), implements through the real System Under Test (applying the **Hypothesis-Driven Bug Diagnosis Loop** on non-obvious failures), verifies Green + fast lint (`exit 0`), and atomically commits its owned files plus synced task `state`/`commit` and `[x] [<sha>]` checklist marker.
3. **Chapter Closeout Sequence (Checkpoint &rarr; Present-Tense Sync &rarr; Zero-Context Review &rarr; Hard Stop)**:
   - **Chapter Recovery Checkpoint**: Run the chapter's aggregate lint and test suite (`exit 0`).
   - **Present-Tense Markdown, OKF, & Full-Plan Sync**: Dispatch an isolated sync subagent (`type_name="self"` on Antigravity) to update affected `.agents/bundles/knowledge/**` and user `docs/**` in present tense, rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` (`[k/N files documented]` and `## 6. Current State & Remaining Plan Snapshot`) in place with zero chronological history (logging only in `.agents/bundles/log.md`), and commit the synced docs.
   - **Zero-Context Chapter Code & Markdown-Sync Review**: Dispatch isolated `@code-reviewer` + `@quality-reviewer` (`type_name="self"` on Antigravity) across `chapter_base_commit..HEAD` covering both code/tests and synced Markdown/OKF files; remediate any `ADOPT` findings and re-verify.
   - **Review Stamp, Pointer Advance, & Hard Stop**: Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` and `state: completed` in `chapters/<ch_id>/spec.md`, mark `- [x] [<REVIEWED_HEAD_SHA>] <ch_id>` and advance `current_chapter` + `last_reviewed_chapter` + `last_reviewed_commit` in root `specs/<flow_id>/spec.md`, commit closeout metadata, and **stop cleanly at the chapter boundary** (recommending `/compact` or a fresh session before the next chapter).

## Guardrails

- Execute one task worksheet per subagent turn and at most **one chapter** (`1–4` tasks) per `/flow:implement` invocation; never chain multiple chapters in one session turn.
- Always run present-tense Markdown/OKF sync **before** Zero-Context Chapter Review so reviewers verify both code and living docs, and stamp `last_reviewed_commit` before stopping so cross-harness `Stop` hooks pass cleanly.
- Never mark a task or chapter `completed` without fresh `exit 0` verification, and never create/mutate Git tags or push without explicit user instruction.

## Output

Return the completed chapter/task summary, verification exit codes, atomic task and sync commit SHAs, Chapter Review Adjudication summary, `last_reviewed_commit`, remaining chapters from the full plan, and `/compact` + next `/flow:implement <flow_id>` (or `/flow:finish <flow_id>`) handoff.

## Validation

Confirm all chapter verification commands exited `0`, every `tasks/<id>-<slug>.md` `state`/`commit` matches its `spec.md` checklist, root `spec.md` + `chapters/index.md` + `knowledge/**` + `docs/**` are synced in present tense without historical prose, and `last_reviewed_commit` covers every completed task commit in the chapter.
