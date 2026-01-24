---
description: Sync context docs with current codebase state
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Refresh

Syncing Flow context with current codebase state.

## Phase 1: Detect Drift

Compare context files with actual codebase:

1. **Tech Stack** - Check if detected stack matches `.agent/tech-stack.md`
2. **Patterns** - Search for patterns not in `.agent/patterns.md`
3. **Files** - Check if referenced files still exist

---

## Phase 2: Update Tech Stack

Scan codebase for:
- New dependencies in package.json/pyproject.toml
- New frameworks detected
- Configuration changes

If drift detected:
```
Tech Stack Drift Detected:

Current:
- Framework: React 18

Detected:
- Framework: React 19 (upgraded)
- New: @tanstack/router

Update tech-stack.md? (yes/no)
```

---

## Phase 3: Pattern Discovery

Search for new patterns not yet documented:
- Common code structures
- Repeated patterns
- New conventions

---

## Phase 4: File Reference Validation

Check all file paths in:
- spec.md files
- plan.md files
- patterns.md

Mark broken references.

---

## Phase 5: Beads Sync

```bash
bd sync
bd prime
```

Ensure Beads is current with git.

---

## Phase 6: Save Refresh State

Create `.agent/refresh_state.json`:

```json
{
  "last_refresh": "timestamp",
  "drift_detected": true,
  "updates_made": [
    "tech-stack.md: Added React 19"
  ]
}
```

---

## Phase 7: Report

```
Context Refresh Complete

Files Updated:
- tech-stack.md (3 changes)
- patterns.md (1 new pattern)

Broken References Fixed: 2
Beads Synced: Yes

Recommendations:
- Review new patterns for accuracy
- Update track specs if affected
```

---

## Critical Rules

1. **DETECT DON'T ASSUME** - Verify before updating
2. **CONFIRM CHANGES** - Ask before modifying
3. **PRESERVE HISTORY** - Log all updates
