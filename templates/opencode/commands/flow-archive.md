# Flow Archive

Archive completed flow and elevate patterns.

## Usage
`/flow:archive {flow_id}`

## Phase 1: Sync and Validate

### 1.1 Sync Beads State

**CRITICAL:** Run `/flow:sync {flow_id}` FIRST to export current Beads state to spec.md.

### 1.2 Validate Flow

Check Beads for completion:

```bash
bd show {epic_id}
```

Or verify all tasks completed in spec.md Implementation Plan section.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings
Parse `.agent/specs/{flow_id}/learnings.md`

### 2.2 Merge to Project Patterns
Append selected patterns to `.agent/patterns.md`

## Phase 3: Close Beads Epic

```bash
bd close {epic_id} --reason "Flow archived"
bd compact  # Optional: compact Beads after archive
```

## Phase 4: Move to Archive

Move `.agent/specs/{flow_id}/` → `.agent/archive/{flow_id}/`

Update `.agent/flows.md`

## Final Output

```
Flow Archived: {flow_id}

Location: .agent/archive/{flow_id}/
Patterns Elevated: {count}
```
