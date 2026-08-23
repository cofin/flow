# Flow Research

Conduct technical research across codebases, SDK documentation, and specifications using automated parallel subagent fan-out.

## Parallel Fan-Out Research Protocol

When investigating a broad topic, API, or system architecture:

1. **Decompose Topic**: Partition the inquiry into 3 to 5 disjoint, orthogonal sub-topics (e.g. Data Model, Security & Auth, External API Contracts, Performance).
2. **Spawn Concurrent Subagents**: Dispatch parallel `@researcher` subagents with isolated briefs (Topic, Scoped Primary Sources, Output Target).
3. **Primary Source Mandate**: Subagents inspect codebase source files, official library documentation, and specifications in isolated context windows.
4. **Structured Note Capture**:
   - Write notes to `.agents/bundles/research/<topic>/<slug>.md` or `.agents/bundles/specs/<flow_id>/research/<slug>.md`.
   - Every note must include exact citations and an explicit `## Gaps` section.
5. **Parent Synthesis**: The parent orchestrator reads only the distilled research notes, keeping its context window clean for planning.

## Frontmatter Schema

```yaml
---
type: Research
research_id: "topic-slug"
title: Research Title
scope: architecture | domain | integration
tags: [tag1, tag2]
status: stable
state: open                     # open | promoted
promoted_to: null               # flow_id once adopted by a spec
created_at: 2026-08-23T12:00:00Z
updated_at: 2026-08-23T12:00:00Z
---
```

## Promotion Contract

Un-promoted research lives in `.agents/bundles/research/<topic>/`. When a flow adopts the research, move the folder to `.agents/bundles/specs/<flow_id>/research/` and set `state: promoted` and `promoted_to: <flow_id>`.
