---
name: flow-completion
description: "Use when reviewing, finishing, archiving, reverting, validating, or cleaning up Flow work after implementation or phase completion."
---

# Flow Completion

Use this lifecycle skill for review, finish, archive, revert, docs, validation, and final cleanup work.

## Workflow

1. Run fresh verification before claiming a phase or flow is complete.
2. Review implementation against the spec, tests, patterns, security, architecture, and performance risks as appropriate.
3. Capture reusable learnings and elevate patterns into project knowledge.
4. Archive completed flows and preserve current-state guidance.
5. For reverts, identify the logical Flow scope and avoid unrelated user changes.

## Guardrails

- No completion claim without fresh verification evidence.
- Do not archive flows whose code, tests, Beads tasks, and markdown views disagree.
- Do not revert unrelated files or user changes.
- Keep knowledge chapters current-state oriented; avoid historical logs outside learnings.

## Validation

- Run full relevant test and validation commands before finish/archive.
- Confirm Beads tasks are closed or intentionally blocked/deferred.
- Confirm `spec.md`, learnings, patterns, and knowledge chapters reflect the current state.

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

Action: run verification, review against the spec, close or explain remaining tasks, sync markdown, elevate reusable patterns, and present finish options.
