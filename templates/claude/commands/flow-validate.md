---
description: Validate project integrity and fix issues
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Validate

Validate Flow project integrity and optionally fix issues.

## Phase 1: Directory Structure

Check required files exist:
- [ ] `.agent/product.md`
- [ ] `.agent/tech-stack.md`
- [ ] `.agent/workflow.md`
- [ ] `.agent/beads.json`
- [ ] `.agent/prds.md`
- [ ] `.agent/patterns.md`
- [ ] `.beads/` directory

---

## Phase 2: Beads Health

```bash
br --version
br prime
```

Check Beads is operational.

---

## Phase 3: Flow Consistency

For each flow in `.agent/prds.md`:

1. Verify directory exists: `.agent/specs/{flow_id}/`
2. Verify required files: spec.md, plan.md, metadata.json
3. Verify Beads epic exists
4. Check task count matches plan

---

## Phase 4: Plan Integrity

For each plan.md:
- Task IDs are sequential
- Status markers are valid: `[ ]`, `[~]`, `[x]`, `[!]`, `[-]`
- Checkpoint SHAs exist in git history

---

## Phase 5: Git Notes

Verify git notes exist for completed tasks.

---

## Phase 6: Report

```
Flow Validation Report

=== Structure ===
[x] .agent/ directory complete
[x] Beads initialized

=== Flows ===
[x] auth_20260124: 12 tasks, 5 complete
[!] dark-mode_20260124: Missing spec.md

=== Issues Found ===
1. dark-mode_20260124: Missing spec.md
2. auth_20260124: Task 3 marked complete but no commit SHA

=== Recommendations ===
- Run with --fix to auto-repair issues
- Manually review dark-mode_20260124
```

---

## Phase 7: Auto-Fix (if --fix)

If `--fix` argument provided:
- Create missing files from templates
- Sync Beads task counts
- Add missing index files

---

## Critical Rules

1. **NON-DESTRUCTIVE** - Only report by default
2. **FIX ON REQUEST** - Only modify with --fix flag
3. **COMPREHENSIVE** - Check everything
