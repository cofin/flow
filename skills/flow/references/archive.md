
# Flow Archive

Archive completed flow and elevate patterns to project level.

## Usage

`flow-archive {flow_id}`

## Phase 1: Validate

### 1.1 Validate Flow

Check Beads for completion status:

```bash
br show {epic_id}
```

Or read `.agents/specs/{flow_id}/spec.md` Implementation Plan section to verify all tasks are `[x]` completed or `[-]` skipped.

If incomplete tasks exist, warn and confirm.

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings

Parse `.agents/specs/{flow_id}/learnings.md`

### 2.2 Identify Patterns for Elevation

Present discovered patterns:

```text
Patterns from {flow_id}:

1. [Code] Use Zod for form validation
2. [Gotcha] Must update barrel exports after adding files
3. [Testing] Mock external APIs in integration tests

Which patterns should be elevated to project-level? [all/select/none]
```

### 2.3 Merge to Project Patterns

Append selected patterns to `.agents/patterns.md`:

```markdown
## Code Conventions
- Use Zod for form validation (from: {flow_id})

## Gotchas
- Must update barrel exports after adding files (from: {flow_id})
```

## Phase 3: Knowledge Synthesis

1. Create `.agents/knowledge/` if missing.
2. Read `learnings.md`, `spec.md` header, and `metadata.json` from the flow.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

## Phase 4: Close Beads Epic

```bash
br close {epic_id} --reason "Flow archived"
```

## Phase 5: Move to Archive

1. Move directory:

   ```text
   .agents/specs/{flow_id}/ -> .agents/archive/{flow_id}/
   ```

2. Update `.agents/flows.md`:
   - Remove from Active section
   - Add to Archived section with completion date

## Phase 6: Create Archive Summary

Create `.agents/archive/{flow_id}/summary.md`:

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

```text
Flow Archived: {flow_id}

Location: .agents/archive/{flow_id}/
Patterns Elevated: {count}
Epic Closed: {epic_id}

Project patterns updated. View with:
cat .agents/patterns.md
```
