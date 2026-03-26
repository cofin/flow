
# Flow Validate

Validate project integrity and fix issues.

## Usage

`flow-validate`

## Phase 1: Structure Validation

### 1.1 Required Files

Check existence of:

- `.agents/product.md`
- `.agents/tech-stack.md`
- `.agents/workflow.md`
- `.agents/patterns.md`
- `.agents/flows.md`
- `.agents/beads.json`

### 1.2 Flow Directories

For each flow in `.agents/flows.md`:

- Verify `.agents/specs/{flow_id}/` exists
- Check for `spec.md`, `metadata.json`

## Phase 2: Beads Validation

```bash
br status
```

### 2.1 Epic Sync

Verify each flow has corresponding Beads epic.

### 2.2 Task Sync

Check spec.md status matches Beads status.

## Phase 3: Content Validation

### 3.1 Plan Tasks

For each spec.md:

- All tasks have valid status markers
- File references exist
- No orphaned tasks

### 3.2 Patterns

For each pattern in patterns.md:

- Referenced files exist
- Code examples still valid

## Phase 4: Git State

```bash
git status
```

- Check for uncommitted changes
- Verify no conflicts

## Phase 5: Verification Gate

```
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Every validation check must produce evidence, not assertions:

| Check | Evidence Required | Not Sufficient |
|-------|-------------------|----------------|
| Structure OK | File existence confirmed | Assumed from last run |
| Beads synced | `br status` output matches flows.md | "Should be synced" |
| Patterns valid | File refs verified on disk | Previous check |
| Git clean | `git status` output shown | Assumed clean |

Run each check fresh. Read output. Report actual results.

## Phase 6: Report & Fix

```text
Validation Results

- Structure: OK (verified: {N} files checked)
- Beads: Synced (verified: {N} epics matched)
- Patterns: 2 stale references (verified: {N} refs checked)
- Git: Clean (verified: git status output)

Issues Found:
1. patterns.md:45 - File 'src/old.ts' not found
2. auth_20260124/spec.md - Task status mismatch with Beads

Auto-fix available for 2 issues. Apply? [Y/n]
```

### Auto-Fix Options

- Remove stale pattern references
- Sync task status with Beads
- Recreate missing metadata.json
