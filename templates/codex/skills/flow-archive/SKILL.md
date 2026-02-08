---
name: flow-archive
---

# Flow Archive

Archive completed flow and elevate patterns to project level.

## Usage

`/flow:archive {flow_id}`

## Phase 1: Sync and Validate

### 1.1 Sync Beads State First

**CRITICAL:** Run `/flow:sync {flow_id}` FIRST to export current Beads state to spec.md before archiving.

This ensures spec.md reflects the final state from Beads (source of truth).

### 1.2 Validate Flow

Check Beads for completion status:

```bash
bd show {epic_id}
```

Or read `.agent/specs/{flow_id}/spec.md` Implementation Plan section to verify all tasks are `[x]` completed or `[-]` skipped.

If incomplete tasks exist, warn and confirm.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings
Parse `.agent/specs/{flow_id}/learnings.md`

### 2.2 Identify Patterns for Elevation
Present discovered patterns:
```
Patterns from {flow_id}:

1. [Code] Use Zod for form validation
2. [Gotcha] Must update barrel exports after adding files
3. [Testing] Mock external APIs in integration tests

Which patterns should be elevated to project-level? [all/select/none]
```

### 2.3 Merge to Project Patterns
Append selected patterns to `.agent/patterns.md`:
```markdown
## Code Conventions
- Use Zod for form validation (from: {flow_id})

## Gotchas
- Must update barrel exports after adding files (from: {flow_id})
```

## Phase 3: Close Beads Epic

```bash
bd close {epic_id} --reason "Flow archived"
bd compact  # Optional: compact Beads after archiving
```

## Phase 4: Move to Archive

1. Move directory:
   ```
   .agent/specs/{flow_id}/ → .agent/archive/{flow_id}/
   ```

2. Update `.agent/flows.md`:
   - Remove from Active section
   - Add to Archived section with completion date

## Phase 5: Create Archive Summary

Create `.agent/archive/{flow_id}/summary.md`:
```markdown
# Archive Summary: {flow_id}

**Completed:** {date}
**Duration:** {days} days
**Tasks:** {completed}/{total}
**Commits:** {count}

## Key Deliverables
- {deliverable 1}
- {deliverable 2}

## Patterns Elevated
- {pattern 1}
- {pattern 2}

## Final State
All tests passing, coverage at {X}%
```

## Final Output

```
Flow Archived: {flow_id}

Location: .agent/archive/{flow_id}/
Patterns Elevated: {count}
Epic Closed: {epic_id}
Beads Compacted: Yes/No

Project patterns updated. View with:
cat .agent/patterns.md
```
