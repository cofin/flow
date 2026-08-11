---
description: Archive completed flows + elevate patterns
---

# Flow Archive

Archive completed flow and elevate patterns.

## Usage
`/flow-archive {flow_id}`

## Phase 1: Validate

### 1.1 Validate Flow

Verify all tasks completed in `.agents/bundles/specs/{flow_id}/spec.md` Implementation Plan section or by scanning task files under `tasks/*.md`.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings
Parse `.agents/bundles/specs/{flow_id}/learnings.md`

### 2.2 Merge to Project Patterns
Append selected patterns to `.agents/bundles/knowledge/patterns/patterns.md`

## Phase 3: Knowledge Synthesis

1. Create `.agents/bundles/knowledge/` if missing.
2. Read `.agents/bundles/specs/{flow_id}/learnings.md` and `.agents/bundles/specs/{flow_id}/spec.md`.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters under `.agents/bundles/knowledge/` (e.g., `product/`, `workflow/`, `patterns/`, `code-styleguides/`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

## Phase 4: Delete Flow Bundle

1. **Log Flow Completion:**
   Append metadata of the completed flow (ID, Title, completion timestamp) to `.agents/bundles/knowledge/log.md`.

2. **Delete Bundle Directory:**
   ```bash
   rm -rf .agents/bundles/specs/{flow_id}/
   ```

## Final Output

```
Flow Archived: {flow_id}

Spec deleted from filesystem
Patterns Elevated: {count}
Logged in .agents/bundles/knowledge/log.md
```
