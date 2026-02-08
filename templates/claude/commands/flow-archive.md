---
description: Archive a completed flow and elevate learnings
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Archive

Archiving flow: **$ARGUMENTS**

## Phase 1: Sync and Validation

### 1.1 Sync Beads State to spec.md

**CRITICAL:** Run `/flow-sync {flow_id}` FIRST to export current Beads state to spec.md before archiving.

This ensures spec.md reflects the final state from Beads (source of truth).

### 1.2 Resolve Flow ID

If not provided, list completed flows from `.agent/flows.md` and ask user to select.

### 1.3 Verify Completion

Check Beads for completion status:

```bash
bd show {epic_id}
```

Or read `.agent/specs/{flow_id}/spec.md` Implementation Plan section.

- If uncompleted tasks exist: "Warning: Flow has incomplete tasks. Continue? (y/n)" → Halt if 'n'.

---

## Phase 2: Pattern Elevation

1. Read `.agent/specs/{flow_id}/learnings.md`.
2. Read `.agent/patterns.md`.
3. Identify new patterns not present in global patterns.
4. **Interactive Selection:**
   - "Found these potential patterns:"
   - [ ] Pattern 1
   - [ ] Pattern 2
   - "Select patterns to elevate (or 'all'/'none'):"
5. **Merge:** Append selected patterns to `.agent/patterns.md`.
   - Format: `- {new pattern} (from: {flow_id})`

---

## Phase 3: Archive Artifacts

1. Create `.agent/archive/` if missing.
2. **Generate Summary:**
   Create `.agent/archive/{flow_id}/summary.md`:
   ```markdown
   # Archive Summary: {flow_id}
   **Archived:** {date}
   **Status:** Complete
   **Elevated Patterns:**
   - {list elevated patterns}
   ```
3. **Move Directory:**
   ```bash
   mv .agent/specs/{flow_id} .agent/archive/{flow_id}
   ```
4. **Update Metadata:**
   Update `.agent/archive/{flow_id}/metadata.json`:
   - Set `"status": "archived"`
   - Set `"archived_at": "{timestamp}"`

---

## Phase 4: Registry Update

Edit `.agent/flows.md`:
1. Find entry for `{flow_id}`.
2. Move from "Active" section to "Archived" section.
3. Update link to: `[./archive/{flow_id}/](./archive/{flow_id}/)`

---

## Phase 5: Beads Cleanup

1. Get `beads_epic_id` from metadata.
2. Close epic:
   ```bash
   bd close {epic_id} --reason "Flow archived"
   ```
3. Compact Beads (optional but recommended):
   ```bash
   bd compact
   # Or for aggressive compaction:
   # bd mol squash
   ```

---

## Phase 6: Git Commit

1. **Check Ignore Status:**
   ```bash
   git check-ignore .agent/
   ```
2. **Commit (if not ignored):**
   ```bash
   git add .agent/
   git commit -m "flow(archive): {flow_id} complete"
   ```
   *If ignored, skip commit and notify user.*

---

## Phase 7: Completion

> "Flow '{flow_id}' archived successfully.
>
> **Summary:**
> - ID: {flow_id}
> - Location: .agent/archive/{flow_id}/
> - Patterns Elevated: {count}
>
> Ready for next flow: `/flow-prd`"