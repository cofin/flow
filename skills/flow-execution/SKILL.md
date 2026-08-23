---
name: flow-execution
description: "Use when implementing Flow tasks from local task files under `.agents/bundles/specs/<flow_id>/tasks/`, claiming ready work, applying the declared verification strategy, recording task notes, committing, and updating task file state."
disable-model-invocation: true
---

# Flow Execution

<!-- lifecycle-ownership: owner=flow-execution; operations=implement -->

## Trigger

Use for `implement` only, after a validated plan contains ready task worksheets.

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

1. **Preflight**: Inspect `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md`, verify dependencies are `closed`, and set `state: in_progress`.
2. **Red-First Verification**: Run the declared test command and confirm it fails (red) on the missing behavior.
3. **Minimal Implementation**: Write minimal production code to pass the verification test (green, exit code 0).
4. **Quality Gates**: Run repository linters and typecheckers while tests remain green.
5. **Atomic Commit & Close**: Stage exact files, commit with signed Git commit, update task frontmatter (`state: closed`, `commit: <sha>`), and reconcile `spec.md` checklist via `/flow:sync`.

## Guardrails

- Execute exactly one task per subagent dispatch.
- Never mark a task `closed` without running the test command and observing exit code 0.
- Stage only task-owned files; never perform opportunistic unrelated edits.
- Work on the active branch. Never create or mutate Git tags.

## Output

Return the executed task ID, test command output, git commit SHA, and recorded discoveries.

## Validation

Confirm the test command produced exit code 0 and the commit SHA is recorded in task frontmatter.

## Example

For a task adding a route handler, write a failing endpoint test, implement the route to pass the test, commit locally, and close the task worksheet.
