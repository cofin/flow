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

1. **Zero-Context Correctness, Standards, & Quality Review (`/flow:review`)**:
   - Compute the exact `base_commit..head_commit` range and changed file surface.
   - Dispatch isolated zero-context reviewers (`run_workflow` `parallel()` with `schema=` and persistent reviewer handles when available, or isolated `@code-reviewer`, `@quality-reviewer`, and matching `.agents/agents/<domain>-reviewer` subagents) passing only disk paths (`spec.md`, `tasks/*.md`, `.agents/skills/`, and `knowledge/` chapters) under the **Zero-Context Isolation Rules**.
   - Evaluate **Spec Conformance**, **Repository Standards, Deep-Module Seams, & Baseline Structural Code Smells**, and **Mandatory Quality & Debloat Review (`quality-review-v1`)**.
   - Adjudicate findings (`ADOPT` vs. `CONTEST` vs. `ESCALATE`), remediate adopted findings in canonical files/tests, and re-verify with the reviewer.
2. **Finish Flow (`/flow:finish`)**:
   - Verify branch-local completion eligibility (or scope-cap follow-up tasks as `deferred` `[-]`), run full verification gates (`knowledge/workflow.md`), confirm review gates passed, evaluate the **ADR Filter** (`knowledge/decisions/adr-NNN-<slug>.md`), mark `spec.md` `state: completed`, and present the structured completion options (`Archive flow now`, `Archive and open/update PR`, `Merge locally and archive`, `Discard work`).
3. **Archive & Contract Flow (`/flow:archive`)**:
   - Execute the `/flow:learn` contraction pass across all OKF knowledge namespaces and `.agents/skills/**` before deletion.
   - Enforce strict write ordering: write `knowledge/**` + `.agents/skills/**` first, prepend the `archive` entry to `.agents/bundles/log.md` second, and delete `.agents/bundles/specs/<flow_id>/` last.
4. **Cleanup, Revert, or Validate (`/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Run groundskeeping and `debloat` across touched files (`/flow:cleanup`), revert designated task/phase/flow commits safely (`/flow:revert`), or run the OKF bundle, skill, and spec validator (`/flow:validate`).

## Guardrails

- Reviewers are strictly read-only isolated agents and receive zero conversational history, rationale, or leading hints.
- Never delete a completed spec directory during `/flow:archive` until its durable discoveries and patterns have been synthesized into `.agents/bundles/knowledge/**` and logged in `.agents/bundles/log.md`.
- Preserve Git history and never create or mutate Git tags.

## Output

Return the review adjudication summary (`ADOPT` / `CONTEST` / `ESCALATE`), verification command exit codes, updated `spec.md` state or `.agents/bundles/knowledge/` contraction report, and next action.

## Validation

Confirm all required review and verification gates passed with exit code `0`, `spec.md` and `tasks/*.md` states match Git history, and `.agents/bundles/index.md` and `log.md` are updated cleanly.
