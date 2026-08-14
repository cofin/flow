
# Flow Finish

Complete a flow's development work by verifying, reviewing, and integrating.

## Usage

`flow-finish {flow_id}` or `flow-finish` (uses current flow)

## Phase 1: Load Context

1. **Read Flow Artifacts:**
   - `.agents/bundles/specs/{flow_id}/spec.md` (frontmatter carries the flow metadata)
2. **Verify all tasks completed:** Read all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` and ensure their frontmatter `state` is `closed` or `skipped`. If any task is open, in progress, or blocked, stop; `complete` cannot bypass terminal task state.

## Phase 2: Verification Gate

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

1. **Run full test suite** — read output, confirm 0 failures
2. **Run coverage check** — confirm target met with actual numbers
3. **Run linter/formatter** — confirm clean output
4. **Sync Spec Checklist:** Run `/flow:sync` to reconcile spec.md task checklists with task files.
5. **Record phase evidence:** Put the exact command/results and affected task ids in a spec-only phase `checkpoint` payload targeting the last functional commit. Never create an empty checkpoint commit.
6. **Optional detailed evidence:** Only after the checkpoint succeeds, append a `flow-git-note-v1` record to that same commit and record `attached|failed` through the idempotent `note(category=git_note_attachment)` state operation. Git notes remain supplementary; never push them automatically.

**If any check fails:** Report actual results. Do NOT proceed until issues resolved.

## Phase 3: Correctness Review

Dispatch final comprehensive code review:

1. **Get git range:** Locate the Git range by finding the merge-base between main and the current branch:

   ```bash
   git log --oneline $(git merge-base main HEAD)..HEAD
   ```

2. **Dispatch code review subagent** with:
   - What was implemented (from spec.md Specification section)
   - Requirements (from spec.md Requirements section)
   - Git range (base to HEAD)
   - Project patterns (from `.agents/bundles/knowledge/patterns.md`)

3. **Handle results:**
   - **Critical issues** → must fix before proceeding
   - **Important issues** → should fix, confirm with user
   - **Minor issues** → note in learnings.md

4. **Log review findings** to `.agents/bundles/specs/{flow_id}/learnings.md`

**Reference:** `superpowers:requesting-code-review` for dispatch pattern

## Phase 4: Mandatory Quality Review

After correctness review passes, follow the `quality-review-v1` contract in
[Review](review.md):

1. Freeze the exact final `base_commit` and `head_commit`. For a one-commit
   change, use that commit's parent as base and the commit as head.
2. Load `.agents/skills/debloat/SKILL.md`, else packaged
   `skills/debloat/SKILL.md`, else the synchronized inline fallback and record
   `debloat_source: inline_fallback`.
3. Dispatch the read-only `quality-reviewer` on that exact range after the
   correctness reviewer. A waiver never substitutes for dispatch.
4. Require an exact-range `QualityReport`. Reject stale base/head evidence.
5. If any Critical/Important finding remains, stop and route through `revise`
   to create or adjust a remediation task. Execute it, rerun affected
   verification and correctness review, then always dispatch a fresh quality
   review on the new exact range.
6. A fresh explicit user waiver may address one named finding only after
   review ran. Record finding id, rationale, approval text/time, compensating
   evidence, and exact range. Other findings remain active.

## Phase 5: Complete the Flow

Request the spec-only `complete` operation only after the ordered gates
`verification -> code_review -> quality_review -> finish` pass. Include the
final functional commit, exact verification and correctness-review evidence,
the fresh `QualityReport`, and any finding-specific waivers. The state sidecar
sets `state: completed`; never edit that field directly.

## Phase 6: Present Options

Present exactly these 4 options:

```text
Flow '{flow_id}' implementation complete and verified. What would you like to do?

1. Merge back to {base_branch} locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

## Phase 7: Execute Choice

### Option 1: Merge Locally

```bash
git checkout {base_branch}
git pull
git merge {feature_branch}
# Run tests on merged result
git branch -d {feature_branch}
```

After merge: suggest running `flow-archive {flow_id}` to elevate patterns.

### Option 2: Push and Create PR

```bash
git push -u origin {feature_branch}
gh pr create --title "{pr_title}" --body "$(cat <<'EOF'
## Summary
{bullets from spec.md}

## Test Plan
- [ ] All tests passing ({count} tests)
- [ ] Coverage at {X}%
- [ ] Code review completed

## Flow
- Flow ID: {flow_id}
- Spec: .agents/bundles/specs/{flow_id}/spec.md
EOF
)"
```

After PR: suggest running `flow-archive {flow_id}` after merge.

### Option 3: Keep As-Is

Report: "Keeping branch `{branch_name}`. Flow artifacts preserved."

### Option 4: Discard

**Confirm first:**

```text
This will permanently delete:
- Branch {branch_name}
- All commits since {base_sha}

Type 'discard' to confirm.
```

Wait for exact confirmation. If confirmed:

```bash
git checkout {base_branch}
git branch -D {feature_branch}
```

## Phase 8: Worktree Cleanup

If working in a git worktree:

```bash
git worktree list | grep {feature_branch}
```

- **Options 1, 4:** Remove worktree: `git worktree remove {path}`
- **Option 2:** Keep worktree until PR merges
- **Option 3:** Keep worktree

## Critical Rules

1. **VERIFY BEFORE OPTIONS** — Never present options with failing tests
2. **ORDERED GATES** — Verification, correctness review, and mandatory quality review all pass on the same fresh exact range before finish/options
3. **CONFIRM DISCARD** — Require typed "discard" for Option 4
4. **SUGGEST ARCHIVE** — After merge/PR, prompt for `flow-archive`
5. **UPDATE SPEC STATE THROUGH SIDECAR** — Request `complete`; never edit `state`/`status` directly.
6. **MARKDOWN AUTHORITY** — Completion and recovery use the sidecar-written checkpoint and task evidence; optional Git notes never replace it.
7. **NO GIT TAGS** — Never create or mutate Git tags for completion evidence or as a notes fallback.
8. **NO REVIEW WAIVER** — A finding-specific waiver cannot replace quality-review dispatch or waive another/stale finding.
