---
description: Five-phase documentation workflow
---

# Flow Docs

Five-phase documentation workflow with validation, knowledge capture, and cleanup.

## Usage
`/flow-docs [validate|capture|archive|cleanup|full]`

## Phase 0: Setup Check

Verify Flow environment:

- **Product Definition** (`.agents/bundles/knowledge/product/product.md`)
- **Tech Stack** (`.agents/bundles/knowledge/product/tech-stack.md`)
- **Workflow** (`.agents/bundles/knowledge/workflow/workflow.md`)
- **Specs Directory** (`.agents/bundles/specs/` — flows are discovered by scanning spec frontmatter)

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

Scan all documentation — spec bundles (`.agents/bundles/specs/*/`), knowledge chapters (`.agents/bundles/knowledge/`), and research folders (`.agents/research/*/`).

For each document verify quality gates:

- **Structural:** Required sections present, no empty placeholders
- **Content:** No `[TODO]`, `[NEEDS CLARIFICATION]` tags
- **Consistency:** Terminology matches, references accurate
- **Currency:** Matches current codebase state

Consider invoking `flow:challenge` on documentation claims that restate code without explaining reasoning. Documentation should explain WHY decisions were made, not just WHAT the code does.

Generate a validation report with Critical/Warning issues and recommended actions.

## Mode B: Knowledge Capture

1. **Identify Knowledge Sources:** completed flows (spec frontmatter `state: completed`), git history, research documents.
2. Use `flow:docgen` for systematic documentation generation with progress tracking (`[3/12 files documented]`).
3. Update the knowledge chapters under `.agents/bundles/knowledge/` (patterns, technology decisions, lessons learned, recovery playbooks).
4. Identify recurring patterns (used in 2+ flows) and propose updates to `.agents/bundles/knowledge/patterns/`.

## Mode C: Archive

Identify archive candidates — completed flows (spec frontmatter `state: completed`) and old research (linked to completed flows or >30 days without a PRD).

For completed flows, prefer `/flow-archive {flow_id}` (synthesizes learnings into knowledge chapters, then deletes the spec bundle). For research, write an archive summary (key outcomes, artifacts, learnings, recovery info) before removal. Commit: `chore(flow): Archive [item_id]`.

## Mode D: Cleanup

1. **Identify Stale Artifacts:** orphaned research (>30 days without a flow), redundant/superseded specs, broken links.
2. **Report** the findings with recommendations.
3. **Execute Cleanup:**
   > "Found [X] items to clean up.
   > A) Clean all (with backup)
   > B) Clean only safe items
   > C) Review individually
   > D) Skip"

## Mode E: Full Cycle

Run Validation → Knowledge Capture → Re-Validation → Archive → Cleanup, then report documents validated, issues fixed, knowledge captured, flows archived, and artifacts cleaned.

## Critical Rules

1. **VALIDATE FIRST** - Always check quality before other operations
2. **BACKUP BEFORE DELETE** - Create backups when cleaning
3. **AUDIT TRAIL** - Commit all changes with clear messages
