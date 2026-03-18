---
description: Generate project summary export
argument-hint: [--format markdown|json]
allowed-tools: Read, Glob, Grep, Bash, Write
---

# Flow Export

Generating project summary export.

## Phase 1: Gather Data

Collect:
- All flows from `.agents/flows.md`
- All patterns from `.agents/patterns.md`
- Flow details from `.agents/specs/*/`
- Archive details from `.agents/archive/*/`

---

## Phase 2: Generate Report

### Markdown Format (default)

```markdown
# Flow Project Export

**Generated:** {date}
**Project:** {from product.md}

## Overview

- Active Flows: {count}
- Archived Flows: {count}
- Total Tasks: {count}
- Completion Rate: {%}

## Active Flows

### {flow_id}

**Status:** In Progress
**Progress:** {completed}/{total} tasks
**Created:** {date}

Description: {from spec.md}

## Archived Flows

### {flow_id}

**Completed:** {date}
**Duration:** {days}
**Tasks:** {count}

Patterns Extracted: {count}

## Project Patterns

{contents of patterns.md}

## Statistics

- Total Commits: {count}
- Lines of Code Added: {estimate}
- Test Coverage: {%}
```

### JSON Format (--format json)

```json
{
  "generated": "ISO date",
  "project": "name",
  "flows": {
    "active": [...],
    "archived": [...]
  },
  "patterns": [...],
  "statistics": {...}
}
```

---

## Phase 3: Output

Write to `.agents/export_{date}.{md|json}`

---

## Critical Rules

1. **COMPREHENSIVE** - Include all relevant data
2. **FORMAT OPTION** - Support markdown and JSON
3. **NO SECRETS** - Exclude any sensitive data
