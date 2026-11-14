# Flow Implement (`/flow:implement`)

Execute **strictly one active chapter** (`1–4` vertical-slice task blueprints) per `/flow:implement` run using Chapter-Batch Execution (`flow-chapter-pipeline` by default so shared files are edited once), Bounded Read Manifests (`read_set <= 6`), Public-Seam TDD, a single `< 60s` Fast Chapter Gate per chapter, commit-first `<CODE_SHA>` sequencing, pre-review present-tense Markdown/OKF synchronization, Zero-Context Chapter Code & Markdown-Sync Review, `last_reviewed_commit` stamping, and a clean chapter-boundary stop.

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
preflight:
  checks:
    - worktree_bundle_and_env_resolved
    - chapter_dependencies_closed_and_reviewed
    - chapter_planning_status_complete
    - dependencies_closed
    - worksheet_complete
    - verification_strategy_declared
    - plan_identity_matches
    - target_symbols_exist
mismatch_classes:
  - empirical_replan_required
  - unreviewed_upstream_chapter
  - code_drift
  - missing_decision
  - invalid_file_symbol_or_test_target
  - acceptance_contradiction
  - scope_expansion
  - invalid_verification_command
```
<!-- flow-execution-policy: end -->

## Usage

```text
/flow:implement [flow_id] [chapter_id | task_id]
```

## Phase 1: Resolve Worktree, Active Chapter, & Run Execution Preflight

1. **Resolve Worktree & Active Chapter (`< 25k` Coordinator Context)**:
   - In linked `git worktree` checkouts, follow `<hook_context>` worktree routing: under `shared` tracking edit `$WORKTREE/.agents/` directly; under `local-only` stealth tracking route all `.agents/` Markdown reads and writes to `$MAIN_WORKTREE/.agents/` (or its symlink), and invoke Python tools via `uv run --no-sync` against the symlinked `.venv` instead of running `make install` or `uv sync`.
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`. If `planning_quality: degraded` is present on root or chapter `spec.md`, surface `planning_degraded_reason` to the user before executing.
   - When `has_chapters: true`, read `specs/<flow_id>/chapters/index.md` and resolve `current_chapter` (or explicit `[chapter_id]`), then read **only** `specs/<flow_id>/chapters/<ch_id>/spec.md` and `chapters/<ch_id>/tasks/*.md`—never load completed or downstream chapters' task worksheets into the coordinator.
   - Verify chapter-level gates before touching any task:
     1. `chapter_dependencies_closed_and_reviewed`: Every chapter in `depends_on_chapters` has `state: completed` and a valid hex `last_reviewed_commit`.
     2. `chapter_planning_status_complete`: `planning_status == "complete"`. If `planning_status == "empirical_dependent"`, halt immediately with zero production edits and route to `/flow:revise <flow_id> <chapter_id>` to fold in upstream empirical findings (`replan_trigger`).
