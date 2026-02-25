# Flow Validate

Validate project integrity and fix issues.

## Phase 1: Structure Validation

Check required files:
- `.agent/product.md`
- `.agent/tech-stack.md`
- `.agent/workflow.md`
- `.agent/patterns.md`
- `.agent/flows.md`

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
