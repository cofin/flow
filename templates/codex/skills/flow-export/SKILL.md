---
name: flow-export
description: "Generate project summary export"
---

# Flow Export

Generate project summary export.

## Usage

```
$flow:export [--format markdown|json]
```

## Workflow

### Phase 1: Gather Data

Collect:
- All flows from `.agents/flows.md`
- All patterns from `.agents/patterns.md`
- Flow details from `.agents/specs/*/`
- Archive details from `.agents/archive/*/`

### Phase 2: Generate Report

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

## Archived Flows

### {flow_id}
**Completed:** {date}
**Tasks:** {count}

## Project Patterns

{contents of patterns.md}
```

### Phase 3: Output

Write to `.agents/export_{date}.md`

## Critical Rules

1. **COMPREHENSIVE** - Include all relevant data
2. **NO SECRETS** - Exclude sensitive data
