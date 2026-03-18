---
description: Validate project integrity and fix issues
---

# Flow Validate

Validate project integrity and fix issues.

## Phase 1: Structure Validation

Check required files:
- `.agents/product.md`
- `.agents/tech-stack.md`
- `.agents/workflow.md`
- `.agents/patterns.md`
- `.agents/flows.md`

## Phase 2: Beads Validation

```bash
br status
```

Verify flow/epic sync.

## Phase 3: Content Validation

- Verify spec.md task status markers
- Check file references exist
- Validate patterns are current

## Phase 4: Report & Fix

```
Validation Results

✓ Structure: OK
✓ Beads: Synced
⚠ Patterns: {N} stale references

Auto-fix available. Apply? [Y/n]
```
