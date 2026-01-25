# Flow Archive

Archive completed track and elevate patterns to project level.

## Usage
`/flow:archive {track_id}`

## Phase 1: Validate Track

1. Read `.agent/specs/{track_id}/plan.md`
2. Verify all tasks are `[x]` completed or `[-]` skipped
3. If incomplete tasks exist, warn and confirm

## Phase 2: Extract Learnings

### 2.1 Read Track Learnings
Parse `.agent/specs/{track_id}/learnings.md`

### 2.2 Identify Patterns for Elevation
Present discovered patterns:
```
Patterns from {track_id}:

1. [Code] Use Zod for form validation
2. [Gotcha] Must update barrel exports after adding files
3. [Testing] Mock external APIs in integration tests

Which patterns should be elevated to project-level? [all/select/none]
```

### 2.3 Merge to Project Patterns
Append selected patterns to `.agent/patterns.md`:
```markdown
## Code Conventions
- Use Zod for form validation (from: {track_id})

## Gotchas
- Must update barrel exports after adding files (from: {track_id})
```

## Phase 3: Close Beads Epic

```bash
bd close {epic_id} --reason "Track archived"
```

## Phase 4: Move to Archive

1. Move directory:
   ```
   .agent/specs/{track_id}/ → .agent/archive/{track_id}/
   ```

2. Update `.agent/tracks.md`:
   - Remove from Active section
   - Add to Archived section with completion date

## Phase 5: Create Archive Summary

Create `.agent/archive/{track_id}/summary.md`:
```markdown
# Archive Summary: {track_id}

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
Track Archived: {track_id}

Location: .agent/archive/{track_id}/
Patterns Elevated: {count}
Epic Closed: {epic_id}

Project patterns updated. View with:
cat .agent/patterns.md
```
