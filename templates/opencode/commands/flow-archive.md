---
description: Archive completed flows + elevate patterns
---

# Flow Archive

Archive completed flow and elevate patterns.

## Usage
`/flow-archive {flow_id}`

## Phase 1: Validate

### 1.1 Validate Flow

Check Beads for completion:

```bash
bd show {epic_id}
```

Or verify all tasks completed in spec.md Implementation Plan section.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings
Parse `.agents/specs/{flow_id}/learnings.md`

### 2.2 Merge to Project Patterns
Append selected patterns to `.agents/patterns.md`

## Phase 3: Knowledge Synthesis

1. Create `.agents/knowledge/` if missing.
2. Read `learnings.md`, `spec.md` header, and `metadata.json` from the flow.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

## Phase 4: Close Beads Epic

```bash
bd close {epic_id} --reason "Flow archived"
```

## Phase 5: Move to Archive

Move `.agents/specs/{flow_id}/` → `.agents/archive/{flow_id}/`

Update `.agents/flows.md`

## Final Output

```
Flow Archived: {flow_id}

Location: .agents/archive/{flow_id}/
Patterns Elevated: {count}
```
