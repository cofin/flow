---
name: apilookup
description: "Auto-activate when looking up API documentation, SDK references, library versions, breaking changes, migration guides, changelogs, or release notes. Use when: checking latest versions, finding official docs, researching deprecations, or comparing API changes between versions."
---

# API Lookup Skill

Look up API documentation, SDK references, library versions, and migration guides using a three-tier resolution strategy that starts with local Flow skill references and escalates to targeted web searches only when needed.

## Overview

Three tiers of resolution, applied in order:

1. **Local skill references** — if a matching Flow skill exists and the registry entry is fresh (< 30 days), load the skill's curated `references/` docs directly. No network needed.
2. **Targeted web lookup** — if local refs are stale (> 30 days) or the query needs more, use the registry's known URLs for targeted searches (max 2-4).
3. **Arbitrary lookup** — for technologies without a matching skill, broad web search with a version-first strategy (max 2-4 searches).

## Usage Patterns

Example queries this skill handles:

- "What's the latest Litestar version and what changed?"
- "How do I use React Server Components?"
- "Show me the SQLAlchemy 2.0 migration guide"
- "What breaking changes are in Angular 19?"
- "What's the current Go module proxy API?" (arbitrary — no local skill)
- "Check if there's a newer version of Tailwind CSS"

## How It Works

### Version Registry

`references/registry.json` maps every Flow skill to:

- Current known version and last-checked date
- Package registry (PyPI, npm, crates.io, etc.)
- Official docs URL, changelog URL, and GitHub repo
- Search hint keywords for targeted queries

### Staleness Thresholds

| Age of registry entry | Action |
|-----------------------|--------|
| < 30 days | Trust local skill references, answer directly |
| 30-90 days | Use local refs as baseline, verify version via web |
| > 90 days | Treat as potentially outdated, do full version check |

### Search Budget

All web lookups are capped at **2-4 searches max**. Prefer `WebFetch` on known URLs over `WebSearch` when registry URLs are available — it is faster and more precise.

## Lookup Rules

See `references/lookup-strategy.md` for the full decision tree. Key principles:

1. **Always start local** — check the registry and load matching skill refs if fresh
2. **Be targeted** — use registry URLs and package names for precise queries
3. **Respect the budget** — 2-4 searches max, stop once you have an authoritative answer
4. **Cite sources** — always include links to official docs or changelogs
5. **Note version gaps** — if local refs cover version X but the current release is Y, tell the user explicitly

## References Index

- **[Lookup Strategy](references/lookup-strategy.md)** — Detailed three-tier resolution instructions
- **[Version Registry](references/registry.json)** — Package metadata and staleness tracking for all skills
- **[Registry Schema](references/registry-schema.md)** — Documents the registry JSON format and fields
