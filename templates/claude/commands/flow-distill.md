---
description: Extract reusable template from completed track
argument-hint: <track_id> <template_name>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Flow Distill

Extracting template from: **$ARGUMENTS**

## Phase 1: Validate Track

1. Verify track exists and is complete (archived or all tasks done)
2. Read spec.md, plan.md, learnings.md

---

## Phase 2: Analyze Structure

Identify:
- Common patterns that could be templated
- Specific details that should become placeholders
- Task structure that's reusable

---

## Phase 3: Create Template

Ask user about abstraction:

> **What should be templated?**
>
> For each section, choose: Template or Specific
>
> - Task 1: Create model -> Template as "Create {{model_name}} model"
> - Task 2: Add auth middleware -> Specific (keep as-is)

---

## Phase 4: Generate Template File

Create `.agent/templates/{template_name}.md`:

```markdown
# Template: {template_name}

**Source:** {track_id}
**Created:** {date}
**Description:** {user description}

## When to Use

{Guidance on when this template applies}

## Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| {{feature_name}} | Name of the feature | user-auth |
| {{model_name}} | Primary model | User |

## Spec Template

# {{feature_name}}

## Problem Statement

{{problem_description}}

## Acceptance Criteria

- [ ] {{criteria_1}}
- [ ] {{criteria_2}}

## Plan Template

### Phase 1: Setup

- [ ] 1. Create {{model_name}} model
- [ ] 2. Add migrations

### Phase 2: Core

- [ ] 3. Implement {{feature_name}} service
- [ ] 4. Add API endpoints

### Phase 3: Testing

- [ ] 5. Write unit tests for {{model_name}}
- [ ] 6. Write integration tests

## Learnings from Source

{Preserved learnings that apply to this pattern}

## Anti-Patterns

{Things to avoid, learned from source track}
```

---

## Phase 5: Register with Beads

```bash
bd mol distill {epic_id} {template_name}
```

---

## Phase 6: Commit Template

```bash
git add .agent/templates/{template_name}.md
git commit -m "flow(template): Add {template_name} from {track_id}"
```

---

## Final Summary

```
Template Extracted

Name: {template_name}
Source: {track_id}
Location: .agent/templates/{template_name}.md

Placeholders: {count}
Tasks: {count}

To use this template:
/flow-formula pour {template_name}
```

---

## Critical Rules

1. **ABSTRACT PROPERLY** - Use meaningful placeholders
2. **PRESERVE LEARNINGS** - Include gotchas and tips
3. **BEADS SYNC** - Register with bd mol
