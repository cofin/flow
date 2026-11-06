---
name: flow-completion
description: "Use when reviewing (/flow:review), finishing (/flow:finish), archiving (/flow:archive), cleaning up (/flow:cleanup), reverting (/flow:revert), or validating (/flow:validate) Flow work."
disable-model-invocation: true
---

# Flow Completion

<!-- lifecycle-ownership: owner=flow-completion; operations=review,finish,archive,cleanup,revert,validate -->

## Trigger

Use for `review` ([`../flow/references/review.md`](../flow/references/review.md)), `finish` ([`../flow/references/finish.md`](../flow/references/finish.md)), `archive` ([`../flow/references/archive.md`](../flow/references/archive.md)), `cleanup` ([`../flow/references/cleanup.md`](../flow/references/cleanup.md)), `revert` ([`../flow/references/revert.md`](../flow/references/revert.md)), and `validate` ([`../flow/references/validate.md`](../flow/references/validate.md)).

<!-- quality-completion-policy: start -->
```yaml
contract: quality-completion-v1
authority: skills/flow/references/review.md
finish_gates: [verification, code_review, quality_review, finish]
archive_gates: [archive_candidate, verification, code_review, quality_review, knowledge_contraction, archive]
runtime_dependency: agent_file_tools_only
```
<!-- quality-completion-policy: end -->

## Workflow

1. **Zero-Context Chapter or Flow Correctness, Markdown-Sync, & Quality Review (`/flow:review [flow_id] [chapter_id]`)**:
   - Compute the exact `base_commit..head_commit` range for the target chapter or full flow and inspect the changed code, test, spec, OKF, and doc surface.
   - Dispatch isolated zero-context reviewers (`run_workflow` `parallel()` with `type_name="self"` on Google Antigravity, checking `git status --porcelain` afterward; isolated `@code-reviewer`, `@quality-reviewer`, and matching `.agents/agents/<domain>-reviewer` subagents elsewhere) passing only disk paths (`spec.md`, `chapters/index.md`, `chapters/<ch_id>/spec.md`, `tasks/*.md`, `.agents/skills/`, and `knowledge/` chapters) under the **Zero-Context Isolation Rules**.
   - Evaluate **Spec Conformance**, **Present-Tense Markdown, Full-Plan Roadmap, & Doc-Sync Conformance**, **Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells**, and **Mandatory Quality, Zero-History Doc Hygiene, & Debloat Review (`quality-review-v1`)**.
   - Adjudicate findings (`ADOPT` vs. `CONTEST` vs. `ESCALATE`), remediate adopted code or Markdown-drift findings, re-verify, and stamp `last_reviewed_commit: <REVIEWED_HEAD_SHA>` on the reviewed chapter/flow `spec.md`.
2. **Finish Flow (`/flow:finish`)**:
   - Verify branch-local completion eligibility: every chapter (`chapters/<ch_id>/spec.md`) and task worksheet is `completed` (or `deferred` `[-]`) with a valid `last_reviewed_commit` covering all chapter task commits and `[N/N files documented]` in `## 3. Documentation & OKF Knowledge Plan`.
   - Run full verification gates (`knowledge/workflow.md`), confirm flow-wide review gates passed, evaluate the **ADR Filter** (`knowledge/decisions/adr-NNN-<slug>.md`), mark root `spec.md` `state: completed` (`current_chapter: null`, `current_task: null`), and present the structured completion options (`Archive flow now`, `Archive and open/update PR`, `Merge locally and archive`, `Discard work`).
3. **Archive & Contract Flow (`/flow:archive`)**:
   - Execute the subagent-sharded `/flow:learn` contraction pass (`1` subagent per domain when `>= 2` domains) across all chapters, OKF knowledge namespaces, and `.agents/skills/**` before deletion.
   - Enforce strict write ordering: write `knowledge/**` + `.agents/skills/**` first, prepend the `archive` entry to `.agents/bundles/log.md` second, and delete `.agents/bundles/specs/<flow_id>/` (including `chapters/`) last.
4. **Cleanup, Revert, or Validate (`/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Run groundskeeping and `debloat` across touched files (`/flow:cleanup`), revert designated `task`, `chapter`, `phase`, or `flow` commits while resetting chapter/root roadmaps in present tense (`/flow:revert`), or run the OKF v0.2 multi-chapter bundle, hook, skill, and spec validator (`/flow:validate`).

## Guardrails

- Reviewers are strictly read-only isolated agents and receive zero conversational history, rationale, or leading hints.
- Never stamp `last_reviewed_commit` or close a chapter/flow until both code/tests AND present-tense Markdown/OKF/user docs (`spec.md`, `chapters/index.md`, `knowledge/**`, `docs/**`) are synchronized and verified free of historical prose.
- Never delete a completed spec directory during `/flow:archive` until its durable discoveries and patterns across all chapters have been synthesized into `.agents/bundles/knowledge/**` and logged in `.agents/bundles/log.md`.
- Preserve Git history and never create or mutate Git tags.

## Output

Return the review adjudication summary (`ADOPT` / `CONTEST` / `ESCALATE`), verification command exit codes, updated `spec.md` state or `.agents/bundles/knowledge/` contraction report, and next action.

## Validation

Confirm all required review and verification gates passed with exit code `0`, `spec.md` and `tasks/*.md` states match Git history, and `.agents/bundles/index.md` and `log.md` are updated cleanly.
