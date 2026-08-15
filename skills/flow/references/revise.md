
# Flow Revise

Update spec or plan when implementation reveals issues.

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

## Usage

```text
flow-revise <flow_id>
```

## Workflow

### Phase 1: Load Current State

Read `.agents/bundles/specs/{flow_id}/`:

- spec.md
- tasks/*.md
- learnings.md

Also load the blocking task's `discover` and `block` evidence, exact unblock
condition, next planning action, current plan identity, and current spec state
revision. Refuse an unclassified or incomplete mismatch report.

### Phase 2: Identify Revision Need (Critical Thinking)

Follow the **Critical Thinking Iron Law** to evaluate the implementation issue:

- **EVALUATE ACCURACY** — What exactly is failing? Read the code/logs.
- **EVALUATE COMPLETENESS** — What was missing in the original spec?
- **EVALUATE REASONING QUALITY** — Why did the original plan fail?
- **INVESTIGATE** — Confirm root cause before proposing revision.

Ask user for guidance on the proposed revision.

Classify the handoff using the execution contract:

| Mismatch | Required planning route |
| --- | --- |
| Missing decision or incomplete executable detail | `refine`, then include the approved worksheet change in `revise` |
| Code drift, invalid file/symbol/test target, acceptance contradiction, scope expansion, or invalid verification command | `revise`; use `refine` to make the replacement worksheet pass the Stateless Executor Test |

Do not authorize the executor to patch around a mismatch. Until a new plan is
validated, only planning Markdown may change.

### Phase 3: Document Reason

Log why revision is needed based on your investigation. **Deliver honest assessment** of the original spec's flaws.

### Phase 4: Refine and Validate the Replacement

Produce exact task/spec diffs that correct the reported mismatch. The affected
worksheet must again pass Objective, Context, Steps, Verification, Acceptance
Criteria, target, dependency, strategy, and contradiction checks. Validate the
complete plan before requesting a mutation.

### Phase 5: Apply One Revision Transaction

Request `revise` from `flow-reconciler` with exact plan diffs, rationale,
reviewer findings, `new_plan_revision = expected_plan_revision + 1`, every
affected task target sorted, and any explicit legal state adjustments. The
sidecar updates every task's copied plan identity before the spec, clears the
shared `plan_commit`, reconciles derived content, and records the decision note.
Never write plan/state fields or maintain `revisions.md` as a second authority.

### Phase 6: Resume Handoff

Return the new plan identity and validation evidence. The executor must reload
the tracked spec/task Markdown and repeat its complete preflight. A released or
blocked task is not resumable merely because prose changed: the plan identity
must differ from the stopped execution and validation must pass.

## Critical Rules

1. **FAIL CLOSED** - No executor production mutation while a mismatch is unresolved
2. **ONE PLAN IDENTITY** - Apply approved plan-bearing edits through one `revise` transaction
3. **FRESH RESUME** - Require changed identity, passed validation, Markdown reload, and repeated preflight
4. **NO RUNTIME EVALUATOR** - Interpret the Markdown contracts directly; installed workflows never call Python or another evaluator
