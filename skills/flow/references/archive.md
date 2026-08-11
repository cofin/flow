
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

Append selected patterns to `.agents/patterns.md`:

```markdown
## Code Conventions
- Use Zod for form validation (from: {flow_id})

## Gotchas
- Must update barrel exports after adding files (from: {flow_id})
```

## Phase 3: Knowledge Synthesis (The Synthesis Mandate)

You are responsible for the formal evolution of the project's knowledge base. It is NOT a manual copy-paste; it is a **Synthesis**.

1. **Consolidate**: Extract task discoveries using the completion utility:
   ```bash
   python3 tools/flow_completion.py consolidate {flow_id}
   ```
2. **Identify**: Read `extracted_learnings.md` and `spec.md` from the flow. Identify which discoveries are one-off observations and which represent **Core Patterns** or **Architectural Shifts**.
3. **Synthesize**: Integrate these discoveries directly into cohesive, logically organized knowledge base chapters in `.agents/bundles/knowledge/` (e.g., `product/`, `workflow/`, `patterns/`, `code-styleguides/`).
4. **Update the State**: Revise these chapters to reflect the *current* authoritative state of the codebase.
5. **No History Logs**: Do NOT outline history or create per-flow logs in the knowledge base. The chapters must provide the high-definition implementation details needed for a new agent to become an instant expert on the current state.

## Phase 4: Delete Flow Bundle

1. **Delete Bundle Directory:** Run the safe deletion command:

   ```bash
   python3 tools/flow_completion.py delete {flow_id}
   ```

## Final Output

```text
Flow Archived: {flow_id}

Spec deleted from filesystem
Patterns Elevated: {count}

Project patterns updated. View with:
cat .agents/patterns.md
```
