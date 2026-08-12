---
description: Archive completed flows + elevate patterns
---

# Flow Archive

Archive completed flow and elevate patterns.

## Usage
`/flow-archive {flow_id}`

## Phase 1: Validation

### 1.1 Resolve Flow ID

If not provided, dynamically scan the `.agents/bundles/specs/` directory to discover active/completed flows and ask the user to select.

### 1.2 Verify Completion

Read the `.agents/bundles/specs/{flow_id}/spec.md` frontmatter `state`.

- If `state` is not `completed` (e.g. `active`, `planned`), warn: "Warning: Flow is not marked as completed. Continue? (y/n)" → Halt if 'n'.

## Phase 2: Pattern Elevation

1. Read `.agents/bundles/specs/{flow_id}/extracted_learnings.md` (generate first in Phase 3 step 1 if missing).
2. Read `.agents/bundles/knowledge/patterns/patterns.md`.
3. Identify new patterns not present in global patterns.
4. **Interactive Selection:**
   - "Found these potential patterns:"
   - [ ] Pattern 1
   - [ ] Pattern 2
   - "Select patterns to elevate (or 'all'/'none'):"
5. **Merge:** Append selected patterns to `.agents/bundles/knowledge/patterns/patterns.md`.
   - Format: `- {new pattern} (from: {flow_id})`

## Phase 3: Knowledge Synthesis

1. **Consolidate Learnings**: Read all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` that have `state: closed` or `skipped`, extract notes from the `## Notes & Discoveries` heading, and write them sorted by timestamp into `.agents/bundles/specs/{flow_id}/extracted_learnings.md`.
2. Read the consolidated learnings at `.agents/bundles/specs/{flow_id}/extracted_learnings.md` and the specification `.agents/bundles/specs/{flow_id}/spec.md`.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters under `.agents/bundles/knowledge/` (e.g., `product/`, `workflow/`, `patterns/`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

## Phase 4: Delete Flow Bundle

1. **Safe Deletion**: Verify that all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` have `state: closed` or `skipped`. If any task is open or in progress, abort and warn. Otherwise, delete the folder `.agents/bundles/specs/{flow_id}/` from the filesystem.

## Phase 5: Git Commit

1. **Commit Changes:**

   ```bash
   git add .agents/bundles/knowledge/patterns/patterns.md .agents/bundles/knowledge/
   git rm -r .agents/bundles/specs/{flow_id}/
   git commit -m "chore(archive): synthesize learnings from {flow_id} and archive spec"
   ```

## Phase 6: Completion

> "Flow '{flow_id}' archived successfully.
>
> **Summary:**
>
> - ID: {flow_id}
> - Spec deleted from filesystem
> - Patterns Elevated: {count}
>
> Ready for next flow: `/flow-prd`"
