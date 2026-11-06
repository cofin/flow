# Flow Implement (`/flow:implement`)

Execute **strictly one active chapter** (`1–4` vertical-slice task blueprints) per `/flow:implement` run using isolated single-worksheet `@executor` subagents, Bounded Read Manifests (`read_set <= 6`), Public-Seam TDD, pre-review present-tense Markdown/OKF synchronization, Zero-Context Chapter Code & Markdown-Sync Review, `last_reviewed_commit` stamping, and a clean chapter-boundary stop.

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
preflight:
  checks:
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

## Phase 1: Resolve Active Chapter, Load Scoped Context, & Run Execution Preflight

1. **Resolve Active Chapter (`< 25k` Coordinator Context)**:
   - Read root `.agents/bundles/specs/<flow_id>/spec.md`, `.agents/bundles/knowledge/workflow.md`, and `.agents/skills/index.md`.
   - When `has_chapters: true`, read `specs/<flow_id>/chapters/index.md` and resolve `current_chapter` (or explicit `[chapter_id]`), then read **only** `specs/<flow_id>/chapters/<ch_id>/spec.md` and `chapters/<ch_id>/tasks/*.md`—never load completed or downstream chapters' task worksheets into the coordinator.
   - Verify chapter-level gates before touching any task:
     1. `chapter_dependencies_closed_and_reviewed`: Every chapter in `depends_on_chapters` has `state: completed` and a valid hex `last_reviewed_commit`.
     2. `chapter_planning_status_complete`: `planning_status == "complete"`. If `planning_status == "empirical_dependent"`, halt immediately with zero production edits and route to `/flow:revise <flow_id> <chapter_id>` to fold in upstream empirical findings (`replan_trigger`).
