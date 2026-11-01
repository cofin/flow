# Flow Revise (`/flow:revise`, alias `/flow:refine`)

Update a specification (`spec.md`) and its task worksheets (`tasks/<id>-<slug>.md`) in place in present tense—either before execution to deepen worksheet detail (`/flow:refine` alias) or mid-execution when a task encounters code drift, a missing decision, or a changed requirement (`/flow:revise`).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
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

### Phase 1: Load Current State & Evaluate Scope Cap

1. Read `.agents/bundles/specs/<flow_id>/spec.md`, `tasks/*.md`, and `learnings.md`.
2. If triggered by a blocked task (`state: blocked`), inspect its `blocked_reason`, `unblock_condition`, and `## Notes & Discoveries`, and read the actual repository source files (`path/to/file::Symbol`) to verify the root cause.
3. **Scope-Growth Escape Hatch**:
   - If resolving the change requires adding a new subsystem, expanding the flow beyond `8–10` tasks, or entering a third revision cycle, do **not** bloat the current spec.
   - Ask the user via `structured-choice-v1` ([`interaction.md`](interaction.md)) whether to close the current spec around its completed tasks and spawn a follow-up spec (`/flow:plan <new_flow_id>`).

### Phase 2: Rewrite In Place in Present Tense (Zero Historical Transcript Bloat)

Worksheets and specifications are present-tense executable instructions, never historical revision logs:

1. **Overwrite Superseded Content In Place**: Update `## 1. Specification & Context`, `## 2. Requirements`, `## 3. Requirement-to-Task Traceability Matrix`, `## 4. Implementation Plan`, and the affected `tasks/<id>-<slug>.md` sections (`## Objective`, `## Context`, `## Steps`, `## Verification`, `## Acceptance Criteria`) directly in present tense.
2. **Never Accumulate Revision Sediment**: Never leave struck-through old steps, "Revision 1 vs. Revision 2" comparison blocks, or multi-paragraph post-mortems in `spec.md` or `tasks/*.md`.
3. **Single-Line Discovery Note**: Record at most one concise bullet (`- [YYYY-MM-DD HH:MM] revise: <root cause & updated target>`) under `## Notes & Discoveries` in the affected task worksheet, and keep `## 5. Continuity Snapshot` in `spec.md` capped at the 5 newest discoveries.

### Phase 3: Increment `plan_revision`, Re-Run Zero-Context Review & Synchronize State

1. **Synchronize Revision & State**:
   - Increment `plan_revision` by `1` once for the revision pass and copy the new `plan_revision` to `spec.md` and every `tasks/<id>-<slug>.md`.
   - For any unblocked task, set `state: pending` (or `open`), clear `blocked_reason: null` and `unblock_condition: null`, and synchronize `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
2. **Zero-Context Focused Review on Changed Surface**:
   - Dispatch `@code-reviewer` (or `run_workflow` `parallel()` with `schema=` when available on Google Antigravity) on the revised `spec.md` and modified `tasks/<id>-<slug>.md` files, and adjudicate findings (`ADOPT` vs. `CONTEST` with evidence).
3. **Re-Anchor `plan_commit` & Resume**:
   - Stamp `plan_commit: <HEAD_SHA>` across `spec.md` and all `tasks/*.md`, log the revision in `.agents/bundles/log.md`, and hand off to `/flow:implement <flow_id>`.
