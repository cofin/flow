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
2. **Quota-Aware Model Selection & Chapter Execution (`1–4` Tasks in Active Chapter Only)**:
   - Execute strictly **one chapter** (`1–4` tasks) per `/flow:implement` run. On Google Antigravity, probe live quotas (`swarm(action="models", all=True)`) and resolve via `tools/model_router.py` (`resolve` + `check-disjoint`): keep the Coordinator on the highest-quota frontier Pro model (`>= 25%` floor), and route execution writers, verifiers, and reviewers to high/extra-thinking Flash tiers (generating conversation-scoped runtime profiles with `materialize-agents` for `run_workflow` pinning).
   - **Disjoint Small Swarm (`small_swarm`, `<= 4` workers total)**: Only when `check-disjoint` confirms `2–4` ready tasks with strictly non-overlapping `files:` and `tests:` write sets AND worker Flash quota is strictly `> 25%` on a `swarm`-capable host, the Coordinator spawns `1–3` writer workers (`workspace: "share"`, tagging prompts `[Flow Swarm Worker]`, forbidden from touching `.agents/bundles/` in shares) plus `1` zero-context read-only verifier (`workspace: "inherit"`). Writers implement and commit locally per share; Coordinator cherry-picks commits in task order, runs the Fast Chapter Gate once, triggers the verifier across `chapter_base_commit..HEAD`, hot-swaps throttled workers with `swarm(action="model")`, runs `swarm(action="kill")` cleanly, and reconciles `.agents/bundles/` in present tense.
   - **Chapter-Batch Fallback (`chapter_batch`)**: On single-task chapters, overlapping write sets, worker Flash quota `<= 25%`, or Claude/Codex/Cursor/OpenCode/VS Code hosts, invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={...})` (Antigravity) or one warm `@executor` turn (`sonnet` on Claude Code when the parent session is Opus; never `haiku` or `flash_lite`).
   - Each writer stays inside its bounded `read_set`, implements vertical slices through the real System Under Test (applying the **Hypothesis-Driven Bug Diagnosis Loop** on non-obvious failures), validates with offline `< 60s` lint + targeted unit test file(s)—**never** running slow `> 60s` full test suites mid-flow—and creates signed code+test commit(s) (`<CODE_SHA>`, or returns `commit_deferred_to_coordinator: true` when `.git/` is read-only inside a sandbox).
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