2. **Resume or Select Ready Task(s) Within Active Chapter**:
   - Record `chapter_base_commit` (the parent of the chapter's first task commit, or `HEAD` when starting the chapter).
   - If a task in the active chapter has `state: in_progress`, inspect `git log -n 5 --oneline` and `git status --short -b` to reconcile any already-landed commit; otherwise select ready `pending`/`open` tasks in `(priority, created_at, id)` order whose `depends_on` tasks are `completed`.
3. **Execution Preflight & Fail-Closed Mismatch Routing**:
   - Before executing the chapter, verify for each ready task:
     1. `dependencies_closed`: Every task in `depends_on` is `completed`/`closed` with a valid `commit` SHA.
     2. `worksheet_complete`: For `blueprint_tier: full` (default), all required headings (`Objective & Scope Boundary`, `Bounded Read Manifest`, `Symbol & Signature Contracts`, `Edge Cases & Error Semantics`, `Public-Seam Test Blueprint`, `Verification`, `Acceptance Criteria`, `Notes & Discoveries`) are populated without placeholders; for `blueprint_tier: compact` (`estimated_loc <= 60` and `read_set <= 3`), `Objective & Scope Boundary`, `Bounded Read Manifest`, `Verification`, and `Acceptance Criteria` are populated; `read_set <= 6` and `estimated_loc <= 250`.
     3. `verification_strategy_declared`: `verification_strategy` matches the task's change class.
     4. `plan_identity_matches`: `plan_revision` and `plan_commit` match between the owning `spec.md` and the task worksheet.
     5. `target_symbols_exist`: All target `files:`, `tests:`, and `path/to/file::Symbol` anchors match current repository reality.
   - If any check fails, classify the mismatch and **make zero production code edits**: append evidence to `## Notes & Discoveries`, set task `state: blocked` (`[!]`), `blocked_reason`, `unblock_condition`, and `next_step: "/flow:revise <flow_id> [chapter_id]"`, and stop cleanly.

## Phase 2: Claim Chapter & Dispatch Chapter-Batch `@executor` (`1–4` Tasks Max)

1. Mark the active chapter `- [~] <ch_id>` in root `specs/<flow_id>/spec.md` (`state: active`, `current_chapter: <ch_id>`) and claim ready tasks (`state: in_progress`, `claimed_by: <harness>:<session_id>[:<role_or_worktree>]` where `<harness> ∈ {agy, claude, codex, cursor, opencode, vscode, cli}`, `claimed_at: <ISO-8601 UTC>`, `current_task: <id>`, checklist `- [~] <id> — ...`); reset both `claimed_by: null` and `claimed_at: null` when releasing a claim back to `pending` or completing a task.
2. **Quota-Aware Dispatch (`small_swarm` on Disjoint Chapters vs. `chapter_batch` Fallback)**:
   - **Pre-Dispatch Model & Disjoint Gate (Google Antigravity)**: Before spawning workers, check live quotas via `swarm(action="models", all=True)` and run `tools/model_router.py resolve` + `tools/model_router.py check-disjoint --bundle <bundle> --flow <flow_id> --chapter <ch_id> --flash-quota <pct>` (optionally writing ephemeral conversation-scoped profiles via `materialize-agents --out-dir <appDataDir>/brain/<conv-id>/.agents/agents` so `run_workflow` binds exact tiers cleanly).
   - **Coordinator-Driven Disjoint Small Swarm (`small_swarm`, strictly `<= 4` workers)**: Selected automatically **only** when (a) host supports `swarm`, (b) `2–4` ready tasks declare explicit non-overlapping `files:` + `tests:` write sets, AND (c) live worker Flash quota is strictly **`> 25%`**:
     1. Update the Swarm UI overview checklist (`plan.json`, no extra monitor or narrator workers) and spawn `1..3` disjoint writer workers (`workspace: "share"`, resolved high/extra-thinking Flash, prompt tagged `[Flow Swarm Worker]` with `templates/agent/executor-schema-card.md` + `agents/executor.md`), keeping `writer_count <= 3`.
     2. Spawn `1` zero-context read-only verifier (`workspace: "inherit"`, resolved verifier model, `[Flow Swarm Worker]`, `agents/code-reviewer.md` + `agents/quality-reviewer.md`), keeping total swarm workers `<= 4`.
     3. Writers stay strictly out of `.agents/bundles/` inside shares, run only scoped task/module verification, and create 1 signed commit in their share worktree/branch (`<SHARE_SHA>`). On quota/rate-limit stalls, Coordinator hot-swaps the worker live via `swarm(action="model")` to the next `fallback_chain` candidate.
     4. Once all writers post their share commit SHAs, Coordinator cherry-picks/merges commits cleanly into the workspace in task order, runs the Fast Chapter Gate once, triggers `@verifier` across `chapter_base_commit..HEAD`, applies any adopted fixes, executes Step 1–3 Closeout below, and terminates every worker with `swarm(action="kill")`.
   - **Default Sequential / Fallback (`execution_mode: "chapter_batch"`)**: Whenever write sets overlap, a chapter has a single ready task, worker Flash quota drops `<= 25%`, or on non-swarm hosts:
     - **Google Antigravity (`run_workflow`)**: Execute `run_workflow(ScriptPath="<plugin_root>/workflows/flow-chapter-pipeline/workflow.py", Args={"flow_id": flow_id, "chapter_id": ch_id, "tasks": task_paths, "execution_mode": "chapter_batch", "executor_agent": resolved_exec_agent, "reviewer_agent": resolved_rev_agent})` with automatic quota fallback (`never flash_lite`).
     - **Claude Code / Codex / Cursor / OpenCode**: Dispatch **one warm `@executor` subagent turn** (`sonnet` on Claude Code when the parent session is Opus—never `"haiku"`; `model_reasoning_effort = "medium"` on Codex) with `templates/agent/executor-schema-card.md`, chapter `spec.md`, and task paths. If unstated symbol dependencies require broad exploration, fail closed as `state: blocked`.

## Phase 3: Execute Public-Seam TDD, Fast Chapter Gate, & Commit-First Sequencing

| Strategy | Initial Evidence | Implementation & Fast Chapter Gate (`< 60s`) |
| --- | --- | --- |
| `behavior_tdd` | Write parameterized behavioral test(s) from the Worked Test Matrix at the confirmed public seam in the canonical test module and observe Red where practical. | Implement the chapter's vertical slices, run the targeted unit test file(s) + offline lint/typecheck gate once (`exit 0`). |
| `regression_tdd` | Write the minimized reproduction test at the public seam in the canonical test module and confirm it fails (Red) with the defect symptom. | Implement the narrow fix and rerun the targeted test file(s) + fast lint gate (`exit 0`). |
| `characterization` | Run the focused behavior baseline at the public seam and confirm it passes before refactoring. | Refactor/debloat while keeping the focused behavior baseline and fast lint gate Green (`exit 0`). |
| `static_validation` | Run the offline native validator, linter, or typechecker baseline. | Prove any new check catches a representative isolated violation, restore clean state, and verify exit code `0`. |
| `documentation_validation` | Run the offline Markdown, link, frontmatter, and example baseline. | Author present-tense docs/OKF chapters and verify all link, schema, and lint checks exit `0`. |
| `integration_acceptance` | Run the focused integration target for the touched subsystem. | Verify end-to-end composition and negative refusal paths exit `0`. |

### Verification Cadence, Public-Seam, & Commit-First Rules

- **Fast Chapter Gate (`< 60s`) vs. Full Release Suite**: Validate **once per chapter batch** using offline sandbox-safe commands (`make lint` / `uv run --no-sync ruff check` + targeted unit test file(s) for touched modules—never `npx --yes` network downloads inside background subagents). **Never** run slow (`> 60s`) full repository test suites between individual tasks or intermediate chapters; run the full suite once at `/flow:finish` (or CI).
- **The Interface Is the Test Surface**: Test strictly through confirmed public interfaces using domain terms from `knowledge/domains/<domain>.md`. Never mock the System Under Test, mock internal collaborators, test private methods, recompute expected outputs with production logic, or create standalone `test_*remediation*.py` / `test_*audit*.py` files.
- **When Tests Fail**: Follow the **Hypothesis-Driven Bug Diagnosis Loop** in [`discipline.md`](discipline.md). If 3 fixes fail in a row, stop, mark the task `blocked`, and route to `/flow:revise`.
- **Commit-First `<CODE_SHA>` Sequencing (Never `git commit --amend`)**:
  1. Stage exact owned production and test paths (`files:` + `tests:`, never `git add -A` or `git add -f`) and create a signed commit (`git commit -S -m "<type>(<scope>): <concise summary>"`) **before** writing `commit:` into task frontmatter so `<CODE_SHA>` is immutable and cryptographically valid.
  2. **Sandbox Read-Only `.git/` Fallback**: If a background subagent runs inside a sandbox where `.git/` is read-only (`Unable to create '.../.git/index.lock'`), it leaves its verified edits cleanly on disk and returns `commit_deferred_to_coordinator: true` + `files_modified` so the coordinator immediately creates `<CODE_SHA>` on its behalf instead of stalling or retrying.

## Phase 4: Chapter Closeout Sequence (Pre-Review Sync &rarr; OKF Gate &rarr; Review &rarr; Hard Stop)

As soon as the active chapter's `1–4` tasks finish implementation and pass the Fast Chapter Gate, execute all closeout steps **before ending the coordinator turn**:

1. **Step 1 — Commit-First SHA Recording & Present-Tense Markdown/OKF Sync**:
   - Perform **pre-review present-tense Markdown/OKF synchronization** (either inside `flow-chapter-pipeline` or via an isolated sync subagent):
     1. Record each completed task's `<CODE_SHA>` in `tasks/<id>-<slug>.md` (`state: completed`, `commit: <CODE_SHA>`, `last_verified_at`, `last_verified_commit: <CODE_SHA>`, `verification_evidence`, `claimed_by: null`, `claimed_at: null`) and mark `- [x] [<CODE_SHA>] <id> — ...` in the owning `spec.md`—**never** amending `<CODE_SHA>`.
     2. Update or create every `.agents/bundles/knowledge/**` chapter and user `README.md` / `docs/**` file owned by this chapter in present tense (`status: stable`, `<= 40`-line `<!-- truth: start -->` block, `sources:` + `[^id]:` footnotes, `verified:` stamp, frontmatter-free `index.md` catalogs).
     3. Rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` **in place in present tense**: reconcile any refined type/signature contracts across root `spec.md` and remaining downstream chapters (`chK..chNN`), update `[k/N files documented]` in `## 3. Documentation & OKF Knowledge Plan`, and rewrite `## 6. Current State & Remaining Plan Snapshot` with the verified baseline at `HEAD`, remaining chapters/tasks across the full plan, and active invariants—with **zero chronological history or revision logs** inside specs or docs.
     4. Run `/flow:validate` on `<flow_id>` (`exit 0`) to deterministically enforce OKF v0.2 structure and Git `diff-tree` task file-ownership proofs, prepend an ISO-dated `chapter-complete` entry to `.agents/bundles/log.md`, and create a signed sync commit (`docs(<scope>): sync present-tense specs and knowledge for <ch_id>`).
2. **Step 2 — Zero-Context Chapter Code & Markdown-Sync Review**:
   - Dispatch isolated read-only reviewers across `chapter_base_commit..HEAD` ([`review.md`](review.md); `flow-chapter-pipeline` or `flow-dual-review` with `type_name="self"` on Google Antigravity, checking `git status --porcelain` afterward; `review_mode="single"` for `Small` single-chapter `<= 2`-task flows, `dual` for all others, running reviewers on **Opus** on Claude Code when available [else `sonnet`] and **Gemini Pro** / Pro-Next on Antigravity when available [else `flash` on quota fallback]—**never** `flash_lite` / `haiku`).
   - Reviewers audit both production/test changes AND the synced `spec.md`, `chapters/index.md`, `knowledge/**`, and `docs/**` files for Spec Conformance, Deep-Module Seams, Present-Tense Full-Plan Roadmap Accuracy, and Zero-History Living-Doc Hygiene (`quality-review-v1`).
   - Remediate any `ADOPT` code or Markdown-sync findings in canonical files, rerun the Fast Chapter Gate + `/flow:validate` (`exit 0`), and re-verify; let `<REVIEWED_HEAD_SHA>` be the verified `HEAD` commit SHA.
3. **Step 3 — Anti-Skip Audit, Review Stamp, Pointer Advance, & Chapter-Boundary Hard Stop**:
   - Verify that zero tasks in `<ch_id>` remain `pending`/`open`/`in_progress`/`blocked` and that any `deferred` item was explicitly approved by the user (`deferred_by: "user"` + non-empty `deferred_reason`).
   - Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, `verified:`, and `state: completed` (`current_task: null`) in `chapters/<ch_id>/spec.md` (or single-chapter `specs/<flow_id>/spec.md`).
   - When `has_chapters: true`, update root `specs/<flow_id>/spec.md` and `chapters/index.md`: mark `- [x] [<REVIEWED_HEAD_SHA>] <ch_id> — ...`, set `last_reviewed_chapter: <ch_id>` and `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, and advance `current_chapter` to the next remaining chapter (never setting root `state: completed` while any chapter in `chapters:` remains open), then create a signed chapter-closeout metadata commit (under `shared` tracking; or sync `.agents/` on disk under `local-only` stealth mode) so `hooks/stop-check.{sh,ps1}` verifies `merge-base --is-ancestor <task_sha> <REVIEWED_HEAD_SHA>` cleanly.
   - **Hard Stop After One Chapter (or Deliberate Pause/Bypass)**: Stop immediately after closing the chapter—never automatically start executing the next chapter in the same turn. Report the completed chapter, `<REVIEWED_HEAD_SHA>`, remaining chapters from the full plan, and recommend running `/compact` (or starting a fresh session) before invoking `/flow:implement <flow_id>` for the next chapter (or `/flow:finish <flow_id>` when all chapters are complete). To stop cleanly mid-chapter for a human handoff without triggering `hooks/stop-check.{sh,ps1}`, set `state: paused` (or `paused: true` / `handoff: true`) on `spec.md`, set per-spec `gate: advisory`, configure `stop_gate` / `sha_tracking` in `.agents/setup-state.json`, or export `FLOW_STOP_GATE=off`; active subagent and workflow runtime leases automatically downgrade coordinator Stop blocking while workers remain active.
