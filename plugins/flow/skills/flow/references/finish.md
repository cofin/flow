# Flow Finish

Complete a flow's development work by verifying, reviewing, closing the spec, and choosing an integration or archive action.

## Contents

- [Load context and scope-cap check](#phase-1-load-context--scope-cap-check)
- [Verification gate](#phase-2-verification-gate)
- [Correctness and quality review](#phase-3-correctness-review)
- [Complete the flow (branch-local)](#phase-5-complete-the-flow-branch-local)
- [Present options and execute choice](#phase-6-present-options)
- [Worktree cleanup and critical rules](#phase-8-worktree-cleanup)

## Usage

`flow-finish {flow_id}` or `flow-finish` (uses current flow)

## Phase 1: Load Context & Scope-Cap Check

1. **Read Flow Artifacts:**
   - `.agents/bundles/specs/{flow_id}/spec.md` (frontmatter carries the flow metadata)
2. **Verify all tasks completed:** Read all task files under `.agents/bundles/specs/{flow_id}/tasks/*.md` and ensure their frontmatter `state` is `closed` or `skipped`.
3. **Pragmatic Closure & Scope-Cap Rule (No Infinite Open Loops):**
   - **Never block a flow from closing because a branch or PR is not yet merged into `main`.** Flow completion (`state: completed`) and archiving (`flow-archive`) are branch-local lifecycle transitions based on local verification of the spec's tasks.
   - If any remaining `open` or `blocked` task represents newly discovered scope, adjacent refactoring, or feature expansion beyond the spec's core acceptance criteria—or if the spec has grown too large (`> 8-10` tasks or `> 2` revision rounds)—ask the user to `skip` those out-of-scope tasks on this flow and **spawn a new follow-up spec** (`/flow:plan <new_flow_id>`) so the current spec can close cleanly.

## Phase 2: Verification Gate

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

1. **Run full test suite** — read output, confirm 0 failures
2. **Run coverage check** — confirm target met with actual numbers (when defined by repo/spec)
3. **Run linter/formatter** — confirm clean output
4. **Sync Spec Checklist:** Run `/flow:sync` to reconcile `spec.md` task checklists and `Continuity Snapshot` with task files.
5. **Record phase evidence:** Put the exact command/results and affected task ids in a spec-only phase `checkpoint` payload targeting the last functional commit. Never create an empty checkpoint commit.
6. **Optional detailed evidence:** Only after the checkpoint succeeds, append a `flow-git-note-v1` record to that same commit and record `attached|failed` through the idempotent `note(category=git_note_attachment)` state operation. Git notes remain supplementary; never push them automatically.

**If any check fails:** Report actual results. Do NOT proceed until issues are resolved.

## Phase 3: Correctness Review

Dispatch final comprehensive code review:

1. **Get git range:** Locate the Git range between the base branch (or flow start commit) and `HEAD`:

   ```bash
   git log --oneline $(git merge-base main HEAD)..HEAD
   ```

2. **Dispatch code review subagent** with:
   - What was implemented (from `spec.md` Specification section)
   - Requirements (from `spec.md` Requirements section)
   - Git range (`base_commit..head_commit`)
   - Relevant project patterns (recursively from `.agents/bundles/knowledge/patterns/**/*.md`)

3. **Handle results pragmatically:**
   - **Critical issues / broken acceptance criteria** → must fix before proceeding.
   - **Important issues within current spec scope** → fix or obtain an explicit user waiver.
   - **Scope-expanding suggestions, adjacent refactors, or Minor issues** → do **NOT** reopen the flow into an endless remediation loop; log them to `.agents/bundles/specs/{flow_id}/learnings.md` or propose a **new follow-up spec** (`/flow:plan`).

## Phase 4: Mandatory Quality Review

After correctness review passes, follow the `quality-review-v1` contract in [Review](review.md):

1. Freeze the exact final `base_commit` and `head_commit`. For a one-commit change, use that commit's parent as base and the commit as head.
2. Load `.agents/skills/debloat/SKILL.md`, else packaged `skills/debloat/SKILL.md`, else the synchronized inline fallback and record `debloat_source: inline_fallback`.
3. Dispatch the read-only `quality-reviewer` on that exact range after the correctness reviewer. A waiver never substitutes for dispatch.
4. Require an exact-range `QualityReport`. Reject stale base/head evidence.
5. If an unwaived Critical/Important defect within the current spec's diff remains, route a narrow remediation through `revise`, execute it, and rerun affected verification and review on the new exact range. If a finding requests a broader architectural refactor outside the spec's scope, record a user waiver or spin off a **new follow-up spec** rather than trapping the current spec in a loop.
6. A fresh explicit user waiver may address one named finding only after review ran. Record finding id, rationale, approval text/time, compensating evidence, and exact range.

## Phase 5: Complete the Flow (Branch-Local)

Request the spec-only `complete` operation immediately after the ordered gates `verification -> code_review -> quality_review -> finish` pass on the current branch. Include the final functional commit, exact verification and correctness-review evidence, the fresh `QualityReport`, and any finding-specific waivers. The state sidecar sets `state: completed` and updates `spec.md` status on disk; never wait for a remote PR merge to mark the spec `completed`.

## Phase 6: Present Options

Present these 4 options:

```text
Flow '{flow_id}' is marked completed and verified on this branch. What would you like to do next?

1. Archive flow now (synthesize knowledge & patterns, contract spec) and keep/PR branch
2. Merge back to {base_branch} locally (and archive flow)
3. Push and create a Pull Request
4. Discard this work

Which option?
```

## Phase 7: Execute Choice

### Option 1: Archive Flow Now on Current Branch (Recommended)

Run `/flow:archive {flow_id}` immediately on the current branch so deep 5-dimension knowledge and pattern synthesis (`knowledge/**` + `log.md`) and spec directory contraction are committed directly to the branch before or alongside a PR.

### Option 2: Merge Locally

```bash
git checkout {base_branch}
git pull
git merge {feature_branch}
git branch -d {feature_branch}
```

Run `/flow:archive {flow_id}` before or immediately after merging so durable knowledge and patterns are synthesized into `.agents/bundles/knowledge/`.

### Option 3: Push and Create PR

If the user has not yet archived the completed spec, offer to run `/flow:archive {flow_id}` first so the PR includes the synthesized knowledge and clean spec contraction, or push and create the PR directly:

```bash
git push -u origin {feature_branch}
gh pr create --title "{pr_title}" --body "$(cat <<'EOF'
## Summary
{bullets from spec.md}

## Test Plan
- [x] All tests passing ({count} tests)
- [x] Code and quality review completed

## Flow
- Flow ID: {flow_id}
EOF
)"
```

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
git branch -d {feature_branch}
```

`git branch -d` refuses an unmerged branch; if the user wants to discard unmerged work, ask them to run `git branch -D {feature_branch}` themselves.

## Phase 8: Worktree Cleanup

If working in a git worktree:

```bash
git worktree list | grep {feature_branch}
```

- **Options 2, 4:** Remove worktree: `git worktree remove {path}`
- **Options 1, 3:** Keep worktree while branch remains active

## Critical Rules

1. **VERIFY BEFORE OPTIONS** — Never mark complete or present options with failing tests.
2. **BRANCH-LOCAL CLOSURE** — Never block `complete` or `archive` waiting for a branch or PR to merge into `main`.
3. **NEW SPEC OVER SCOPE CREEP** — When follow-up ideas or adjacent refactors emerge, close the current spec and plan a new spec rather than looping endlessly.
4. **ORDERED GATES** — Verification, correctness review, and mandatory quality review all pass on the same fresh exact range before `complete`.
5. **CONFIRM DISCARD** — Require typed "discard" for Option 4.
6. **RIGOROUS ARCHIVE** — Prompt for `/flow:archive` so knowledge and patterns are synthesized before the spec disappears.
7. **UPDATE SPEC STATE THROUGH SIDECAR** — Request `complete`; never edit `state` ad hoc.
8. **MARKDOWN AUTHORITY** — Completion and recovery use the sidecar-written checkpoint and task evidence; optional Git notes never replace it.
9. **NO GIT TAGS** — Never create or mutate Git tags for completion evidence or as a notes fallback.
10. **NO REVIEW WAIVER** — A finding-specific waiver cannot replace quality-review dispatch or waive another/stale finding.
