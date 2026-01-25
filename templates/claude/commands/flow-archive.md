---
description: Archive completed track and elevate patterns
argument-hint: <track_id>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Flow Archive

Archiving track: **$ARGUMENTS**

## Phase 1: Verify Completion

Check all tasks in plan.md are `[x]` or `[-]`.

If incomplete tasks exist:
> Track has {N} incomplete tasks. Archive anyway? (yes/no)

---

## Phase 2: Pattern Elevation

Read `.agent/specs/{track_id}/learnings.md`.

For each learning entry:

> **Elevate to patterns.md?**
>
> Learning: {description}
>
> - Yes - Add to project patterns
> - No - Track-specific only

---

## Phase 3: Update patterns.md

For elevated patterns, append to `.agent/patterns.md`:

```markdown
## Code Conventions

- {new pattern} (from: {track_id})
```

---

## Phase 4: Generate Summary

Create archive summary:

```markdown
# Archive Summary: {track_id}

**Completed:** {date}
**Duration:** {days from creation to completion}
**Tasks:** {completed}/{total}

## Key Accomplishments

{list main deliverables}

## Patterns Extracted

{list patterns elevated to patterns.md}

## Files Modified

{list of files created/changed}

## Commits

{list of commit SHAs}
```

---

## Phase 5: Move to Archive

```bash
mv .agent/specs/{track_id} .agent/archive/{track_id}
```

---

## Phase 6: Update Registry

In `.agent/prds.md`:
- Change status: `[ ]` -> `[x]`
- Add completion date

---

## Phase 7: Beads Cleanup

```bash
bd close {epic_id} --reason "Archived"
```

If beads.json has `compactOnArchive: true`:
```bash
bd compact {epic_id}
```

---

## Phase 8: Final Commit

```bash
git add .agent/
git commit -m "flow(archive): {track_id} complete"
```

---

## Final Summary

```
Track Archived

ID: {track_id}
Location: .agent/archive/{track_id}/
Duration: {N} days

Patterns Elevated: {count}
Tasks Completed: {count}
Commits: {count}

Next: Start a new track with `/flow-newtrack`
```

---

## Critical Rules

1. **VERIFY COMPLETION** - Warn if incomplete tasks
2. **ELEVATE PATTERNS** - Don't lose learnings
3. **PRESERVE HISTORY** - Move, don't delete
4. **BEADS SYNC** - Close epic in Beads
