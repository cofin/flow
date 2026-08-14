---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying TDD, recording task notes, committing, and updating task file state."
---

# Flow Execution

Use this lifecycle skill when implementation starts after a Flow plan or ready task file exists.

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - fail-closed-no-production-mutation
  - fresh-validated-plan-resume
transitions:
  - preflight-claim
  - mismatch-discover-block
  - nonblocking-discover-release
  - revised-plan-resume
authority: skills/flow/references/implement.md
```
<!-- flow-execution-policy: end -->

## Workflow

1. **Read Configuration:** Check `use_branched_workspaces` in `.agents/config.json` (default to `false` if missing).
2. **Select and Preflight Ready Work:** Select ready work from `.agents/bundles/specs/<flow_id>/tasks/*.md` (YAML frontmatter `state: open` and dependencies resolved). Before requesting `claim`, verify closed dependencies, worksheet completeness and live targets, the declared verification strategy, matching task/spec plan identity, and the freshly read spec state revision. A stub or stale target fails closed.
3. **Determine Execution Strategy:**
   - **Branched Workspace (Delegated):** If `use_branched_workspaces` is `true` and the harness supports it, spawn a subagent with `Workspace='branch'`. Dispatch ONE task per subagent — feed it only the task worksheet verbatim, the spec's relevant phase excerpt, applicable patterns/knowledge excerpts, and the canonical verification commands (never the whole spec tree). The subagent follows the worksheet exactly — no improvisation or scope changes; if the worksheet is insufficient it stops and reports the gap — plus the same rules as inline execution: TDD, exact sidecar requests for notes/state, and fresh close evidence. Verify its evidence before dispatching the next task.
   - **Inline Execution:** Otherwise, proceed with inline execution in the current workspace:
     - Read the relevant spec, task notes, patterns, affected files, and validation commands.
     - Record investigation findings with the `flow-reconciler` `note` or `discover` operation.
     - Follow red-green-refactor: write the failing test, verify the failure, implement minimally, verify green, then refactor.
     - Commit targeted changes, retrieve the commit SHA, and request `close` with fresh evidence through `flow-reconciler`.

## Mismatch decision table

The exact mismatch classes, reports, transitions, and resume guards are defined
in [Implement](../flow/references/implement.md). Code drift, a missing decision,
an invalid file/symbol/test target, an acceptance contradiction, scope
expansion, or an invalid verification command permits read-only reproduction
only. Make no production edit. Request `discover`, then `block` with evidence,
impact, an exact unblock condition, and the next `revise` or `refine` action. A
nonblocking discovery may instead be followed by `release` when the current
claimant stops.

Resume only after plan identity changes, validation passes, tracked Markdown is
reloaded, and the complete preflight passes again. There is no
`implement_state.json`, hidden state copy, or installed evaluator; all state
transitions use the Markdown sidecar protocol.

## Guardrails

- Never edit task/spec state or checklist markers directly; request every transition from `flow-reconciler` under the canonical state contract.
- Do not skip failing-test evidence for behavior changes.
- Do not silently descope messy tasks; refine or ask how to prioritize.
- Preserve unrelated user changes and keep edits scoped to the claimed task.

## Validation

- Verify the new test failed for the intended reason before implementation.
- Run focused tests after each task and the repo’s aggregate verification before phase completion.
- Record commit reference and discoveries through exact sidecar requests.

## References Index

- [Implement](../flow/references/implement.md)
- [Discipline](../flow/references/discipline.md)

## Example

User: "Implement auth flow."

Action: preflight the next ready worksheet, request its claim, write a failing auth test, implement minimally, verify, commit, and request close with the commit SHA and fresh evidence.
