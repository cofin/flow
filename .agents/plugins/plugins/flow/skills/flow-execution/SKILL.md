---
name: flow-execution
description: "Use when implementing Flow tasks from Beads or spec.md, claiming ready work, applying TDD, recording task notes, committing, and syncing after task state changes."
---

# Flow Execution

Use this lifecycle skill when implementation starts after a Flow plan or ready Beads task exists.

## Workflow

1. Select ready work from `bd ready` and claim it before editing.
2. Read the relevant spec, notes, patterns, affected files, and validation commands.
3. Record investigation findings with `bd note`.
4. Follow red-green-refactor: write the failing test, verify the failure, implement minimally, verify green, then refactor.
5. Commit targeted changes, close the Beads task with evidence, and sync markdown when policy requires it.

## Guardrails

- Do not manually edit task status markers in markdown.
- Do not skip failing-test evidence for behavior changes.
- Do not silently descope messy tasks; refine or ask how to prioritize.
- Preserve unrelated user changes and keep edits scoped to the claimed task.

## Validation

- Verify the new test failed for the intended reason before implementation.
- Run focused tests after each task and the repo’s aggregate verification before phase completion.
- Record test output, commit reference, and closure reason in Beads.

## References Index

- [Implement](../flow/references/implement.md)
- [Discipline](../flow/references/discipline.md)

## Example

User: "Implement auth flow."

Action: claim the next ready Beads task, add code-path notes, write a failing auth test, implement the minimal behavior, verify, commit, close the task, and sync.
