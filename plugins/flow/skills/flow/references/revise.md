# Flow Revise

Update a spec or task worksheet in-place when implementation reveals a mismatch, keeping the Markdown clean, current-state, and synchronized without accumulating historical transcripts.

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

- `spec.md`
- `tasks/*.md`
- `learnings.md`

Also load the blocking task's `discover` and `block` evidence, exact unblock condition, next planning action, current plan identity, and current spec state revision. Refuse an unclassified or incomplete mismatch report.

### Phase 2: Identify Revision Need & Check Scope Cap

Follow the **Critical Thinking Iron Law** to evaluate the implementation issue:

- **EVALUATE ACCURACY** — What exactly is failing? Read the code/logs.
- **EVALUATE COMPLETENESS** — What was missing or inaccurate in the worksheet?
- **EVALUATE REASONING QUALITY** — Why did the original step or target fail?
- **INVESTIGATE** — Confirm root cause before proposing revision.

**Scope-Growth Escape Hatch (New Spec vs. Revise):**

- If resolving the issue requires adding a new subsystem, expanding the flow beyond `8–10` tasks, or entering a third revision cycle for the same flow, **do NOT keep bloating the current spec**.
- Instead, ask the user whether to descope/close the current spec around its completed deliverables and **create a new follow-up spec** (`/flow:plan <new_flow_id>`) for the expanded scope.

Classify the handoff using the execution contract:

| Mismatch | Required planning route |
| --- | --- |
| Missing decision or incomplete executable detail | `refine`, then include the approved worksheet change in `revise` |
| Code drift, invalid file/symbol/test target, acceptance contradiction, scope expansion, or invalid verification command | `revise`; use `refine` to make the replacement worksheet pass the Stateless Executor Test |

Do not authorize the executor to patch around a mismatch. Until a new plan is validated, only planning Markdown may change.

### Phase 3: Rewrite In-Place (Zero Transcript Bloat)

**IRON LAW: WORKSHEETS ARE PRESENT-TENSE INSTRUCTIONS, NOT HISTORICAL TRANSCRIPTS.**

When revising `spec.md` and `tasks/*.md`:

1. **Replace obsolete content in-place**: Overwrite stale file paths, line numbers, code snippets, steps, and acceptance criteria directly inside `## Objective`, `## Context`, `## Steps`, `## Verification`, and `## Acceptance Criteria`. Never keep struck-through old plans, "Revision 1 vs Revision 2" comparison blocks, or multi-paragraph post-mortems inside the spec or task body.
2. **One-line rationale only**: Record at most **one single-line bullet** (`- <timestamp> [<operation_id>] revise: <concise root cause & change>`) in `## Notes & Discoveries`. Keep `## Continuity Snapshot` in `spec.md` capped at the 5 newest discoveries, pruning superseded notes.
3. **Prune stale transaction transcripts**: Once the revision transaction commits and live Markdown is verified, prune superseded or obsolete prior terminal journals (`committed`, `rolled_back`, `superseded`) under `<configured-root>/transactions/` so hundreds of old transaction folders never accumulate or confuse future sessions.

### Phase 4: Refine, Validate, and Apply One Revision Transaction

Produce exact task/spec diffs that pass Objective, Context, Steps, Verification, Acceptance Criteria, target, dependency, strategy, and contradiction checks.

Apply a journaled `revise` through `flow-state` with exact plan diffs, concise rationale, reviewer findings, `new_plan_revision = expected_plan_revision + 1`, every affected task target sorted, and explicit legal state adjustments (`unblock`, `reopen`, `skip`, or `create`). In the **same transaction**, ensure Markdown status is 100% synchronized:

- Update every task's `plan_revision`, `plan_commit: null`, `state`, `state_revision`, `blocked_reason`, `unblock_condition`, and `next_step` before writing `spec.md`.
- Update `spec.md` frontmatter (`plan_revision`, `plan_commit: null`, `state_revision`, `current_task`, `updated_at`), reconcile all `## Implementation Plan` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`) to match task file `state`, and update `## Continuity Snapshot` with the next exact actionable step.
- Never maintain `revisions.md` as a second authority or leave checklist markers out of sync with task frontmatter.

### Phase 5: Resume Handoff

Return the new plan identity, synchronized status summary, and validation evidence. The executor reloads the clean, present-tense `spec.md` and `tasks/*.md` and repeats its five-check preflight.

## Critical Rules

1. **FAIL CLOSED** — No executor production mutation while a mismatch is unresolved.
2. **IN-PLACE PRESENT-TENSE REWRITE** — Overwrite superseded steps in-place; never hoard historical transcripts or old failed plans in `spec.md` or `tasks/*.md`.
3. **SYNCHRONIZE MARKDOWN STATUS** — Every `revise` must leave task frontmatter `state`, `spec.md` checklist markers, and `Continuity Snapshot` 100% aligned.
4. **SPLIT WHEN GROWING TOO LARGE** — Spawn a new spec instead of expanding a spec past its cohesive scope.
5. **ONE PLAN IDENTITY & FRESH RESUME** — Apply approved edits through one `revise` transaction, reload Markdown, and repeat preflight.
6. **NO RUNTIME EVALUATOR** — Interpret the Markdown contracts directly; installed workflows never call Python or another evaluator.
