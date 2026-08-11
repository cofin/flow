---
description: Archive completed flows + elevate patterns
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Archive

> Lifecycle skill: use `flow-completion` through the `flow` router.

Archiving flow: **$ARGUMENTS**

## Phase 1: Validation

### 1.1 Resolve Flow ID

If not provided, dynamically scan the `.agents/bundles/specs/` directory to discover active/completed flows and ask the user to select.

### 1.3 Verify Completion

Read the `.agents/bundles/specs/{flow_id}/spec.md` Implementation Plan section (or scan task files under `.agents/bundles/specs/{flow_id}/tasks/*.md`) to check completion status.

- If uncompleted tasks exist: "Warning: Flow has incomplete tasks. Continue? (y/n)" → Halt if 'n'.

---

## Phase 2: Pattern Elevation

1. Read `.agents/bundles/specs/{flow_id}/learnings.md`.
2. Read `.agents/bundles/knowledge/patterns/patterns.md`.
3. Identify new patterns not present in global patterns.
4. **Interactive Selection:**
   - "Found these potential patterns:"
   - [ ] Pattern 1
   - [ ] Pattern 2
   - "Select patterns to elevate (or 'all'/'none'):"
5. **Merge:** Append selected patterns to `.agents/bundles/knowledge/patterns/patterns.md`.
   - Format: `- {new pattern} (from: {flow_id})`

---

## Phase 3: Knowledge Synthesis

1. Create `.agents/bundles/knowledge/` if missing.
2. Read `.agents/bundles/specs/{flow_id}/learnings.md` (or consolidated learnings) and `.agents/bundles/specs/{flow_id}/spec.md`.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters under `.agents/bundles/knowledge/` (e.g., `product/`, `workflow/`, `patterns/`, `code-styleguides/`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

---

## Phase 4: Delete Flow Bundle

1. **Log Flow Completion:**
   Append metadata of the completed flow (ID, Title, completion timestamp) to `.agents/bundles/knowledge/log.md`.

2. **Delete Flow Bundle Directory:**

   ```bash
   rm -rf .agents/bundles/specs/{flow_id}/
   ```

---

## Phase 5: Git Commit

1. **Check Ignore Status:**

   ```bash
   git check-ignore .agents/
   ```

2. **Commit Changes (if not ignored):**

   ```bash
   git add .agents/bundles/knowledge/
   git rm -r .agents/bundles/specs/{flow_id}/
   git commit -m "chore(archive): archive {flow_id} and elevate patterns"
   ```

   *If ignored, skip commit and notify user.*

---

## Phase 6: Completion

> "Flow '{flow_id}' archived successfully.
>
> **Summary:**
>
> - ID: {flow_id}
> - Spec deleted from filesystem
> - Patterns Elevated: {count}
> - Logged in .agents/bundles/knowledge/log.md
>
> Ready for next flow: `/flow-prd`"
