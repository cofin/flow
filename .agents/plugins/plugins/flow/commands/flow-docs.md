---
description: Five-phase documentation workflow
argument-hint: [validate|capture|archive|cleanup|full]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Flow Docs

> Lifecycle skill: use `flow-completion` through the `flow` router.

Managing documentation for Flow project.

## Phase 0: Setup Check

Using the **Universal File Resolution Protocol**, verify:

- **Product Definition** (`.agents/product.md`)
- **Tech Stack** (`.agents/tech-stack.md`)
- **Workflow** (`.agents/workflow.md`)
- **PRD Registry** (`.agents/flows.md`)

If ANY missing: "Flow not set up. Run `/flow-setup` first." → HALT

---

## Phase 1: Mode Selection

**If `$ARGUMENTS` provided:** Use specified mode.

**If empty:** Present options:
> "What documentation task would you like to perform?
>
> A) **Validate** - Run quality gates on all documentation
> B) **Capture** - Extract knowledge from completed PRDs
> C) **Archive** - Move completed items to archive with summary
> D) **Cleanup** - Remove stale artifacts and organize workspace
> E) **Full Cycle** - Run all phases in sequence"

---

## Mode A: Validation

### Scan Documentation

Identify all docs:

- Flow specs (`.agents/`)
- PRD folders (`.agents/specs/*/`)
- Research folders (`.agents/research/*/`)

### Quality Gate Checks

For each document verify:

- **Structural:** Required sections present, no empty placeholders
- **Content:** No `[TODO]`, `[NEEDS CLARIFICATION]` tags
- **Consistency:** Terminology matches, references accurate
- **Currency:** Matches current codebase state

### Documentation Quality

Consider invoking `flow:challenge` on documentation claims that restate code without explaining reasoning. Documentation should explain WHY decisions were made, not just WHAT the code does.

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

---

## Mode B: Knowledge Capture

### Identify Knowledge Sources

1. **Completed PRDs:** Scan for PRDs marked `[x]`
2. **Git History:** Analyze commits for context
3. **Research Documents:** Extract validated patterns

### Documentation Generation

Use `flow:docgen` for systematic documentation generation. Follow its file-by-file analysis workflow with progress tracking (`[3/12 files documented]`) to ensure complete coverage. Use its component template for structured per-component documentation.

### Generate Knowledge Summary

Create/update `.agents/knowledge-base.md`:

```markdown
# Project Knowledge Base
Last Updated: [timestamp]

## Patterns & Best Practices
[From completed PRDs]

## Technology Decisions
| Technology | Reason | PRD Reference |
|------------|--------|---------------|

## Lessons Learned
### What Worked Well
### What Could Be Improved

## Recovery Playbooks
[Compiled recovery strategies]
```

### Pattern Library Update

Identify recurring patterns (used in 2+ PRDs) and propose styleguide updates.

---

## Mode C: Archive

### Identify Archive Candidates

- Completed PRDs (status `[x]`)
- Old research (linked to completed PRDs or >30 days without PRD)

### Generate Archive Summary

For each item, create `archive-summary.md`:

```markdown
# Archive Summary: [item_id]
Archived: [timestamp]

## Key Outcomes
- [Outcome]

## Artifacts Included
- spec.md, knowledge.md

## Key Learnings
[From knowledge.md]

## Recovery Information
**To restore:** Copy from archive to active, update registry
```

### Execute Archive

1. Move to `.agents/archive/`
2. Remove from PRD registry
3. Add to archive index
4. Commit: `chore(flow): Archive [item_id]`

---

## Mode D: Cleanup

### Identify Stale Artifacts

1. **Orphaned:** Research without PRD (>30 days)
2. **Redundant:** Duplicate research, superseded specs
3. **Broken:** Links to deleted files

### Cleanup Report

```markdown
# Cleanup Report
Generated: [timestamp]

## Stale Artifacts Found
| Item | Type | Age | Recommendation |
|------|------|-----|----------------|

## Disk Space Recovery
Potential savings: [size]
```

### Execute Cleanup

> "Found [X] items to clean up.
> A) Clean all (with backup)
> B) Clean only safe items
> C) Review individually
> D) Skip"

---

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
- PRDs Archived: [count]
- Artifacts Cleaned: [count]

## Project Health
- Documentation Score: [%]
- Knowledge Coverage: [%]
```

---

## Critical Rules

1. **VALIDATE FIRST** - Always check quality before other operations
2. **BACKUP BEFORE DELETE** - Create backups when cleaning
3. **AUDIT TRAIL** - Commit all changes with clear messages
