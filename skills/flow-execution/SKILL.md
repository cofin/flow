---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying the declared verification strategy, recording task notes, committing, and updating task file state."
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
   - **Branched Workspace (Delegated):** If `use_branched_workspaces` is `true` and the harness supports it, spawn a subagent with `Workspace='branch'`. Dispatch ONE task per subagent — feed it only the task worksheet verbatim, the spec's relevant phase excerpt, applicable patterns/knowledge excerpts, and the canonical verification commands (never the whole spec tree). The subagent follows the worksheet exactly — no improvisation or scope changes; if the worksheet is insufficient it stops and reports the gap — plus the same rules as inline execution: the declared verification strategy, exact sidecar requests for notes/state, and fresh close evidence. Verify its evidence before dispatching the next task.
   - **Inline Execution:** Otherwise, proceed with inline execution in the current workspace:
     - Read the relevant spec, task notes, patterns, affected files, and validation commands.
     - Record investigation findings with the `flow-reconciler` `note` or `discover` operation.
     - Follow the declared verification strategy in [Discipline](../flow/references/discipline.md). Use red-green-refactor only for `behavior_tdd` or `regression_tdd`; use the required green baseline, native gate, docs validation, or composed acceptance evidence for the other strategies.
     - Commit targeted changes, retrieve the functional commit SHA, and put compact fresh verification evidence in the `close` request to `flow-reconciler`.
     - Only after close succeeds, optionally append the detailed `flow-git-note-v1` record to that functional commit, then report attachment success or failure with an idempotent `note(category=git_note_attachment)` request. Git notes are supplementary and are never pushed automatically.

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
- Do not skip failing-test evidence for behavior/regression strategies, and do not invent it for other strategies.
- Do not silently descope messy tasks; refine or ask how to prioritize.
- Preserve unrelated user changes and keep edits scoped to the claimed task.

## Validation

- Verify the strategy's required initial evidence before implementation.
- Run focused tests after each task and the repo’s aggregate verification before phase completion.
- Record commit reference and discoveries through exact sidecar requests.
- Put compact evidence inside `close`/phase `checkpoint` requests. Optional detailed notes follow a successful state transaction, target an existing functional commit, and use the protocol in [Git Notes](../../docs/git-notes.md).
- Never create or mutate Git tags, including as a fallback when notes are unavailable.

## References Index

- [Implement](../flow/references/implement.md)
- [Discipline](../flow/references/discipline.md)
- [Git Notes](../../docs/git-notes.md)

## Example

User: "Implement auth flow."

Action: preflight the next ready worksheet, request its claim, collect the declared strategy's initial evidence, implement minimally, verify, commit, and request close with the commit SHA and fresh evidence.
