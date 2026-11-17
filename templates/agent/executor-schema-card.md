# Flow Executor Schema Card

Self-contained execution and present-tense sync contract for `/flow:implement`.
Stay inside the active chapter's `spec.md`, its `tasks/*.md` worksheets, and their `read_set` files.
Never browse plugin reference docs or unrelated chapters.

## 1. Chapter-Batch Execution and TDD

- **Group Edits**: Implement the assigned tasks (`tasks_per_worker`, default `<= 4`) or pre-built briefs from `flow-cli.mjs tasks plan --briefs` in dependency order. Read and edit shared code and canonical test files (`tests/<module>/test_<unit>.*`) once per pass.
- **Public-Interface Testing**: Test through confirmed public interfaces with parameterized test cases. Never mock real code, write mock-only tests, add inline `#` comments in Python, or create standalone `test_*remediation*.py` or `test_*audit*.py` files.
- **Preflight and Blocking**: If target `path/to/file::Symbol` anchors are missing or contradict live code, stop without editing production files. Mark the task `state: blocked` (`[!]`) with `blocked_reason` and `unblock_condition`, and route to `/flow:revise`.
- **Bug Diagnosis**: Use structured bug diagnosis on unexpected failures; stop and mark `blocked` after `3` failed fix attempts.
- **Completion Check**: Never mark a chapter or task `completed` without `exit 0` verification and edits to its declared `files:`/`tests:`. Never mark a chapter or task `deferred` or `skipped` without `deferred_by: "user"` and `deferred_reason`.

## 2. Fast Checks and Sandbox Commands

- **Validate Once (`< 60s` Chapter Check)**: Run the commands in `## Verification` plus workspace-resolved lint and targeted unit test commands from `.agents/setup-state.json` or project config (`Makefile`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`).
- **Skip Slow Suites Mid-Flow**: Never run slow (`> 60s` or container-backed) full test suites between tasks or intermediate chapters; reserve full suites for `/flow:finish` or CI.
- **Existing Environments**: When a project `.venv` exists with `uv`, prefer offline `uv run --no-sync ...` or direct `.venv/bin/...` executables unless lockfiles changed.
- **Sandbox-Safe Commands**: Inside background workflows, never pass `BypassSandbox: true`, never run network-fetching wrappers (`npx --yes`), and avoid `$(...)` or `env` prefixes so permissions stay prefix-matchable.

## 3. Commit Order and Present-Tense Sync

1. **Commit Code and Tests First**: Stage only the chapter's owned `files:` and `tests:` paths and run `git commit -S -m "<type>(<scope>): <concise summary>"`. Capture `<CODE_SHA>` via `git rev-parse --short HEAD`.
2. **Read-Only `.git/` Fallback**: If `.git/` is read-only inside a workflow sandbox, do not retry `git commit`. Leave edits on disk, sync Markdown with `commit: pending_coordinator`, and return `commit_deferred_to_coordinator: true` with exact `files_modified`.
3. **Present-Tense Sync Commit (Never `git commit --amend`)**: Update `tasks/*.md` (`state: completed`, `commit: <CODE_SHA>`, `last_verified_commit: <CODE_SHA>`), `chapters/<ch_id>/spec.md` (`- [x] [<CODE_SHA>]`), `chapters/index.md`, and root `spec.md` (`[k/N files documented]` and `## 6. Current State & Remaining Plan Snapshot`).
4. **Docs and Validation**: Update affected `.agents/bundles/knowledge/**` and `docs/**` in present tense (current state only, no body `---` rules), prepend an entry to `.agents/bundles/log.md`, run `/flow:validate`, and commit the sync before independent review.
