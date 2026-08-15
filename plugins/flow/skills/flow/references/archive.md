
# Flow Archive

Archiving is a contraction: durable knowledge moves into the knowledge chapters, one line lands in the bundle log, and the spec directory is deleted — including the flow's promoted `research/`. `.agents/bundles/specs/` holds only planned and active flows.

## Tracking Policy (Stealth Mode)

Contraction does not depend on Git. Read `workflow_preferences.ignore_policy`
from `<configured-root>/setup-state.json`; if absent, ask once and persist it.

- **`shared`** — bundles are tracked; step 7 writes the archive commit.
- **`local-only` (stealth mode)** — nothing in `.agents/` is committed.
  Contraction runs identically, minus the commit. Deleted bytes are
  unrecoverable: an accepted risk of the mode, not a warning to re-raise per
  archive. Knowledge chapters and `log.md` are the whole durable record, so keep
  a borderline learning rather than dropping it.

Never force-add ignored Flow files to make an archive "recoverable".

Git notes under `refs/notes/flow` are supplementary audit evidence only. Their
absence or an attachment failure never changes archive eligibility: canonical
Markdown and the archive journal are sufficient for recovery. Archive never
pushes, copies, rewrites, prunes, or requires the notes ref.
Never create or mutate Git tags for archive evidence or as a notes fallback.

Archive follows the ordered gates `archive_candidate -> verification ->
code_review -> quality_review -> archive`. The quality gate is mandatory and
uses the `quality-review-v1` contract in [Review](review.md).

## Procedure

1. **Validate**: resolve the flow id (scan spec frontmatter for `state: completed` when not given). Confirm every task file is `state: closed` or `skipped`; abort otherwise. Resolve the tracking policy above. Under `shared`, check recoverability with `git ls-files --error-unmatch` — an untracked bundle in a shared repo is an anomaly and needs explicit user confirmation. Under `local-only`, skip the check: untracked is the configured state.
2. **Render candidate (no live contraction yet)**:
   - Consolidate all task `## Notes & Discoveries`, `learnings.md`, and promoted `research/` content into a transient working list.
   - Research is contracted, not shelved. Findings that still describe how the
     codebase or its dependencies work belong in `knowledge/`; findings that
     only justified a decision already made are dropped. Do not copy research
     verbatim into a knowledge chapter, and never relocate it to an archive
     directory — `bundles/research/` is for un-promoted work only.
   - Map each durable learning to its existing project-shaped chapter recursively under `knowledge/`: conventions/gotchas → `knowledge/patterns.md`; workflow changes → `knowledge/workflow.md`; architecture → the relevant nested architecture chapter; style/domain rules → the matching nested topic chapter; product changes → `product/` docs. Never flatten nested knowledge into invented top-level files.
   - Rewrite each affected chapter as coherent current-state documentation: integrate into existing prose, update stale statements, merge duplicates. No dated entries, no flow attributions, no changelog lines, no "completed X" notes in knowledge chapters — history belongs in `log.md` only.
   - Present proposed chapter edits for user approval before writing. Skip low-value notes rather than hoarding them.
   - Delete any leftover `extracted_learnings.md` — consolidated views are transient.
   - Render the complete archive request: knowledge destinations and full before/after bytes, log entry, notes incorporation, sorted archive inventory, and full file fragments for every spec deletion. The deletion inventory covers the entire spec directory — `spec.md`, `tasks/`, `learnings.md`, and `research/`.
3. **Create disposable local review range**: apply only the rendered candidate in a disposable local branch/worktree and commit it. Its parent is `base_commit`; the candidate commit is `head_commit`. This range must contain the exact knowledge, log, and deletion bytes from the rendered manifest. Never use a Git tag and never push the candidate.
4. **Review exact candidate**:
   - Run archive-relevant verification on `base_commit..head_commit`.
   - Run correctness review on that exact range.
   - Always dispatch the read-only `quality-reviewer` afterward on the same range. Resolve `.agents/skills/debloat/SKILL.md`, then packaged `skills/debloat/SKILL.md`, then the inline fallback.
   - Critical/Important findings block archive. Route remediation through `revise`, execute it, render a new candidate, and rerun verification, correctness review, and a fresh quality review.
   - A fresh user waiver applies to one named finding and this range only; it cannot replace dispatch.
5. **Bind candidate**: compare the requested `archive_candidate_manifest` and every before/after fragment byte-for-byte with the reviewed candidate. Any changed knowledge, log, inventory, deletion, base, or head invalidates the report; render and review a new candidate range.
6. **Request archive**: submit the exact range, byte-identical manifest, verification/code/quality evidence, and finding-specific waivers to the state sidecar. The sidecar journals and applies knowledge first, log second, and spec deletion last. Do not delete the live spec directory directly.
7. **Commit** (`shared` policy only): after the archive transaction commits and postconditions pass, stage only its recorded bundle paths and create one `chore(archive)` commit. Under `local-only`, the archive is complete when the transaction's postconditions pass — skip this step entirely rather than force-adding ignored paths.

## Verification

```bash
ls .agents/bundles/specs/          # archived flow gone; only planned/active remain
ls .agents/bundles/research/       # un-promoted research only; nothing for the archived flow
head -20 .agents/bundles/log.md    # new archive entry at the top
```

Knowledge chapters must read as if written fresh today — an agent reading `knowledge/` should learn how the codebase works now, never which flow taught us.

The postcondition bytes must equal the reviewed candidate manifest exactly. A
different archive fragment is not a small follow-up; it is a new candidate that
requires a fresh range and all three review gates.
