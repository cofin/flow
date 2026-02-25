# Flow Docs

Five-phase documentation workflow with validation, knowledge capture, and cleanup.

## Usage

`/flow:docs [validate|capture|archive|cleanup|full]`

## Phase 0: Setup Check

Verify Flow environment:
- **Product Definition** (`.agent/product.md`)
- **Tech Stack** (`.agent/tech-stack.md`)
- **Workflow** (`.agent/workflow.md`)
- **Flow Registry** (`.agent/flows.md`)

If ANY missing: "Flow not set up. Run `/flow:setup` first." → HALT

## Phase 1: Mode Selection

**If arguments provided:** Use specified mode.

**If empty:** Present options:
> "What documentation task would you like to perform?
>
> A) **Validate** - Run quality gates on all documentation
> B) **Capture** - Extract knowledge from completed flows
> C) **Archive** - Move completed items to archive with summary
> D) **Cleanup** - Remove stale artifacts and organize workspace
> E) **Full Cycle** - Run all phases in sequence"

## Mode A: Validation

### Scan Documentation

Identify all docs:
- Flow specs (`.agent/`)
- Flow folders (`.agent/specs/*/`)
- Research folders (`.agent/research/*/`)

### Quality Gate Checks

For each document verify:
- **Structural:** Required sections present, no empty placeholders
- **Content:** No `[TODO]`, `[NEEDS CLARIFICATION]` tags
- **Consistency:** Terminology matches, references accurate
- **Currency:** Matches current codebase state

### Generate Validation Report

```markdown
# Documentation Validation Report
Generated: [timestamp]

## Summary
- Total Documents: [count]
- Passed: [count]
- Needs Attention: [count]

## Issues Found
### Critical (Must Fix)
- [document]: [issue]

### Warnings (Should Fix)
- [document]: [issue]

## Recommended Actions
1. [Action]
```

## Mode B: Knowledge Capture

### Identify Knowledge Sources

1. **Completed Flows:** Scan for flows marked `[x]`
2. **Git History:** Analyze commits for context
3. **Research Documents:** Extract validated patterns

### Generate Knowledge Summary

Create/update `.agent/knowledge-base.md`:

```markdown
# Project Knowledge Base
Last Updated: [timestamp]

## Patterns & Best Practices
[From completed flows]

## Technology Decisions
| Technology | Reason | Flow Reference |
|------------|--------|----------------|

## Lessons Learned
### What Worked Well
### What Could Be Improved
```

### Pattern Library Update

Identify recurring patterns (used in 2+ flows) and propose styleguide updates.

## Mode C: Archive

### Identify Archive Candidates

- Completed flows (status `[x]`)
- Old research (linked to completed flows or >30 days without flow)

### Generate Archive Summary

For each item, create `archive-summary.md`:

```markdown
# Archive Summary: [item_id]
Archived: [timestamp]

## Key Outcomes
- [Outcome]

## Artifacts Included
- spec.md, learnings.md

## Key Learnings
[From learnings.md]

## Recovery Information
**To restore:** Copy from archive to active, update registry
```

### Execute Archive

1. Move to `.agent/archive/`
2. Remove from flow registry
3. Add to archive index
4. Commit: `chore(flow): Archive [item_id]`

## Mode D: Cleanup

### Identify Stale Artifacts

1. **Orphaned:** Research without flow (>30 days)
2. **Redundant:** Duplicate research, superseded specs
3. **Broken:** Links to deleted files

### Execute Cleanup

> "Found [X] items to clean up.
> A) Clean all (with backup)
> B) Clean only safe items
> C) Review individually
> D) Skip"

## Mode E: Full Cycle

Run all phases in sequence:

1. **Validation** - Fix critical issues
2. **Knowledge Capture** - Update knowledge base
3. **Re-Validation** - Verify consistency
4. **Archive** - Archive completed items
5. **Cleanup** - Remove stale artifacts

### Final Report

```markdown
# Documentation Cycle Complete
Generated: [timestamp]

## Summary
- Documents Validated: [count]
- Issues Fixed: [count]
- Knowledge Items Captured: [count]
- Flows Archived: [count]
- Artifacts Cleaned: [count]

## Project Health
- Documentation Score: [%]
- Knowledge Coverage: [%]
```

## Critical Rules

1. **VALIDATE FIRST** - Always check quality before other operations
2. **BACKUP BEFORE DELETE** - Create backups when cleaning
3. **AUDIT TRAIL** - Commit all changes with clear messages
