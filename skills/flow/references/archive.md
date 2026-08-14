
# Flow Archive

Archiving is a contraction: durable knowledge moves into the knowledge chapters, one line lands in the bundle log, and the spec directory is deleted. Git history is the archive — `.agents/bundles/specs/` holds only planned and active flows.

Git notes under `refs/notes/flow` are supplementary audit evidence only. Their
absence or an attachment failure never changes archive eligibility: canonical
Markdown and the archive journal are sufficient for recovery. Archive never
pushes, copies, rewrites, prunes, or requires the notes ref.
Never create or mutate Git tags for archive evidence or as a notes fallback.

## Procedure

1. **Validate**: resolve the flow id (scan spec frontmatter for `state: completed` when not given). Confirm every task file is `state: closed` or `skipped`; abort otherwise. Check recoverability with `git ls-files --error-unmatch` — if the bundle is untracked, deletion is unrecoverable and needs explicit user confirmation.
2. **Synthesize (RE-synthesize, never append)**:
   - Consolidate all task `## Notes & Discoveries` and `learnings.md` content into a transient working list.
   - Map each durable learning to its chapter: conventions/gotchas → `knowledge/patterns.md`; workflow changes → `knowledge/workflow.md`; architecture → `knowledge/architecture.md`; style rules → `knowledge/<topic>-style.md`; product changes → `product/` docs.
   - Rewrite each affected chapter as coherent current-state documentation: integrate into existing prose, update stale statements, merge duplicates. No dated entries, no flow attributions, no changelog lines, no "completed X" notes in knowledge chapters — history belongs in `log.md` only.
   - Present proposed chapter edits for user approval before writing. Skip low-value notes rather than hoarding them.
   - Delete any leftover `extracted_learnings.md` — consolidated views are transient.
3. **Log**: one entry in `.agents/bundles/log.md` under today's ISO date: flow id, one-line outcome, final commit SHA, chapters touched. Update `index.md` if it lists the flow.
4. **Delete** `.agents/bundles/specs/{flow_id}/`.
5. **Commit** (tracked bundles only): stage the bundle, `git rm` the spec directory, one `chore(archive)` commit.

## Verification

```bash
ls .agents/bundles/specs/          # archived flow gone; only planned/active remain
head -20 .agents/bundles/log.md    # new archive entry at the top
```

Knowledge chapters must read as if written fresh today — an agent reading `knowledge/` should learn how the codebase works now, never which flow taught us.
