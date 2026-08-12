---
description: Conduct pre-PRD research
agent: flow
---

# Flow Research

Conducting research for: $ARGUMENTS

## Phase 0: Setup Check

Verify Flow environment:

- **Product Definition** (`.agents/bundles/knowledge/product/product.md`)
- **Tech Stack** (`.agents/bundles/knowledge/product/tech-stack.md`)
- **Workflow** (`.agents/bundles/knowledge/workflow/workflow.md`)

If ANY missing: "Flow not set up. Run `/flow-setup` first." → HALT

## Phase 1: Research Initialization

1. **Define Topic:** Use provided argument or ask user
2. **Classify Type:** New Feature, Bug Investigation, Integration, Refactoring, Performance

## Phase 2: Codebase Exploration

1. Map relevant modules and files (always include `file:line` references)
2. Identify existing patterns
3. Analyze dependencies

## Phase 3: External Documentation

1. Lookup relevant library documentation (use `flow:apilookup` when available)
2. Note APIs, best practices, gotchas

## Phase 4: Prior Art

1. Check git history for similar work
2. Research external patterns

## Phase 5: Risk Assessment

1. Identify technical risks
2. Plan recovery strategy

## Phase 6: Create Research Document

Create `.agents/research/{research_id}/research.md` with YAML frontmatter (no separate metadata file):

```yaml
---
type: Research
research_id: {research_id}
title: {topic}
created_at: ISO timestamp
libraries_researched: [lib1, lib2]
files_analyzed: [path1, path2]
linked_prd: null
linked_flow: null
---
```

Body sections:

- Executive Summary
- Codebase Analysis (with `file:line` references)
- Library Documentation
- Prior Art
- Risk Assessment
- Recommended Approach
- Research Outputs (this research informs the roadmap spec at `.agents/bundles/specs/{prd_id}/spec.md` and the flow bundle at `.agents/bundles/specs/{flow_id}/`, when created)

## Critical Rules

1. **THOROUGH EXPLORATION** - Analyze codebase before external research
2. **RISK FOCUSED** - Always include recovery planning
3. **ACTIONABLE OUTPUT** - Research should inform PRD creation (`/flow-prd`)
