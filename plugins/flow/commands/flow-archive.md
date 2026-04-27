---
description: Archive completed flows + elevate patterns
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Archive

> **Beads mode:** Skip every `bd` invocation below when the SessionStart hook reports `Beads Backend: Missing (None)` or `Disabled via plugin config (useBeads=false)`. Treat `spec.md` markers as fallback source of truth and skip `/flow:sync`. Never halt for missing Beads. See `skills/flow/references/discipline.md`.
>
> Lifecycle skill: use `flow-completion` through the `flow` router.

Archiving flow: **$ARGUMENTS**

## Phase 1: Validation

### 1.1 Resolve Flow ID

If not provided, list completed flows from `.agents/flows.md` and ask user to select.

### 1.3 Verify Completion

Check Beads for completion status:

```bash
bd show {epic_id}
```

Or read `.agents/specs/{flow_id}/spec.md` Implementation Plan section.

- If uncompleted tasks exist: "Warning: Flow has incomplete tasks. Continue? (y/n)" → Halt if 'n'.

---

## Phase 2: Pattern Elevation

1. Read `.agents/specs/{flow_id}/learnings.md`.
2. Read `.agents/patterns.md`.
3. Identify new patterns not present in global patterns.
4. **Interactive Selection:**
   - "Found these potential patterns:"
   - [ ] Pattern 1
   - [ ] Pattern 2
   - "Select patterns to elevate (or 'all'/'none'):"
5. **Merge:** Append selected patterns to `.agents/patterns.md`.
   - Format: `- {new pattern} (from: {flow_id})`

---

## Phase 3: Knowledge Synthesis

1. Create `.agents/knowledge/` if missing.
2. Read `learnings.md`, `spec.md` header, and `metadata.json` from the flow.
3. Synthesize learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`).
4. Update the current state of these documents. Do NOT outline history or create per-flow logs. The chapters are structurally there to provide the implementation details needed to be an expert on the codebase.

---

## Phase 4: Archive Artifacts

1. Create `.agents/archive/` if missing.
2. **Generate Summary:**
   Create `.agents/archive/{flow_id}/summary.md`:

   ```markdown
   # Archive Summary: {flow_id}
   **Archived:** {date}
   **Status:** Complete
   **Elevated Patterns:**
   - {list elevated patterns}
   ```

3. **Move Directory:**

   ```bash
   mv .agents/specs/{flow_id} .agents/archive/{flow_id}
   ```

4. **Update Metadata:**
   Update `.agents/archive/{flow_id}/metadata.json`:
   - Set `"status": "archived"`
   - Set `"archived_at": "{timestamp}"`

---

## Phase 5: Registry Update

Edit `.agents/flows.md`:

1. Find entry for `{flow_id}`.
2. Move from "Active" section to "Archived" section.
3. Update link to: `[./archive/{flow_id}/](./archive/{flow_id}/)`

---

## Phase 6: Beads Cleanup

1. Get `beads_epic_id` from metadata.
2. Close epic:

   ```bash
   bd close {epic_id} --reason "Flow archived"
   ```

3. Verify closure:

   ```bash
   bd show {epic_id}
   ```

---

## Phase 7: Git Commit

1. **Check Ignore Status:**

   ```bash
   git check-ignore .agents/
   ```

2. **Commit (if not ignored):**

   ```bash
   git add .agents/patterns.md .agents/flows.md .agents/knowledge/ .agents/archive/{flow_id}/
   git commit -m "chore(archive): {flow_id} complete"
   ```

   *If ignored, skip commit and notify user.*

---

## Phase 8: Completion

> "Flow '{flow_id}' archived successfully.
>
> **Summary:**
>
> - ID: {flow_id}
> - Location: .agents/archive/{flow_id}/
> - Patterns Elevated: {count}
>
> Ready for next flow: `/flow-prd`"
