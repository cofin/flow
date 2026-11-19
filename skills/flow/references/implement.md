# Flow Implement (`/flow:implement`)

Execute **the active chapter** (`1..N` tasks, or consecutive ready non-`empirical_dependent` chapters with `--all`) using parallel separate-file workers (`small_swarm` on Antigravity; `parallel_tasks` elsewhere) or sequential `chapter_batch` turns (`<= 4` tasks per worker on `standard`/`fast` roles so `strong` quota stays reserved for planning).
Follow public interface TDD, run one fast chapter check (`< 60s`), commit code first to obtain `<CODE_SHA>`, sync present-tense Markdown and OKF docs, run independent chapter review, stamp `last_reviewed_commit`, and close the chapter.

## Usage

```text
/flow:implement [flow_id] [chapter_id | task_id] [--all]
```

## Phase 1: Worktree, Active Chapter & Preflight

1. **Resolve Worktree & Active Chapter (`< 25k` Coordinator Context)**:
   - In linked `git worktree` checkouts, follow `<hook_context>` routing: under `shared` tracking edit `$WORKTREE/.agents/` directly; under `local-only` stealth mode route `.agents/` edits to `$MAIN_WORKTREE/.agents/` (or its symlink), and run Python via `uv run --no-sync`.
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`. If `planning_quality: degraded` is set, show `planning_degraded_reason` before executing.
   - When `has_chapters: true`, read `specs/<flow_id>/chapters/index.md` and resolve `current_chapter` (or `[chapter_id]`), then read **only** `specs/<flow_id>/chapters/<ch_id>/spec.md` and `chapters/<ch_id>/tasks/*.md`.
   - Verify chapter preconditions before touching any task:
     1. `chapter_dependencies_closed_and_reviewed`: Every chapter in `depends_on_chapters` has `state: completed` and a valid hex `last_reviewed_commit`.
     2. `chapter_planning_status_complete`: `planning_status == "complete"`. If `planning_status == "empirical_dependent"`, stop without editing production code and route to `/flow:revise <flow_id> <chapter_id>` to fold in `replan_trigger` findings.
2. **Resume or Select Ready Tasks**:
   - Record `chapter_base_commit` (the parent of the chapter's first task commit, or `HEAD` when starting).
   - If a task has `state: in_progress`, inspect `git log -n 5 --oneline` and `git status --short -b` to sync any landed commit; otherwise select ready `pending`/`open` tasks in `(priority, created_at, id)` order whose `depends_on` tasks are `completed`.
3. **Preflight & Stop-Without-Editing Routing**:
   - Before running the chapter, verify for each ready task:
     1. `dependencies_closed`: Every task in `depends_on` is `completed`/`closed` with a valid `commit` SHA.
     2. `worksheet_complete`: For `worksheet_format: full`, all 8 headings (`## Objective & Scope Boundary`, `## Bounded Read Manifest`, `## Symbol & Signature Contracts`, `## Edge Cases & Error Semantics`, `## Public-Seam Test Blueprint`, `## Verification`, `## Acceptance Criteria`, `## Notes & Discoveries`) are populated.
     3. `compact_worksheet`: For `worksheet_format: compact`, `## Objective & Scope Boundary`, `## Bounded Read Manifest`, `## Contracts & Edge Cases`, `## Test Matrix`, `## Verification`, and `## Acceptance Criteria` are populated without arbitrary `read_set` or `estimated_loc` rejections.
     4. `verification_strategy_declared`: `verification_strategy` matches the task's change class.
     5. `plan_identity_matches`: `plan_revision` and `plan_commit` match between the owning `spec.md` and the task worksheet.
     6. `target_symbols_exist`: All target `files:`, `tests:`, and `path/to/file::Symbol` anchors match current repo code.
   - If any check fails, stop without editing production code: append evidence to `## Notes & Discoveries`, set `state: blocked` (`[!]`), `blocked_reason`, `unblock_condition`, and `next_step: "/flow:revise <flow_id> [chapter_id]"`.

## Phase 2: Claim Chapter & Dispatch Workers

1. Mark the active chapter `- [~] <ch_id>` in root `specs/<flow_id>/spec.md` (`state: active`, `current_chapter: <ch_id>`) and claim ready tasks (`state: in_progress`, `claimed_by: <harness>:<session_id>[:<role_or_worktree>]`, `claimed_at: <ISO-8601 UTC>`, `current_task: <id>`, marker `- [~]`).
2. Reset both `claimed_by: null` and `claimed_at: null` when releasing a claim back to `pending` or completing a task.
3. **Cross-Harness Worker Dispatch ([`orchestration.md`](orchestration.md))**:
   - **Pre-Dispatch Plan & Model Route**: Build ready steps via `flow tasks plan --briefs --flow <flow_id> --chapter <ch_id> --json` (tasks around `<= 250` LOC, `<= 3` files, `< 4k`-token briefs) and resolve `(model, effort)` via `flow models route --json`.
   - **Google Antigravity (`small_swarm`, `<= 4` workers per step)**: Selected when `>= 2` ready tasks edit separate files and capacity permits:
     1. Update the Swarm UI checklist (`plan.json`) and spawn `1..3` writer workers (`workspace: "share"`, tagged `[Flow Swarm Worker]` with `templates/agent/executor-schema-card.md` + `agents/executor.md`) plus `1` independent read-only verifier (`workspace: "inherit"`).
     2. Writers stay out of `.agents/bundles/` inside shares, implement from their `< 4k`-token brief, and create one signed commit (`<SHARE_SHA>`). Between steps, sync checklists via `flow sync` before running consolidated closeout checks once.
   - **Claude Code, Codex CLI, Cursor & OpenCode V2 (`parallel_tasks`)**: Dispatch up to `4` isolated `@executor` subagents over separate-file tasks (worktrees or separate assigned paths) using `.claude/agents/flow-model-*` or `.codex/agents/flow-model-*`, merge into the workspace, and run `flow sync`.
   - **Packaged Workflow Fallback (`flow-chapter-pipeline`)**: Invoke `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={"flow_id": flow_id, "chapter_id": ch_id, "tasks": task_paths})` for parallel-step or sequential `chapter_batch` runs with CLI sync between steps and `ReviewRoster` closeout.

## Phase 3: Public Interface TDD & Commit Code First

| Strategy | Initial Evidence | Implementation & Fast Chapter Check (`< 60s`) |
| --- | --- | --- |
| `behavior_tdd` | Write parameterized behavioral test(s) from the test cases at the confirmed public interface in the canonical test module and observe failure where practical. | Implement the chapter's tasks, run the targeted unit test file(s) and offline lint/typecheck once (`exit 0`). |
| `regression_tdd` | Write the minimized reproduction test at the public interface in the canonical test module and confirm it fails with the defect symptom. | Implement the narrow fix and rerun the targeted test file(s) and fast lint check (`exit 0`). |
| `characterization` | Run the focused behavior baseline at the public interface and confirm it passes before refactoring. | Refactor or debloat while keeping the focused behavior baseline and fast lint check passing (`exit 0`). |
| `static_validation` | Run the offline native validator, linter, or typechecker baseline. | Prove any new check catches a representative isolated violation, restore clean state, and verify exit code `0`. |
| `documentation_validation` | Run the offline Markdown, link, frontmatter, and example baseline. | Author present-tense docs/OKF chapters and verify all link, schema, and lint checks exit `0`. |
| `integration_acceptance` | Run the focused integration target for the touched subsystem. | Verify end-to-end composition and negative refusal paths exit `0`. |

### Verification Cadence & Commit-Code-First Rules

- **Fast Chapter Check (`< 60s`) vs. Full Release Suite**: Validate once per chapter using offline sandbox-safe commands from `## Verification`, `.agents/setup-state.json`, or detected build config (`Makefile`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`). Run only targeted test files for touched modules—never `npx --yes` downloads inside subagents, and never `> 60s` full suites between tasks (run the full suite once at `/flow:finish` or CI).
- **The Interface Is the Test Surface**: Test through confirmed public interfaces using domain terms from `knowledge/domains/<domain>.md`. Never mock real code, mock internal collaborators, test private methods, recompute expected outputs with production logic, or create `test_*remediation*.py` / `test_*audit*.py` files.
- **When Tests Fail**: Follow the **Bug Diagnosis Loop** in [`discipline.md`](discipline.md). If 3 fixes fail in a row, stop, mark the task `blocked`, and route to `/flow:revise`.
- **Commit Code First (`<CODE_SHA>`, Never `git commit --amend`)**:
  1. Stage exact owned production and test paths (`files:` + `tests:`, never `git add -A` or `git add -f`) and create a signed commit (`git commit -S -m "<type>(<scope>): <concise summary>"`) before writing `commit:` into task frontmatter.
  2. **Sandbox Read-Only `.git/` Fallback**: If a background subagent cannot write `.git/index.lock`, it leaves verified edits on disk and returns `commit_deferred_to_coordinator: true` plus `files_modified` so the coordinator creates `<CODE_SHA>` immediately.

## Phase 4: Chapter Closeout Sequence

As soon as all tasks in the active chapter finish and pass the fast chapter check, run all closeout steps before ending the coordinator turn:

1. **Record `<CODE_SHA>` & Sync Present-Tense Markdown/OKF**:
   - Run pre-review Markdown/OKF sync (inside `flow-chapter-pipeline` or via an isolated sync subagent):
     1. Record each completed task's `<CODE_SHA>` in `tasks/<id>-<slug>.md` (`state: completed`, `commit: <CODE_SHA>`, `last_verified_at`, `last_verified_commit: <CODE_SHA>`, `verification_evidence`, `claimed_by: null`, `claimed_at: null`) and mark `- [x] [<CODE_SHA>] <id> — ...` in `spec.md` without amending `<CODE_SHA>`.
     2. Update or create every `.agents/bundles/knowledge/**` chapter and user `README.md` / `docs/**` file owned by this chapter in present tense (`status: stable`, `<= 40`-line `<!-- truth: start -->` truth block, `sources:` + `[^id]:` footnotes, `verified:`, frontmatter-free `index.md`).
     3. Rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` in place in present tense: sync refined contracts across root `spec.md` and downstream chapters (`chK..chNN`), update `[k/N files documented]` in `## 3. Documentation & OKF Knowledge Plan`, and update `## 6. Current State & Remaining Plan Snapshot` with zero chronological history.
     4. Run `/flow:validate` on `<flow_id>` (`exit 0`), prepend an ISO-dated `chapter-complete` entry to `.agents/bundles/log.md`, and create a signed sync commit (`docs(<scope>): sync present-tense specs and knowledge for <ch_id>`).
2. **Independent Chapter Code & Doc-Sync Review**:
   - Dispatch isolated read-only reviewers across `chapter_base_commit..HEAD` planned via `flow review plan --json` ([`review.md`](review.md), [`orchestration.md`](orchestration.md); `flow-chapter-pipeline` or `flow-dual-review` with `type_name="self"` on Antigravity, checking `git status --porcelain` afterward).
   - Reviewers check both code/test changes and the synced `spec.md`, `chapters/index.md`, `knowledge/**`, and `docs/**` files for spec conformance, deep module interfaces, roadmap accuracy, and doc hygiene.
   - Fix any `ADOPT` findings in canonical files, rerun the fast chapter check and `/flow:validate` (`exit 0`), and re-verify; let `<REVIEWED_HEAD_SHA>` be the verified `HEAD` commit SHA.
3. **Completion Check, Review Stamp & Chapter-Boundary Stop**:
   - Verify zero tasks in `<ch_id>` remain `pending`, `open`, `in_progress`, or `blocked`, and any `deferred` item carries `deferred_by: "user"` and `deferred_reason`.
   - Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, `verified:`, and `state: completed` (`current_task: null`) in `chapters/<ch_id>/spec.md` (or single-chapter `specs/<flow_id>/spec.md`).
   - When `has_chapters: true`, update root `specs/<flow_id>/spec.md` and `chapters/index.md`: mark `- [x] [<REVIEWED_HEAD_SHA>] <ch_id> — ...`, set `last_reviewed_chapter: <ch_id>` and `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, and advance `current_chapter` to the next open chapter.
   - Never set root `state: completed` while any chapter in `chapters:` remains open. Create a signed closeout commit under `shared` tracking (or sync `.agents/` on disk under `local-only` stealth mode) so `hooks/stop-check.{sh,ps1}` verifies `merge-base --is-ancestor <task_sha> <REVIEWED_HEAD_SHA>`.
   - **Chapter-Boundary Stop vs. `--all`**: By default, stop after closing the active chapter, report `<REVIEWED_HEAD_SHA>` and remaining chapters, and hand off to `/flow:implement <flow_id>` or `/flow:finish <flow_id>`.
   - With `--all`, advance to the next ready non-`empirical_dependent` chapter and repeat Phases 1–4 until all ready chapters finish or hit an `empirical_dependent` or `blocked` check.
   - **Deliberate Pause or Bypass**: To pause mid-chapter without triggering `hooks/stop-check.{sh,ps1}`, set `state: paused` (or `paused: true` / `handoff: true`) on `spec.md`, set `stop_check: advisory`, configure `stop_check` / `sha_tracking` in `.agents/setup-state.json`, or export `FLOW_STOP_CHECK=off`. Active subagent and workflow runtime leases downgrade coordinator stop blocking while workers run.
