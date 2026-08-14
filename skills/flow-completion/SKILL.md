---
name: flow-completion
description: "Use when reviewing, finishing, archiving, reverting, validating, or cleaning up Flow work after implementation or phase completion."
---

# Flow Completion

Use this lifecycle skill for review, finish, archive, revert, docs, validation, and final cleanup work.

<!-- quality-completion-policy: start -->
```yaml
contract: quality-completion-v1
authority: skills/flow/references/review.md
finish_gates: [verification, code_review, quality_review, finish]
archive_gates: [archive_candidate, verification, code_review, quality_review, archive]
runtime_dependency: agent_file_tools_only
evaluator_module: forbidden
```
<!-- quality-completion-policy: end -->

## Workflow

1. Run fresh verification before claiming a phase or flow is complete.
2. Dispatch correctness review on the exact candidate range, then always dispatch the read-only `quality-reviewer` on that same range using the contract in [Review](../flow/references/review.md). A waiver never replaces dispatch.
3. For every Critical/Important quality finding, stop completion and route through `revise` to create or adjust a remediation task. After it executes, rerun affected verification and correctness review, then dispatch a fresh quality review on the new exact range.
4. Put phase evidence in the spec-only `checkpoint` payload, targeting the last functional commit. After the checkpoint succeeds, an optional detailed Git note may be appended and its result recorded through the idempotent state-sidecar `note` operation. Never create an empty checkpoint commit and never push notes automatically.
5. Archive completed flows as a contraction — synthesize, log, delete: RE-synthesize durable learnings into project-shaped knowledge chapters, add one `.agents/bundles/log.md` entry (date, flow_id, one-line outcome, final commit SHA), then delete the spec directory. `.agents/bundles/specs/` holds only planned and active flows; git history is the archive.
6. Before archive mutation, render the complete candidate manifest in a disposable local review range. Run verification, correctness review, and mandatory quality review on its exact base/head; pass that range and the byte-identical manifest to `archive`. Any content change invalidates the report and requires a new candidate and reviews.
7. Before deleting, verify recoverability with `git ls-files` — untracked bundles are unrecoverable and need explicit user confirmation. Commit the deletion for tracked bundles only.
8. For reverts, identify the logical Flow scope and avoid unrelated user changes.

## Guardrails

- No completion claim without fresh verification evidence.
- No finish/archive without a fresh `QualityReport` for the exact candidate range, even when a user waives a named finding.
- Quality review is read-only; findings become planned remediation rather than opportunistic edits.
- Do not archive flows whose code, tests, task metadata, and markdown views disagree.
- Do not revert unrelated files or user changes.
- Rewrite knowledge chapters as coherent current-state documentation — never append dated entries, "from: {flow_id}" attributions, changelog lines, or completion notes; history belongs in `.agents/bundles/log.md` only.
- Treat `extracted_learnings.md` as transient: delete it after synthesis, never leave it behind.
- Never delete an untracked spec bundle without explicit user confirmation.
- Git notes are supplementary evidence, never state or recovery authority. Their absence or attachment failure cannot block archive once canonical Markdown evidence satisfies the archive contract.
- Never create or mutate Git tags, including as a fallback for notes, checkpoints, or archive evidence.

## Validation

- Run full relevant test and validation commands before finish/archive.
- Confirm task metadata files are closed or skipped.
- Confirm knowledge chapters read as current-state docs and `log.md` carries the archive entry; after archive, the spec directory is gone from `specs/`.

## References Index

- [Review](../flow/references/review.md)
- [Finish](../flow/references/finish.md)
- [Archive](../flow/references/archive.md)
- [Revert](../flow/references/revert.md)
- [Docs](../flow/references/docs.md)
- [Validate](../flow/references/validate.md)
- [Cleanup](../flow/references/cleanup.md)
- [Git Notes](../../docs/git-notes.md)

## Example

User: "Finish this flow."

Action: run verification, review against the spec, verify task files are closed, sync markdown, elevate reusable patterns, and present finish options.
