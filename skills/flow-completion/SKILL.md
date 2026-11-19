---
name: flow-completion
description: "Use when reviewing (/flow:review), finishing (/flow:finish), archiving (/flow:archive), cleaning up (/flow:cleanup), reverting (/flow:revert), or validating (/flow:validate) Flow work."
disable-model-invocation: true
---

# Flow Completion

<!-- lifecycle-ownership: owner=flow-completion; operations=review,finish,archive,cleanup,revert,validate -->

## Trigger

Use for `review` ([`../flow/references/review.md`](../flow/references/review.md)), `finish` ([`../flow/references/finish.md`](../flow/references/finish.md)), `archive` ([`../flow/references/archive.md`](../flow/references/archive.md)), `cleanup` ([`../flow/references/cleanup.md`](../flow/references/cleanup.md)), `revert` ([`../flow/references/revert.md`](../flow/references/revert.md)), and `validate` ([`../flow/references/validate.md`](../flow/references/validate.md)).

## Workflow

1. **Independent Chapter or Flow Review (`/flow:review [flow_id] [chapter_id]`)**:
   - Compute the exact `base_commit..head_commit` range for the target chapter or full flow and inspect the changed code, test, spec, OKF, and doc surface.
   - Dispatch isolated reviewers planned via `flow review plan --json`. Run `workflows/flow-dual-review/workflow.py` on Google Antigravity (checking `git status --porcelain` afterward), or isolated `@code-reviewer`, `@quality-reviewer`, and matching `.agents/agents/<domain>-reviewer` subagents elsewhere ([`../flow/references/orchestration.md`](../flow/references/orchestration.md)). Pass only disk paths (`spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, `tasks/*.md`, `.agents/skills/`, and `knowledge/`).
   - Evaluate spec conformance, present-tense Markdown and doc sync, repository standards and deep-module design, and quality, current-state doc hygiene, and debloat.
   - Decide on each finding (`ADOPT` vs. `CONTEST` vs. `ESCALATE`), fix adopted code or doc-drift findings, re-verify, and stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` on the reviewed chapter/flow `spec.md`.
2. **Finish Flow (`/flow:finish`)**:
   - Run `/flow:validate` on `<flow_id>` to verify the completion check. Confirm zero open chapters or tasks remain, every `deferred` item has `deferred_by: "user"` and `deferred_reason`, and every task commit touched a declared path in `files:` or `tests:`. Also verify each completed chapter has a valid `last_reviewed_commit` and `[N/N files documented]` is satisfied. If `planning_quality: degraded` is present on `spec.md`, remind the user before sign-off.
   - Run the **Full Release Check** (`knowledge/workflow.md`, including any `> 60s` full test suite deferred during chapter checks) and confirm flow-wide reviews passed. Evaluate the **ADR Filter** (`knowledge/decisions/adr-NNN-<slug>.md`), mark root `spec.md` `state: completed` (`current_chapter: null`, `current_task: null`), and present completion options (`Archive flow now`, `Archive and open/update PR`, `Merge locally and archive`, `Discard work`).
3. **Archive Flow (`/flow:archive`)**:
   - Verify `/flow:validate` passes completion checks on `<flow_id>` (`state: completed` with zero open chapters/tasks) before touching `specs/<flow_id>/`. In linked `local-only` Git worktrees, apply `.agents/` updates directly to the primary checkout's `.agents/` bundle.
   - Run the parallel `/flow:learn` pass (`1` subagent per domain when `>= 2` domains) across all chapters, OKF knowledge namespaces, and `.agents/skills/**` before deletion.
   - Follow strict archive order: write `knowledge/**` + `.agents/skills/**` first, prepend the `archive` entry to `.agents/bundles/log.md` second, delete `.agents/bundles/specs/<flow_id>/` (including `chapters/`) last, and run `/flow:validate` afterward to confirm zero broken links.
4. **Cleanup, Revert, or Validate (`/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Run groundskeeping and `debloat` across touched files (`/flow:cleanup`), or revert designated `task`, `chapter`, `phase`, or `flow` commits while resetting roadmaps in present tense (`/flow:revert`). Run `/flow:validate` to check OKF bundles, workflows, schema cards, completion checks, worktrees, hooks, skills, and specs.

## Guardrails

- Reviewers are read-only isolated agents and receive zero chat history, rationale, or leading hints.
- Require verification, code review, and quality review before `/flow:finish` or `/flow:archive`.
- Never stamp `last_reviewed_commit` or close a chapter/flow until both code/tests and present-tense Markdown/OKF/user docs (`spec.md`, `chapters/index.md`, `knowledge/**`, `docs/**`) are synced and free of stale history.
- Never delete a completed spec directory during `/flow:archive` until its durable discoveries and patterns across all chapters are captured into `.agents/bundles/knowledge/**` and logged in `.agents/bundles/log.md`.
- Preserve Git history and never create or mutate Git tags.

## Output

Return the review summary (`ADOPT` / `CONTEST` / `ESCALATE`), check exit codes, updated `spec.md` state or `.agents/bundles/knowledge/` archive report, and next action.

## Validation

Confirm all required review and verification checks passed with exit code `0`, `spec.md` and `tasks/*.md` states match Git history, and `.agents/bundles/index.md` and `log.md` are updated.
