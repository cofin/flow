
# Flow Archive

Archive completed flow and elevate patterns to project level.

## Usage

`flow-archive {flow_id}`

## Phase 1: Validate

### 1.1 Verification Gate

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

1. **Run full test suite** — read output, confirm 0 failures
2. **Check Beads** for completion status:

   ```bash
   br show {epic_id}
   ```

3. **Verify** all tasks are completed or explicitly skipped — read `spec.md` Implementation Plan section
4. If incomplete tasks or failing tests exist, warn and confirm.

### 1.2 Optional Code Review

For flows being archived without prior `flow-review`:

- Dispatch final code review subagent with full flow git range
- Log findings to `learnings.md` (will be archived with flow)
- Fix Critical issues before archiving

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

## Phase 3: Knowledge Synthesis (The Synthesis Mandate)

You are responsible for the formal evolution of the project's knowledge base. It is NOT a manual copy-paste; it is a **Synthesis**.

1. **Identify**: Read `learnings.md`, `spec.md`, and `metadata.json` from the flow. Identify which discoveries are one-off observations and which represent **Core Patterns** or **Architectural Shifts**.
2. **Synthesize**: Integrate these discoveries directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`).
3. **Update the State**: Revise these chapters to reflect the *current* authoritative state of the codebase.
4. **No History Logs**: Do NOT outline history or create per-flow logs in the knowledge base. The chapters must provide the high-definition implementation details needed for a new agent to become an instant expert on the current state.

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
