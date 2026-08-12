---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying TDD, recording task notes, committing, and updating task file state."
---

# Flow Execution

Use this lifecycle skill when implementation starts after a Flow plan or ready task file exists.

## Workflow

1. Select ready work from `.agents/bundles/specs/<flow_id>/tasks/*.md` (YAML frontmatter `state: open` and dependencies resolved) and claim it (state to `in_progress`).
2. Read the relevant spec, task notes, patterns, affected files, and validation commands.
3. Record investigation findings directly inside the task file's `## Notes & Discoveries` section.
4. Follow red-green-refactor: write the failing test, verify the failure, implement minimally, verify green, then refactor.
5. Commit targeted changes, retrieve the commit SHA, and close the task (status to `closed` and write commit SHA to frontmatter).

## Guardrails

- Do not manually edit task status markers in markdown.
- Do not skip failing-test evidence for behavior changes.
- Do not silently descope messy tasks; refine or ask how to prioritize.
- Preserve unrelated user changes and keep edits scoped to the claimed task.

## Validation

- Verify the new test failed for the intended reason before implementation.
- Run focused tests after each task and the repo’s aggregate verification before phase completion.
- Record commit reference and discoveries inside the task markdown file.

## References Index

- [Implement](../flow/references/implement.md)
- [Discipline](../flow/references/discipline.md)

## Example

User: "Implement auth flow."

Action: claim the next ready task file, add code-path notes to `## Notes & Discoveries`, write a failing auth test, implement the minimal behavior, verify, commit, and update the task status to closed with the commit SHA.
