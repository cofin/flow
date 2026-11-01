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

1. **Zero-Context Correctness & Quality Review (`/flow:review`)**:
   - Compute the exact `base_commit..head_commit` range and changed file surface.
   - Dispatch zero-context reviewers (using Antigravity's `run_workflow` `parallel()` with `schema=` and persistent multi-turn reviewer handles when available, or isolated `@code-reviewer`, `@quality-reviewer`, and matching `.agents/agents/<domain>-reviewer` subagents) passing only disk paths (`spec.md`, `tasks/*.md`, `.agents/skills/`, and `knowledge/` chapters).
   - Adjudicate findings (`ADOPT` vs. `CONTEST` with evidence), remediate adopted findings in canonical files/tests, and re-verify with the reviewer.
2. **Finish Flow (`/flow:finish`)**:
   - Run the repository's full verification gates (`knowledge/workflow.md`), verify all tasks in `spec.md` are `[x] [<sha>]`, record any new architectural decisions in `knowledge/decisions/adr-NNN-<slug>.md`, and mark `spec.md` `state: completed`.
3. **Archive & Contract Flow (`/flow:archive`)**:
   - Invoke the `/flow:learn` contraction pass to promote durable architecture, patterns, domain rules, testing insights, and gotchas from `specs/<flow_id>/{spec.md,learnings.md,research/*,tasks/*}` into `.agents/bundles/knowledge/**` and `.agents/skills/**`.
   - Record an `archive` entry in `.agents/bundles/log.md`, remove the completed `.agents/bundles/specs/<flow_id>/` directory, and update `.agents/bundles/index.md`.
4. **Cleanup, Revert, or Validate (`/flow:cleanup`, `/flow:revert`, `/flow:validate`)**:
   - Run `debloat` across touched files (`/flow:cleanup`), revert designated task/flow commits safely (`/flow:revert`), or validate OKF bundle and skill integrity (`/flow:validate`).

## Guardrails

- Reviewers are strictly read-only and receive zero conversational planning history.
- Never delete a completed spec directory during `/flow:archive` until its durable discoveries and patterns have been synthesized into `.agents/bundles/knowledge/**` and logged in `.agents/bundles/log.md`.
- Preserve Git history and never create or mutate Git tags.

## Output

Return the review adjudication summary (`ADOPT` vs. `CONTEST`), verification command exit codes, updated `spec.md` state or `.agents/bundles/knowledge/` contraction report, and next action.

## Validation

Confirm all required review and verification gates passed with exit code `0`, `spec.md` and `tasks/*.md` states match Git history, and `.agents/bundles/index.md` and `log.md` are updated cleanly.
