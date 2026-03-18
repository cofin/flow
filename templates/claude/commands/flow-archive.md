---
description: Archive completed flows + elevate patterns
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Archive

Archiving flow: **$ARGUMENTS**

## Phase 1: Validation

### 1.1 Resolve Flow ID

If not provided, list completed flows from `.agents/flows.md` and ask user to select.

### 1.3 Verify Completion

Check Beads for completion status:

```bash
br show {epic_id}
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

## Phase 3: Knowledge Extraction

1. Create `.agents/knowledge/` if missing.
2. Read `learnings.md`, `spec.md` header, and `metadata.json` from the flow.
3. Generate `.agents/knowledge/{flow_id}.md` with:
   ```markdown
   # Knowledge: {flow_id}

   **Flow:** {flow_id}
   **Description:** {from metadata/spec}
   **Completed:** {date}
   **Archived:** {today}

   ## Topics
   {lowercase, comma-separated tags: e.g., authentication, middleware, testing}

   ## Patterns Elevated
   - {patterns selected for elevation in Phase 2}

   ## All Learnings
   {verbatim learnings.md content}

   ## Key Files
   {files mentioned in learnings entries}

   ## Summary
   {2-3 sentence auto-generated summary}
   ```
4. Update `.agents/knowledge/index.md`:
   - Append row to Entries table: `| {flow_id} | {date} | {topics} | {summary} |`
   - Add entries under Topic Index headings (create headings if new)

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
   br close {epic_id} --reason "Flow archived"
   ```
3. Verify closure:
   ```bash
   br show {epic_id}
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
   git commit -m "flow(archive): {flow_id} complete"
   ```
   *If ignored, skip commit and notify user.*

---

## Phase 8: Completion

> "Flow '{flow_id}' archived successfully.
>
> **Summary:**
> - ID: {flow_id}
> - Location: .agents/archive/{flow_id}/
> - Patterns Elevated: {count}
>
> Ready for next flow: `/flow-prd`"