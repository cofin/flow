
# Flow Finish

Complete a flow's development work by verifying, reviewing, and integrating.

## Usage

`flow-finish {flow_id}` or `flow-finish` (uses current flow)

## Phase 1: Load Context

1. **Read Flow Artifacts:**
   - `.agents/specs/{flow_id}/spec.md`
   - `.agents/specs/{flow_id}/metadata.json`
2. **Load Beads context:**

   ```bash
   bd show {epic_id}
   ```

3. **Verify all tasks completed** — check Beads for any open tasks:

   ```bash
   bd list --parent {epic_id} --status open
   ```

   If open tasks remain, warn and confirm with user before proceeding.

## Phase 2: Verification Gate

```text
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

1. **Run full test suite** — read output, confirm 0 failures
2. **Run coverage check** — confirm target met with actual numbers
3. **Run linter/formatter** — confirm clean output
4. **Sync Beads to spec.md:**

   ```bash
   # Ensure spec.md reflects current state
   ```

   Run `/flow:sync` to update spec.md from Beads.

**If any check fails:** Report actual results. Do NOT proceed until issues resolved.

## Phase 3: Code Review

Dispatch final comprehensive code review:

1. **Get git range** from Beads task completion records:

   ```bash
   # Base: commit before first task started
   # Head: current HEAD
   git log --oneline {base_sha}..HEAD
   ```

2. **Dispatch code review subagent** with:
   - What was implemented (from spec.md Specification section)
   - Requirements (from spec.md Requirements section)
   - Git range (base to HEAD)
   - Project patterns (from `.agents/patterns.md`)

3. **Handle results:**
   - **Critical issues** → must fix before proceeding
   - **Important issues** → should fix, confirm with user
   - **Minor issues** → note in learnings.md

4. **Log review findings** to `.agents/specs/{flow_id}/learnings.md`

**Reference:** `superpowers:requesting-code-review` for dispatch pattern

## Phase 4: Present Options

Present exactly these 4 options:

```text
Flow '{flow_id}' implementation complete and verified. What would you like to do?

1. Merge back to {base_branch} locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

## Phase 5: Execute Choice

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
- Spec: .agents/specs/{flow_id}/spec.md
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

## Phase 6: Beads Cleanup

For Options 1, 2 (successful completion):

```bash
bd close {epic_id} --reason "Flow finished: {option_chosen}"
```

For Option 4 (discard):

```bash
bd close {epic_id} --reason "Flow discarded"
```

## Phase 7: Worktree Cleanup

If working in a git worktree:

```bash
git worktree list | grep {feature_branch}
```

- **Options 1, 4:** Remove worktree: `git worktree remove {path}`
- **Option 2:** Keep worktree until PR merges
- **Option 3:** Keep worktree

## Critical Rules

1. **VERIFY BEFORE OPTIONS** — Never present options with failing tests
2. **CODE REVIEW FIRST** — Dispatch review before presenting options
3. **CONFIRM DISCARD** — Require typed "discard" for Option 4
4. **SUGGEST ARCHIVE** — After merge/PR, prompt for `flow-archive`
5. **SYNC BEADS** — Close epic after executing choice
