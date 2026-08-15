---
type: Guide
title: Project Workflow
---

# Project Workflow

<!-- truth: start -->
- Task files under `.agents/bundles/specs/<flow_id>/tasks/` are authoritative; `spec.md` is the synchronized checklist and continuity view.
- Use the repository's canonical setup, focused-test, lint/type/build, and aggregate verification commands. Replace the placeholders below during setup.
- Every task declares and justifies one `verification_strategy`; only observable behavior and defect correction require an initial failing test.
- Record durable findings in the task's `## Notes & Discoveries` and preserve unrelated worktree changes.
- Consumer operational skills install only under `.agents/skills/`. Product, knowledge, research, and specs remain under `.agents/bundles/`.
- Flow never creates, moves, force-updates, or deletes Git tags, and never pushes automatically.
<!-- truth: end -->

## Canonical commands

Setup must replace examples with repository-native commands and expected outcomes. Prefer aggregate wrappers over ad hoc tool calls.

```bash
# setup: make install | uv sync | npm install
# focused tests: make test | uv run pytest tests/path.py -q | npm test
# lint/type/build: make lint | make type-check | npm run check
# aggregate verification: make check | just check | task verify
```

Use non-interactive modes in automation. Before claiming a result, run the exact command freshly, read its complete output and exit status, and report limitations.

## Direct-read continuity

1. Resolve `.agents/setup-state.json:root_directory`, defaulting to `.agents/`.
2. Read unresolved transaction journals under `<configured-root>/tasks/transactions/` before normal work.
3. Read active/completed spec frontmatter and Continuity Snapshot, then all task frontmatter.
4. Verify plan identity, state revision bounds, current claim, dependencies, and checklist agreement.
5. Select an explicit task, the sole in-progress task, or the first ready task ordered by priority, creation time, and id.
6. Read the complete worksheet, direct dependencies, newest discoveries, and only the relevant project-shaped knowledge chapters.

Hooks and prior conversation are routing hints, not authority. State operations use ordinary file tools and the packaged Flow state contract; there is no Flow CLI or consumer Python runtime.

## Task and state operations

A task is ready when `state: open`, all `depends_on` tasks are `closed`, its worksheet is complete, and its plan identity matches the spec.

| Operation | Purpose |
| --- | --- |
| `claim` | Move one ready task to `in_progress` and set the spec current task. |
| `discover` | Append investigation evidence without changing the worksheet. |
| `block` / `unblock` | Record or resolve an exact blocker and next step. |
| `release` | Return an in-progress task to open when the claimant stops. |
| `checkpoint` | Bind fresh task, phase, or plan evidence. |
| `close` | Close the sole claimed task with commit-bound evidence. |
| `revise` | Change approved plan-bearing content and increment plan identity. |
| `reconcile` | Update derived spec checklist/snapshot from task-file truth. |
| `complete` / `archive` | Finish verified work, synthesize knowledge, log, then contract the spec directory. |
| `recover` | Resume or roll back one recorded interrupted transaction. |

Never edit task/spec state or checklist markers independently. Apply task changes before spec changes in one journaled state transaction and reread the result. A worksheet mismatch stops production mutation and routes through `discover`, `block`, and `revise` or `refine`.

## Verification strategies

| Strategy | Select for | Required evidence |
| --- | --- | --- |
| `behavior_tdd` | New observable behavior | Focused behavior fails because it is absent; minimal implementation makes it green. |
| `regression_tdd` | Defect correction | Focused reproduction demonstrates the defect; the narrow fix makes it green. |
| `characterization` | Behavior-preserving refactor/deletion | Green focused baseline before and unchanged behavior after. |
| `static_validation` | Manifest, config, generated surface, tooling | Native parser/lint/type/build; isolated representative violation proves a new/replacement gate fails with the expected diagnostic. |
| `documentation_validation` | Links, examples, docs structure | Docs-native baseline and final link/example/build/structure checks. |
| `integration_acceptance` | Composition of existing contracts | Green focused baseline; end-to-end scenario plus injected negative states proving refusal paths. |

A waiver does not replace the selected strategy. It requires an explicit rationale, approver, and compensating evidence. Never manufacture a failing unit test for documentation, configuration, generated output, prose, or behavior-preserving cleanup. Integration acceptance routes missing implementation through revise instead of absorbing it.

## Execution sequence

1. Preflight the worksheet, live targets, dependencies, strategy, plan identity, state revision, and worktree.
2. Claim the task through the state contract.
3. Record discoveries in `## Notes & Discoveries`.
4. Obtain the strategy's required initial evidence.
5. Make the minimum worksheet-scoped change.
6. Obtain focused green evidence, refactor only while green, and run relevant aggregate gates.
7. Review the diff and stage exact task-owned paths only.
8. Commit once with a conventional message.
9. Close the task with the commit, exact commands/results, and checked acceptance criteria; reconcile the spec in the same state transaction.

Use one task per delegated invocation and one functional commit per task. Never stage broadly in a shared or dirty checkout. Commits remain local unless the user separately authorizes publication.

## Low-signal test and gate policy

Reject tests that lock incidental prompt phrases, private implementation shape, duplicate snapshots, or file existence without an operational contract. Prefer native parser, lint, type, and build contracts to source scanners when they express the complete rule. Retain tests for observable behavior, public contracts, proven regressions, error paths, interoperability, and operationally meaningful structure such as signatures, exports, hashing, memory layout, compilation, serialization, and isolation.

When replacing a gate, prove the replacement against an isolated violation before removing the old check. Confirm aggregate discovery includes new and untracked files where relevant.

## Commits and checkpoints

Use `<type>(<scope>): <description>` and stage exact paths. Do not force-add ignored Flow artifacts. A phase checkpoint records affected task ids, the last functional commit, and fresh aggregate evidence; never create an empty checkpoint commit.

Flow may append supplementary Git notes under `refs/notes/flow` only after the canonical Markdown transaction succeeds. Notes are optional, stay local by default, and never become state authority. Git tags are prohibited as evidence or fallback transport.

## Knowledge lifecycle

1. **Capture:** append dated discoveries to the owning task and reusable learnings to the flow's `learnings.md`.
2. **Synthesize:** integrate reusable current-state guidance into the best matching chapter anywhere under `.agents/bundles/knowledge/**/*.md`; preserve project-shaped nesting such as `data-model/`, `app-design/`, `standards/`, or `domains/`.
3. **Log:** history belongs in `.agents/bundles/log.md`, not in current-state knowledge prose.
4. **Contract:** after verified completion and archive review, delete the archived spec directory; Git history is the archive.

Operational project skills live only at `.agents/skills/`. Never create `.agents/bundles/skills/`.

## Quality gates

Before close or checkpoint, require:

- worksheet acceptance criteria satisfied with fresh evidence;
- selected verification strategy followed, including isolated gate proof when required;
- focused and relevant aggregate commands green;
- repository-defined lint, type, build, docs, coverage, security, and performance gates run when applicable;
- no accidental public API, typing, performance, import-boundary, or behavior change;
- no unrelated paths staged and `git diff --check` clean;
- discoveries and verification limitations recorded.

Coverage follows repository and worksheet requirements. Compare affected lines/branches when deleting behavioral tests; there is no universal percentage or one-test-file-per-module mandate.
