
# Flow Docs

Five-phase documentation workflow with validation, knowledge capture, and cleanup.

## Contents

- [Setup and mode selection](#phase-0-setup-check)
- [Validation](#mode-a-validation)
- [Knowledge capture](#mode-b-knowledge-capture)
- [Archive and cleanup](#mode-c-archive)
- [Full cycle and rules](#mode-e-full-cycle)

## Usage

`flow-docs [validate|capture|archive|cleanup|full]`

## Phase 0: Setup Check

Verify Flow environment:

- **Product Definition** (`.agents/bundles/product/product.md`)
- **Tech Stack** (`.agents/bundles/product/tech-stack.md`)
- **Workflow** (`.agents/bundles/knowledge/workflow.md`)
- **Specs Directory** (`.agents/bundles/specs/` — flows are discovered by scanning spec frontmatter)

If ANY missing: "Flow not set up. Run `flow-setup` first." -> HALT

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

- Flow specs (`.agents/`)
- Flow folders (`.agents/bundles/specs/*/`)
- Research folders (`.agents/bundles/research/*/`)

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

1. **Completed Flows:** Read resident specs with `state: completed` and verify
   every task file is `closed` or `skipped`.
2. **Git History:** Analyze commits for context
3. **Research Documents:** Extract validated patterns

### Generate Knowledge Summary

Re-synthesize current-state guidance into the best matching chapter under
`.agents/bundles/knowledge/**/*.md`. Preserve project-shaped relative paths,
indexes, and links; never flatten the knowledge tree.

### Pattern Library Update

Identify recurring patterns (used in 2+ flows) and propose styleguide updates.

## Mode C: Archive

### Identify Archive Candidates

- Completed flows (`state: completed`)
- Old research (linked to completed flows or >30 days without flow)

### Execute Archive

1. Re-synthesize task notes and learnings into project-shaped knowledge.
2. Add one `.agents/bundles/log.md` entry with date, flow id, outcome, and final SHA.
3. Delete the reviewed completed spec directory; Git history is the archive.
4. Commit the tracked contraction locally without pushing or mutating Git tags.

## Mode D: Cleanup

### Identify Stale Artifacts

1. **Orphaned:** Research without flow (>30 days)
2. **Redundant:** Duplicate research, superseded specs
3. **Broken:** Links to deleted files

## Mode E: Full Cycle

Run all phases in sequence:

1. **Validation** - Fix critical issues
2. **Knowledge Capture** - Update knowledge base
3. **Re-Validation** - Verify consistency
4. **Archive** - Archive completed items
5. **Cleanup** - Remove stale artifacts

## Critical Rules

1. **VALIDATE FIRST** - Always check quality before other operations
2. **BACKUP BEFORE DELETE** - Create backups when cleaning
3. **AUDIT TRAIL** - Commit all changes with clear messages
