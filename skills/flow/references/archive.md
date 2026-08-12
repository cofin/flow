
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
2. **Verify** flow is completed — read `.agents/bundles/specs/{flow_id}/spec.md` and ensure `status: completed`
3. If spec is not completed, warn and confirm.

### 1.2 Optional Code Review

For flows being archived without prior `flow-review`:

- Dispatch final code review subagent with full flow git range
- Log findings to `extracted_learnings.md` (will be archived with flow)
- Fix Critical issues before archiving

## Phase 2: Extract Learnings

### 2.1 Read Flow Learnings

Parse `.agents/bundles/specs/{flow_id}/extracted_learnings.md` (generated in next phase).

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

Append selected patterns to `.agents/bundles/knowledge/patterns/patterns.md`:

```markdown
## Code Conventions
- Use Zod for form validation (from: {flow_id})

## Gotchas
- Must update barrel exports after adding files (from: {flow_id})
```

## Phase 3: Knowledge Synthesis (The Synthesis Mandate)

You are responsible for the formal evolution of the project's knowledge base. It is NOT a manual copy-paste; it is a **Synthesis**.

1. **Consolidate**: Extract task discoveries directly:
   - Read all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` that have `status: closed` or `skipped`.
   - Read note lines starting with `- [` under `## Notes & Discoveries`.
   - Write these notes to `.agents/bundles/specs/{flow_id}/extracted_learnings.md` sorted by timestamp, annotated with their task ID.
2. **Identify**: Read `extracted_learnings.md` and `spec.md` from the flow. Identify which discoveries are one-off observations and which represent **Core Patterns** or **Architectural Shifts**.
3. **Synthesize**: Integrate these discoveries directly into cohesive, logically organized knowledge base chapters in `.agents/bundles/knowledge/` (e.g., `product/`, `workflow/`, `patterns/`, `code-styleguides/`).
4. **Update the State**: Revise these chapters to reflect the *current* authoritative state of the codebase.
5. **No History Logs**: Do NOT outline history or create per-flow logs in the knowledge base. The chapters must provide the high-definition implementation details needed for a new agent to become an instant expert on the current state.

## Phase 4: Delete Flow Spec Folder

1. **Delete spec bundle**: Run safe deletion directly:
   - Read all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` and ensure their status is `closed` or `skipped`. If any task is open or in progress, abort and warn the developer.
   - Delete all files inside `.agents/bundles/specs/{flow_id}/` (and its subdirectories) and remove the directory itself.

## Final Output

```text
Flow Archived: {flow_id}

Spec deleted from filesystem
Patterns Elevated: {count}

Project patterns updated. View with:
cat .agents/bundles/knowledge/patterns/patterns.md
```
