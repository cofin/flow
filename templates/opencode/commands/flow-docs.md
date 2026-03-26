---
description: Five-phase documentation workflow
---

# Flow Docs

Five-phase documentation workflow with validation, knowledge capture, and cleanup.

## Usage
`/flow-docs [validate|capture|archive|cleanup|full]`

## Phase 0: Setup Check

Verify Flow environment:
- **Product Definition** (`.agents/product.md`)
- **Tech Stack** (`.agents/tech-stack.md`)
- **Workflow** (`.agents/workflow.md`)
- **Flow Registry** (`.agents/flows.md`)

If ANY missing: "Flow not set up. Run `/flow-setup` first." → HALT

## Phase 1: Mode Selection

**If arguments provided:** Use specified mode.

**If empty:** Present options:
> A) **Validate** - Run quality gates on all documentation
> B) **Capture** - Extract knowledge from completed flows
> C) **Archive** - Move completed items to archive with summary
> D) **Cleanup** - Remove stale artifacts and organize workspace
> E) **Full Cycle** - Run all phases in sequence

## Mode A: Validation

Scan all documentation, verify quality gates (structural, content, consistency, currency).

## Mode B: Knowledge Capture

Extract knowledge from completed flows, update `.agents/knowledge-base.md`.

## Mode C: Archive

Archive completed flows to `.agents/archive/`, update registry.

## Mode D: Cleanup

Remove orphaned research, redundant specs, broken links.

## Mode E: Full Cycle

Run Validation → Knowledge Capture → Re-Validation → Archive → Cleanup.

## Critical Rules

1. **VALIDATE FIRST** - Always check quality before other operations
2. **BACKUP BEFORE DELETE** - Create backups when cleaning
3. **AUDIT TRAIL** - Commit all changes with clear messages
