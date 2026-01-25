# Flow PRD

Create a new track with specification and implementation plan.

## Phase 1: Validate Environment

Check for `.agent/` directory. If missing: "Run `/flow:setup` first." → HALT

## Phase 2: Gather Track Information

### 2.1 Track Description
User provides: description of what to build

### 2.2 Generate Track ID
Format: `shortname_YYYYMMDD`
Example: `user-auth_20260124`

## Phase 3: Research Phase

Before writing spec:
1. Search codebase for related code
2. Read `.agent/patterns.md` for relevant patterns
3. Identify affected files

## Phase 4: Create Spec

Create `.agent/specs/{track_id}/spec.md`:

```markdown
# {Track Title}

## Overview
{Brief description}

## Problem Statement
{What problem does this solve}

## Requirements
### Functional
- [ ] Requirement 1
- [ ] Requirement 2

### Non-Functional
- [ ] Performance targets
- [ ] Security requirements

## Affected Files
- `src/file1.ts` - {reason}
```

## Phase 5: Create Plan

Create `.agent/specs/{track_id}/plan.md`:

```markdown
# Implementation Plan: {track_id}

## Phase 1: {Phase Name}

- [ ] Task 1.1: {Description}
  - Files: `src/file.ts`
  - Tests: `tests/file.test.ts`
```

## Phase 6: Create Beads Epic

```bash
bd create "Track: {track_id}" -t epic -p 1
bd create "{task_description}" --parent {epic_id} -p 1
```

## Phase 7: Register Track

Add to `.agent/tracks.md`:
```markdown
## Active

- [ ] `{track_id}` - {description} (epic: {epic_id})
```

## Final Output

```
Track Created: {track_id}

Spec: .agent/specs/{track_id}/spec.md
Plan: .agent/specs/{track_id}/plan.md

Next: Run `/flow:implement {track_id}` to start
```
