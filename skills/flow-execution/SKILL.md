---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying TDD, recording task notes, committing, and updating task file state."
---

# Flow Execution

Use this lifecycle skill when implementation starts after a Flow plan or ready task file exists.

## Workflow

1. **Read Configuration:** Check `use_branched_workspaces` in `.agents/config.json` (default to `false` if missing).
2. **Select Ready Work:** Select ready work from `.agents/bundles/specs/<flow_id>/tasks/*.md` (YAML frontmatter `state: open` and dependencies resolved). **Refinement gate:** if the task file is a stub (missing its Objective/Context/Steps/Verification/Acceptance Criteria worksheet sections), do NOT execute it — route through `flow-refine` first. Claim the task (state to `in_progress`) only once its worksheet is Ready.
3. **Determine Execution Strategy:**
   - **Branched Workspace (Delegated):** If `use_branched_workspaces` is `true` and the harness supports it, spawn a subagent with `Workspace='branch'`. Dispatch ONE task per subagent — feed it only the task worksheet verbatim, the spec's relevant phase excerpt, applicable patterns/knowledge excerpts, and the canonical verification commands (never the whole spec tree). The subagent follows the worksheet exactly — no improvisation or scope changes; if the worksheet is insufficient it stops and reports the gap — plus the same rules as inline execution: TDD, notes in the task file, close with `state: closed` + commit SHA, immediate checklist reconciliation. Verify its evidence before dispatching the next task.
   - **Inline Execution:** Otherwise, proceed with inline execution in the current workspace:
     - Read the relevant spec, task notes, patterns, affected files, and validation commands.
     - Record investigation findings directly inside the task file's `## Notes & Discoveries` section.
     - Follow red-green-refactor: write the failing test, verify the failure, implement minimally, verify green, then refactor.
     - Commit targeted changes, retrieve the commit SHA, and close the task (set `state` to `closed` and write commit SHA to frontmatter).

## Guardrails

- Never flip checklist markers without the matching task-file `state:` change — and never leave them stale: reconcile the `spec.md` checklist immediately after EVERY task state change (claim, block, skip, close).
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
