
# Flow Research

Conduct pre-PRD research including codebase analysis and documentation lookup.

## Usage

```text
flow-research <topic>
```

## Workflow

### Phase 1: Research Initialization

1. **Define Topic:** Use provided argument or ask user
2. **Classify Type:** New Feature, Bug Investigation, Integration, Refactoring, Performance

### Phase 2: Codebase Exploration

1. Map relevant modules and files
2. Identify existing patterns
3. Analyze dependencies

### Phase 3: External Documentation

1. Lookup relevant library documentation
2. Note APIs, best practices, gotchas

### Phase 4: Prior Art

1. Check git history for similar work
2. Research external patterns

### Phase 5: Risk Assessment

1. Identify technical risks
2. Plan recovery strategy

### Phase 6: Create Research Document

Research ids follow flow identity: `<slug>_<YYYYMMDD>`, lowercase, no `research_`
prefix (the directory already says that). Create
`.agents/bundles/research/<research_id>/research.md` as a valid OKF v0.2
document with frontmatter:

```yaml
---
type: Research
research_id: <research_id>
title: <research_title>
state: open          # open | promoted
created_at: <ISO timestamp>
updated_at: <ISO timestamp>
description: <one-line summary>
tags: [<work-kind>, <domain>, ...]
promoted_to: null
---
```

Populate every field — one Work Kind plus 1–4 domain tags per
[OKF tagging](../../okf/references/frontmatter-and-tagging.md), never `[]`.

Body sections:

- Executive Summary
- Codebase Analysis
- Library Documentation
- Prior Art
- Risk Assessment
- Recommended Approach

## Promotion Contract

`bundles/research/` holds **un-promoted research only**. When a PRD or plan
adopts research, it becomes part of that flow's bundle:

1. **Ensure a destination flow.** If none exists, derive `<flow_id>` as
   `<slug>_<YYYYMMDD>` from the research title, create
   `bundles/specs/<flow_id>/spec.md` with `state: planned` seeded from the
   research summary and recommended approach, and confirm the id.
2. **Move, never copy** the directory to
   `bundles/specs/<flow_id>/research/` — `git mv` when tracked.
3. **Update frontmatter:** `state: promoted`, `promoted_to: <flow_id>`, refresh
   `updated_at`. Add `research: [<research_id>]` to the spec.
4. **Repair links** that pointed at the old path, and
   `bundles/research/index.md`.
5. **One owner per document.** If two flows need it, the durable content belongs
   in a `knowledge/` chapter instead.

Promoted research archives with its flow (see [Archive](archive.md)).

## Critical Rules

1. **THOROUGH EXPLORATION** - Analyze codebase before external research
2. **ACTIONABLE OUTPUT** - Research should inform PRD creation
3. **RESEARCH IS UN-PROMOTED ONLY** - `bundles/research/` never holds research
   that already belongs to a flow
4. **MOVE ON PROMOTION** - Promotion relocates the directory; it never copies
