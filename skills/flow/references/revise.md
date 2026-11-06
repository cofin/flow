# Flow Revise (`/flow:revise`, alias `/flow:refine`)

Update, split, or deepen a root specification (`specs/<flow_id>/spec.md`), nested chapter specification (`specs/<flow_id>/chapters/<ch_id>/spec.md`), and 8-section task blueprints (`tasks/<id>-<slug>.md`) **in place in present tense**—either before execution (`/flow:refine`), when promoting an `empirical_dependent` chapter after upstream runtime evidence lands, or mid-execution when a chapter/task encounters code drift, an unstated edge case, or changed requirements (`/flow:revise`).

<!-- flow-execution-policy: start -->
```yaml
contract: worksheet-execution-v1
invariants:
  - worksheet-first
  - zero-decision-implementation-readiness
  - anti-truncation-chapter-expansion
  - present-tense-full-plan-sync
  - fail-closed-no-production-mutation
  - fresh-validated-plan-resume
authority: skills/flow/references/revise.md
```
<!-- flow-execution-policy: end -->

## Usage

```text
/flow:revise <flow_id> [chapter_id] [changes]
/flow:refine <flow_id> [chapter_id | task_id]
```

## Workflow

### Phase 1: Scoped Inspection, Gap Scan, & Chapter Expansion Check

1. Read root `.agents/bundles/specs/<flow_id>/spec.md`, `chapters/index.md` (when `has_chapters: true`), the target `chapters/<ch_id>/spec.md` and `tasks/*.md` (never loading unrelated completed chapters into the coordinator), and relevant `.agents/bundles/knowledge/**` chapters.
2. If triggered by:
   - **A `blocked` task (`state: blocked`)**: Inspect `blocked_reason`, `unblock_condition`, and `## Notes & Discoveries`, and verify the exact repository symbols (`path/to/file::Symbol`) on disk.
   - **An `empirical_dependent` chapter (`planning_status: empirical_dependent`)**: Verify the upstream chapters in `depends_on_chapters` are `completed` with valid `last_reviewed_commit`, gather the empirical evidence specified in `replan_trigger`, finalize concrete signatures/thresholds/test literals, set `planning_status: complete`, and clear `replan_trigger: null`.
3. **Run the Zero-Decision & Anti-Truncation Check**:
   - Reject and deepen any chapter or worksheet with deferred research, unresolved edge-case decisions, missing concrete type/signature contracts, missing `Caller -> Seam -> Collaborator` wiring, missing Worked Test Matrix literals, missing `Documentation & OKF Knowledge Plan` items, or `read_set > 6` / `estimated_loc > 250`.
   - **Never Truncate to Fit `4` Tasks**: If a single-chapter flow grows past `4` tasks, convert it to `chapters/index.md` + `chapters/ch01-<slug>/..chNN-<slug>/`. If an existing chapter requires `> 4` tasks, **split it into additional `chNN-<slug>` chapters** (updating `depends_on_chapters` on downstream chapters as needed) rather than compressing tasks or dropping documentation/edge cases.

### Phase 2: Delegated Present-Tense Rewrite & Full-Plan Synchronization (Zero History)

Delegate multi-file blueprint edits to an isolated `@plan-generator` subagent (`type_name="self"` on Google Antigravity). Specifications, chapter catalogs, and worksheets are **present-tense blueprints of current verified state and remaining work—never revision logs**:

1. **Overwrite Target Chapter & Worksheets In Place**:
   - Update all 6 sections of `chapters/<ch_id>/spec.md` (or single-chapter `spec.md`) and all 8 blueprint sections of affected `tasks/<id>-<slug>.md` directly in present tense with OKF v0.2 `sources:` + `[^id]:` citations and zero standalone `---` body rules.
   - If a previously `completed` chapter is reopened or has new/pending tasks added, set its `state` back to `planned` or `active` and **clear `last_reviewed_commit: null`** so the `Stop` hook and `/flow:implement` require a fresh chapter code/doc review before re-closing it.
2. **Mandatory Root Roadmap & `chapters/index.md` Synchronization**:
   - Whenever any chapter is revised, split into new `chNN-<slug>` chapters, promoted from `empirical_dependent` to `complete`, or changes a shared cross-chapter contract or doc target, **simultaneously rewrite root `specs/<flow_id>/spec.md` and `specs/<flow_id>/chapters/index.md` in place in present tense**:
     - Update `chapters: [...]`, `current_chapter`, shared public type/signature contracts in `## 2`, `[k/N files documented]` in `## 3`, traceability rows in `## 4`, the full chapter checklist in `## 5`, and `## 6. Current State & Remaining Plan Snapshot` (stating verified baseline at `HEAD`, active chapter, and full remaining chapter list).
     - Inspect remaining downstream chapters (`chK..chNN`): if a shared contract changed, either update those downstream chapter blueprints in parallel subagents now or mark them `planning_status: empirical_dependent` with an explicit `replan_trigger` so stale signatures never survive on disk.
3. **Zero Historical Sediment**:
   - Never leave `Revision History` / `Changelog` headings, `"previously we planned..."` or `"revised from..."` commentary, or struck-through checklist items (`- [ ] ~~...~~`) in `spec.md`, `chapters/index.md`, or `tasks/*.md`.
   - Record chronological revision events exclusively by prepending an entry to `.agents/bundles/log.md` (plus at most one concise implementation-relevant bullet under `## Notes & Discoveries` in an affected task worksheet).

### Phase 3: Increment `plan_revision`, Zero-Context Review, & Re-Anchor `plan_commit`

1. **Synchronize Revision & Checklist State**:
   - Increment `plan_revision` by `1` once for the revision pass and synchronize `plan_revision` across root `spec.md`, revised `chapters/<ch_id>/spec.md`, and their `tasks/*.md` files.
   - Reset unblocked tasks to `state: pending` (`blocked_reason: null`, `unblock_condition: null`) and ensure every task `state` matches its owning `spec.md` checklist marker (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
2. **Zero-Context Review on Changed Surface**:
   - Dispatch isolated Zero-Context Reviewer subagent(s) (`@code-reviewer`; `type_name="self"` on Google Antigravity) with **only disk paths** for root `specs/<flow_id>/spec.md`, `chapters/index.md`, and the revised chapter/task files, verifying blueprint completeness, anti-truncation, OKF v0.2 conformance, and full-plan present-tense consistency. Adjudicate findings (`ADOPT` / `CONTEST` / `ESCALATE`).
3. **Re-Anchor `plan_commit` & Resume**:
   - Present the `Approve | Revise | Refine` gate ([`interaction.md`](interaction.md)). Once approved, stamp `status: stable` and `plan_commit: <HEAD_SHA>` across revised specs and tasks, prepend a `revise` entry to `.agents/bundles/log.md`, and hand off to `/flow:implement <flow_id>`.
