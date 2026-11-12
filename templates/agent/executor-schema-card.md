# Flow Executor Schema Card

Self-contained execution and present-tense synchronization contract for `/flow:implement`. Stay strictly inside the active chapter's `spec.md`, its `tasks/*.md` worksheets, and their `read_set` files—never browse plugin reference documentation or unrelated chapters.

## 1. Chapter-Batch Execution & Public-Seam TDD

- **Batch Edits Across the Active Chapter**: Implement the active chapter's `1..4` vertical-slice worksheets (`t01..t0K`) in dependency order within a single warm pass so shared production modules and canonical unit test files (`tests/<module>/test_<unit>.*`) are read and edited coherently once.
- **Public-Seam Integrity**: Test strictly through confirmed public interfaces with parameterized cases and concrete Worked Test Matrix literals. Never mock the System Under Test, write tautological assertions, use inline `#` restatement comments in Python, or create standalone `test_*remediation*.py` / `test_*audit*.py` files.
- **Fail-Closed Preflight & Escalation**: If target `path/to/file::Symbol` anchors are missing or contracts contradict live code, stop before editing production files, mark the affected task `state: blocked` (`[!]`) with `blocked_reason` and `unblock_condition`, and route to `/flow:revise`. Apply the Hypothesis-Driven Bug Diagnosis Loop on unexpected failures; escalate after `3` failed fix attempts.
- **Anti-Skip Rule**: Never mark a chapter or task `completed` without running verification (`exit 0`) and modifying its declared `files:`/`tests:`, and never mark a chapter or task `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

## 2. Fast Verification Cadence & Sandbox-Safe Permissions

- **Validate Once per Chapter (`< 60s` Fast Gate)**: After applying the chapter's code and unit test edits, run the repository's fast static check (`make lint` or offline `uv run --no-sync ruff check` + `mypy`/`pyright`) plus **only** the targeted unit test file(s) declared in the chapter's `tests:` (`uv run --no-sync pytest <target_test_file> -q`).
- **Minimize Full Test Suite Runs**: Never run slow (`> 60s` or container-backed) full test suites between tasks or at intermediate chapter boundaries; reserve full test suites for `/flow:finish` or CI.
- **Worktree `.venv` Usage**: When `.venv` is symlinked from the primary checkout, run `uv run --no-sync ...` or `.venv/bin/...` directly—never run `make install` or `uv sync` unless `pyproject.toml` changed.
- **Prefix-Matchable Offline Commands**: Inside background workflows, never pass `BypassSandbox: true`, never invoke network-fetching wrappers (`npx --yes`), and avoid command substitutions (`$(...)`) or `env` prefixes so granted permissions inherit cleanly.

## 3. Commit-SHA Sequencing & Pre-Review Present-Tense Sync

1. **Commit Code & Tests First**: Stage only the chapter's owned `files:` and `tests:` paths and run `git commit -S -m "<type>(<scope>): <concise summary>"`. Capture `<CODE_SHA>` via `git rev-parse --short HEAD`. *(If running inside a sandboxed background workflow where `.git/` is read-only and `git commit` is denied, do not retry or stall—leave edits on disk, sync Markdown below with `commit: pending_coordinator`, and return `commit_deferred_to_coordinator: true` with exact `files_modified` so the coordinator commits cleanly.)*
2. **Present-Tense Sync Commit (Never `git commit --amend`)**: Update `tasks/*.md` (`state: completed`, `commit: <CODE_SHA>`, `last_verified_commit: <CODE_SHA>`), rewrite `chapters/<ch_id>/spec.md` (`- [x] [<CODE_SHA>]`), `chapters/index.md`, root `specs/<flow_id>/spec.md` (`[k/N files documented]` and `## 6. Current State & Remaining Plan Snapshot`), affected `.agents/bundles/knowledge/**` + `docs/**` in present tense (zero historical prose, zero body `---` rules), prepend an entry to `.agents/bundles/log.md`, validate via `/flow:validate`, and create the sync commit before Zero-Context Chapter Review.
