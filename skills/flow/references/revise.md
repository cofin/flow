# Flow Revise (`/flow:revise`, alias `/flow:refine`)

Update or deepen a specification (`spec.md`) and its task worksheets (`tasks/<id>-<slug>.md`) in place in present tense—either before execution to satisfy the **Zero-Decision Implementation Readiness Standard** (`/flow:refine` alias) or mid-execution when a task encounters code drift, a missing decision, or a changed requirement (`/flow:revise`).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - zero-decision-implementation-readiness
  - present-tense-in-place-rewrite
  - fail-closed-no-production-mutation
  - fresh-validated-plan-resume
authority: skills/flow/references/revise.md
```
<!-- flow-execution-policy: end -->

## Usage

```text
/flow:revise <flow_id> [changes]
/flow:refine <flow_id> [task_id]
```

## Workflow

### Phase 1: Load Current State, Gap Scan, & Evaluate Scope Cap

1. Read `.agents/bundles/specs/<flow_id>/spec.md`, `tasks/*.md`, `learnings.md`, and relevant `.agents/bundles/knowledge/**` chapters.
2. If triggered by a blocked task (`state: blocked`), inspect its `blocked_reason`, `unblock_condition`, and `## Notes & Discoveries`, and read the actual repository source files (`path/to/file::Symbol`) to verify the root cause.
3. **Run the Zero-Decision Stateless Executor Test**:
   - For every task worksheet, ask: *"If I handed this worksheet to a fresh Goldfish executor with zero chat history, could it implement and verify the change 100% correctly on the first attempt without making any independent design choice?"*
   - Reject and refine any worksheet that has:
     - Deferred research or unverified external API behavior
     - Unresolved architectural or edge-case decisions
     - Vague prose (`"wire up"`, `"finish integration"`, `"handle edge cases"`) instead of concrete `path/to/file::Symbol` targets and code/signature sketches
     - Missing `verification_strategy` or missing public-seam test cases
     - Overlapping file ownership across ready tasks or tasks too large for one subagent turn and one commit (`~400` lines max including tests)
4. **Scope-Growth Escape Hatch**:
   - If resolving the change requires adding a new subsystem, expanding the flow beyond `8–10` tasks, or entering a third revision cycle, do **not** bloat the current spec.
   - Ask the user via `structured-choice-v1` ([`interaction.md`](interaction.md)) whether to close the current spec around its completed tasks and spawn a follow-up spec (`/flow:plan <new_flow_id>`).

### Phase 2: Rewrite In Place in Present Tense (Zero Historical Sediment)

Worksheets and specifications are present-tense executable instructions, never historical revision transcripts:

1. **Overwrite Superseded Content In Place**: Update `## 1. Specification & Context`, `## 2. Requirements & Architecture`, `## 3. Requirement-to-Task Traceability Matrix`, `## 4. Implementation Plan`, and the affected `tasks/<id>-<slug>.md` sections (`## Objective`, `## Context`, `## Steps`, `## Verification`, `## Acceptance Criteria`) directly in present tense.
2. **Eliminate Revision Sediment**: Never leave struck-through old steps, `"Revision 1 vs. Revision 2"` comparison blocks, or multi-paragraph post-mortems in `spec.md` or `tasks/*.md`.
3. **Single-Line Discovery Note**: Record at most one concise bullet (`- [YYYY-MM-DD HH:MM] revise: <root cause & updated target>`) under `## Notes & Discoveries` in the affected task worksheet, and keep `## 5. Continuity Snapshot` in `spec.md` capped at the 5 newest discoveries.

### Phase 3: Increment `plan_revision`, Re-Run Goldfish Review & Re-Anchor `plan_commit`

1. **Synchronize Revision & State**:
   - Increment `plan_revision` by `1` once for the revision pass and copy the new `plan_revision` to `spec.md` and every `tasks/<id>-<slug>.md`.
   - For any unblocked task, set `state: pending` (or `open`), clear `blocked_reason: null` and `unblock_condition: null`, and synchronize `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
2. **Stateless Goldfish Review on Changed Surface**:
   - Dispatch `@code-reviewer` (or `run_workflow` `parallel()` with `schema=SPEC_REVIEW_SCHEMA` when available on Google Antigravity) with **only disk paths** for the revised `spec.md` and modified `tasks/<id>-<slug>.md` files, and adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`).
3. **Re-Anchor `plan_commit` & Resume**:
   - Present the `Approve | Revise | Refine` gate ([`interaction.md`](interaction.md)). Once approved, stamp `plan_commit: <HEAD_SHA>` across `spec.md` and all `tasks/*.md`, log the revision in `.agents/bundles/log.md`, and hand off to `/flow:implement <flow_id>`.
