---
name: flow-completion
description: "Use when reviewing, finishing, archiving, reverting, validating, or cleaning up Flow work after implementation or phase completion."
---

# Flow Completion

Use this lifecycle skill for review, finish, archive, revert, docs, validation, and final cleanup work.

## Workflow

1. Run fresh verification before claiming a phase or flow is complete.
2. Review implementation against the spec, tests, patterns, security, architecture, and performance risks as appropriate.
3. Archive completed flows as a contraction — synthesize, log, delete: RE-synthesize durable learnings into the knowledge chapters, add one `.agents/bundles/log.md` entry (date, flow_id, one-line outcome, final commit SHA), then delete the spec directory. `.agents/bundles/specs/` holds only planned and active flows; git history is the archive.
4. Before deleting, verify recoverability with `git ls-files` — untracked bundles are unrecoverable and need explicit user confirmation. Commit the deletion for tracked bundles only.
5. For reverts, identify the logical Flow scope and avoid unrelated user changes.

## Guardrails

- No completion claim without fresh verification evidence.
- Do not archive flows whose code, tests, task metadata, and markdown views disagree.
- Do not revert unrelated files or user changes.
- Rewrite knowledge chapters as coherent current-state documentation — never append dated entries, "from: {flow_id}" attributions, changelog lines, or completion notes; history belongs in `.agents/bundles/log.md` only.
- Treat `extracted_learnings.md` as transient: delete it after synthesis, never leave it behind.
- Never delete an untracked spec bundle without explicit user confirmation.

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

## Example

User: "Finish this flow."

Action: run verification, review against the spec, verify task files are closed, sync markdown, elevate reusable patterns, and present finish options.
