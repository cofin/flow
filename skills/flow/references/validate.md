
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

## Phase 5: Report & Fix

```
Validation Results

- Structure: OK
- Beads: Synced
- Patterns: 2 stale references
- Git: Clean

Issues Found:
1. patterns.md:45 - File 'src/old.ts' not found
2. auth_20260124/spec.md - Task status mismatch with Beads

Auto-fix available for 2 issues. Apply? [Y/n]
```

### Auto-Fix Options
- Remove stale pattern references
- Sync task status with Beads
- Recreate missing metadata.json
