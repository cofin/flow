---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying the declared verification strategy, recording task notes, committing, and updating task file state."
---

# Flow Execution

<!-- lifecycle-ownership: owner=flow-execution; operations=implement -->

## Trigger

Use for `implement` only, after a validated plan contains a ready worksheet.

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

1. Read `use_branched_workspaces` from `.agents/config.json` (default `false`).
2. Preflight one open task: closed dependencies, complete worksheet, live
   targets, declared strategy, matching plan identity, and fresh state revision.
3. Claim through `flow-reconciler`. For delegated branched work, dispatch one
   worksheet only; otherwise execute inline with the same contract.
4. Record discoveries, obtain the strategy's required initial evidence, make
   the minimum task-owned change, and keep focused evidence green while
   refactoring.
5. Run fresh verification, stage exact paths, create one local commit, and send
   commit-bound close evidence to `flow-reconciler`.
6. A worksheet mismatch permits read-only reproduction only; discover and
   block or release, then resume only after revised identity and fresh preflight.

## Guardrails

- Never edit task/spec state or checklist markers outside the state contract.
- Use red-green-refactor only for behavior/regression strategies; do not invent
  a RED result for static, documentation, characterization, or integration work.
- Preserve unrelated work and never push automatically. Never create or mutate Git tags.

## Output

Return initial and final evidence, changed/staged paths, local commit SHA,
discoveries, close result, and every verification limitation.

## Validation

Require the declared strategy's initial proof, focused and aggregate evidence,
acceptance-criteria checks, no foreign staged paths, and a fresh close result.

## Conditional References

- [Implement](../flow/references/implement.md) — load for preflight and mismatch routes.
- [Discipline](../flow/references/discipline.md) — load for the declared strategy.
- [State](../flow/references/state.md) — load before any state request.
- [Git Notes](../../docs/git-notes.md) — load only for optional post-close notes.

## Example

For one ready task, preflight, claim, collect required initial evidence,
implement minimally, verify, commit locally, and request close.