2. **Resume or Select Ready Task(s) Within Active Chapter**:
   - Record `chapter_base_commit` (the parent of the chapter's first task commit, or `HEAD` when starting the chapter).
   - If a task in the active chapter has `state: in_progress`, inspect `git log -n 5 --oneline` and `git status --short -b` to reconcile any already-landed commit; otherwise select ready `pending`/`open` tasks in `(priority, created_at, id)` order whose `depends_on` tasks are `completed`.
3. **Execution Preflight & Fail-Closed Mismatch Routing**:
   - Before each task executes, verify:
     1. `dependencies_closed`: Every task in `depends_on` is `completed`/`closed` with a valid `commit` SHA.
     2. `worksheet_complete`: All 8 required blueprint headings (`Objective & Scope Boundary`, `Bounded Read Manifest`, `Symbol & Signature Contracts`, `Edge Cases & Error Semantics`, `Public-Seam Test Blueprint`, `Verification`, `Acceptance Criteria`, `Notes & Discoveries`) are populated without placeholders, with `read_set <= 6` and `estimated_loc <= 250`.
     3. `verification_strategy_declared`: `verification_strategy` matches the task's change class.
     4. `plan_identity_matches`: `plan_revision` and `plan_commit` match between the owning `spec.md` and the task worksheet.
     5. `target_symbols_exist`: All target `files:`, `tests:`, and `path/to/file::Symbol` anchors match current repository reality.
   - If any check fails, classify the mismatch and **make zero production code edits**: append evidence to `## Notes & Discoveries`, set task `state: blocked` (`[!]`), `blocked_reason`, `unblock_condition`, and `next_step: "/flow:revise <flow_id> [chapter_id]"`, and stop cleanly.

## Phase 2: Claim Task & Dispatch Isolated `@executor` Pipeline (`1–4` Tasks Max)

1. Mark the active chapter `- [~] <ch_id>` in root `specs/<flow_id>/spec.md` (`state: active`, `current_chapter: <ch_id>`) and claim each ready task (`state: in_progress`, `claimed_by`, `claimed_at`, `current_task: <id>`, checklist `- [~] <id> — ...`).
2. **Isolated Subagent / `run_workflow` Pipeline Execution**:
   - Dispatch one fresh isolated `@executor` subagent (`model: inherit`) per task worksheet across **only the active chapter's `1–4` tasks**. Never dispatch implementation subagents in parallel when tasks touch shared files.
   - On Google Antigravity, use `run_workflow` `pipeline(chapter_worksheets, run_worksheet)` where each stage invokes `agent(type_name="self", role=f"Execute {task_id}", schema=TASK_RESULT_SCHEMA, model="inherit")` with `agents/executor.md`, the worksheet path, the owning chapter `spec.md` path, and referenced `.agents/skills/` + `knowledge/` chapters so file reads and test logs stay out of the coordinator context.
   - Each `@executor` reads **only** its `Bounded Read Manifest` (`read_set <= 6` files + chapter `spec.md` + referenced skills/knowledge chapters); if unstated symbol dependencies would require broad codebase exploration, it fails closed as `state: blocked` rather than compacting its context window, and returns a concise `<= 30`-line structured receipt.

## Phase 3: Execute Declared Verification Strategy & Public-Seam TDD

| Strategy | Initial Evidence | Implementation & Final Evidence |
| --- | --- | --- |
| `behavior_tdd` | Write focused behavioral test(s) from the worksheet's Worked Test Matrix at the confirmed public seam in the canonical test module and run to confirm failure (Red). | Implement the minimal production change, rerun until Green (`exit 0`), and run fast lint/typecheck gates. |
| `regression_tdd` | Write the minimized reproduction test at the public seam in the canonical test module and confirm it fails (Red) with the defect symptom. | Implement the narrow fix, rerun the regression test and module suite until Green (`exit 0`). |
| `characterization` | Run the focused behavior baseline at the public seam and confirm it passes before refactoring. | Refactor/debloat while keeping the behavior baseline unchanged and Green (`exit 0`). |
| `static_validation` | Run the native validator, linter, or typechecker baseline. | Prove any new check catches a representative isolated violation, restore clean state, and verify exit code `0`. |
| `documentation_validation` | Run the Markdown, link, frontmatter, and example baseline. | Author present-tense docs/OKF chapters and verify all link, schema, and lint checks exit `0`. |
| `integration_acceptance` | Run the focused integration baseline. | Verify end-to-end composition and negative refusal paths exit `0`. |

### Public-Seam & Test-Quality Rules

- **The Interface Is the Test Surface**: Test strictly through confirmed public interfaces using domain terms from `knowledge/domains/<domain>.md`.
- **Never Write Implementation-Coupled or Tautological Tests**: Never mock the System Under Test, mock internal collaborators, test private methods, or recompute expected outputs with production logic; assert against concrete literals from the worksheet's Worked Test Matrix.
- **Canonical Test Files Only**: Add or update tests inside existing canonical module test files (`tests/<module>/test_<unit>.py`); never create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **When Tests Fail**: Follow the **Hypothesis-Driven Bug Diagnosis Loop** in [`discipline.md`](discipline.md). If 3 fixes fail in a row, stop, mark the task `blocked`, and route to `/flow:revise`.
- **Atomic Task Commit**: After verification exits `0`, each `@executor` updates its `tasks/<id>-<slug>.md` (`state: completed`, `commit: <sha>`, `last_verified_at`, `last_verified_commit`, `verification_evidence`, `claimed_by: null`, `claimed_at: null`) and owning `spec.md` checklist (`- [x] [<sha>] <id> — ...`) together with its owned `files:` and `tests:` in one atomic signed commit (`git commit -S -m "<type>(<scope>): <concise summary>"`), never using `git add -A` or `git add -f`.

## Phase 4: Chapter Closeout Sequence (Checkpoint &rarr; Present-Tense Sync &rarr; Review &rarr; Hard Stop)

As soon as all `1–4` tasks in the active chapter (or single-chapter flow) reach `completed` / `deferred`, execute all four closeout steps **before ending the coordinator turn**:

1. **Step 1 — Chapter Recovery Checkpoint**:
   - Run `debloat` checks across the chapter's touched files and execute the **Chapter / Phase Recovery Checkpoint** command (`lint` + chapter/module test suite), confirming exit code `0` and recording `last_verified_checkpoint`.
2. **Step 2 — Present-Tense Markdown, OKF, & Full-Plan Sync (Isolated Sync Subagent)**:
   - Dispatch an isolated Documentation & Plan Sync subagent (`type_name="self"` on Google Antigravity) to synchronize all living Markdown **before** code review:
     1. Update or create every `.agents/bundles/knowledge/**` chapter and user `README.md` / `docs/**` file owned by this chapter in present tense (`status: stable`, `<= 40`-line `<!-- truth: start -->` block, `sources:` + `[^id]:` footnotes, `verified:` stamp, frontmatter-free `index.md` catalogs).
     2. Rewrite `chapters/<ch_id>/spec.md`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` **in place in present tense**: reconcile any refined type/signature contracts across root `spec.md` and remaining downstream chapters (`chK..chNN`), update `[k/N files documented]` in `## 3. Documentation & OKF Knowledge Plan`, and rewrite `## 6. Current State & Remaining Plan Snapshot` with the verified baseline at `HEAD`, remaining chapters/tasks across the full plan, and active invariants—with **zero chronological history or revision logs** inside specs or docs.
     3. Prepend an ISO-dated `chapter-complete` entry to `.agents/bundles/log.md` and create a signed commit (`docs(<scope>): sync present-tense specs and knowledge for <ch_id>`).
3. **Step 3 — Zero-Context Chapter Code & Markdown-Sync Review**:
   - Dispatch isolated read-only `@code-reviewer` and `@quality-reviewer` subagents (`type_name="self"` on Google Antigravity, checking `git status --porcelain` afterward) across `chapter_base_commit..HEAD` ([`review.md`](review.md)).
   - Reviewers audit both production/test changes AND the synced `spec.md`, `chapters/index.md`, `knowledge/**`, and `docs/**` files for Spec Conformance, Deep-Module Seams, Present-Tense Full-Plan Roadmap Accuracy, and Zero-History Living-Doc Hygiene (`quality-review-v1`).
   - Remediate any `ADOPT` code or Markdown-sync findings in canonical files, rerun the Chapter Recovery Checkpoint (`exit 0`), and re-verify with the reviewers; let `<REVIEWED_HEAD_SHA>` be the verified `HEAD` commit SHA.
4. **Step 4 — Review Stamp, Pointer Advance, & Chapter-Boundary Hard Stop**:
   - Stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, `verified:`, and `state: completed` (`current_task: null`) in `chapters/<ch_id>/spec.md` (or single-chapter `specs/<flow_id>/spec.md`).
   - When `has_chapters: true`, update root `specs/<flow_id>/spec.md` and `chapters/index.md`: mark `- [x] [<REVIEWED_HEAD_SHA>] <ch_id> — ...`, set `last_reviewed_chapter: <ch_id>` and `last_reviewed_commit: <REVIEWED_HEAD_SHA>`, and advance `current_chapter` to the next remaining chapter (or set `current_chapter: null` when all chapters are `[x]`), then create a signed chapter-closeout metadata commit so `hooks/stop-check.{sh,ps1}` verifies `merge-base --is-ancestor <task_sha> <REVIEWED_HEAD_SHA>` cleanly.
   - **Hard Stop After One Chapter**: Stop immediately after closing the chapter—never automatically start executing the next chapter in the same turn. Report the completed chapter, `<REVIEWED_HEAD_SHA>`, remaining chapters from the full plan, and recommend running `/compact` (or starting a fresh session) before invoking `/flow:implement <flow_id>` for the next chapter (or `/flow:finish <flow_id>` when all chapters are complete).
