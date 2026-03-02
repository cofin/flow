---
description: Archive completed flows + elevate patterns
---

# Flow Archive

Archive completed flow and elevate patterns.

## Usage
`/flow:archive {flow_id}`

## Phase 1: Validate

### 1.1 Validate Flow

Check Beads for completion:

```bash
br show {epic_id}
```

Or verify all tasks completed in spec.md Implementation Plan section.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings
Parse `.agent/specs/{flow_id}/learnings.md`

### 2.2 Merge to Project Patterns
Append selected patterns to `.agent/patterns.md`

## Phase 3: Knowledge Extraction

1. Create `.agent/knowledge/` if missing.
2. Read `learnings.md`, `spec.md` header, and `metadata.json` from the flow.
3. Generate `.agent/knowledge/{flow_id}.md` with:
   - Flow ID, description, completion date, archive date
   - Topic tags (2-5 tags inferred from learnings content)
   - Which patterns were elevated to patterns.md
   - **Full verbatim content** from learnings.md
   - Key files mentioned in learnings
   - 2-3 sentence summary
4. Update `.agent/knowledge/index.md`:
   - Append row to Entries table: `| {flow_id} | {date} | {topics} | {summary} |`
   - Add entries under Topic Index headings (create headings if new)

## Phase 4: Close Beads Epic

```bash
br close {epic_id} --reason "Flow archived"
```

## Phase 5: Move to Archive

Move `.agent/specs/{flow_id}/` → `.agent/archive/{flow_id}/`

Update `.agent/flows.md`

## Final Output

```
Flow Archived: {flow_id}

Location: .agent/archive/{flow_id}/
Patterns Elevated: {count}
```
