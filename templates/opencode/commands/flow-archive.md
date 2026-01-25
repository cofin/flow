# Flow Archive

Archive completed track and elevate patterns.

## Usage
`/flow:archive {track_id}`

## Phase 1: Validate Track

Verify all tasks are `[x]` completed or `[-]` skipped.

## Phase 2: Extract Learnings

### 2.1 Read Track Learnings
Parse `.agent/specs/{track_id}/learnings.md`

### 2.2 Merge to Project Patterns
Append selected patterns to `.agent/patterns.md`

## Phase 3: Close Beads Epic

```bash
bd close {epic_id} --reason "Track archived"
```

## Phase 4: Move to Archive

Move `.agent/specs/{track_id}/` → `.agent/archive/{track_id}/`

Update `.agent/tracks.md`

## Final Output

```
Track Archived: {track_id}

Location: .agent/archive/{track_id}/
Patterns Elevated: {count}
```
