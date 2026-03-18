---
description: List and manage flow templates
argument-hint: [list|pour|distill] [template_name]
allowed-tools: Read, Write, Glob, Bash
---

# Flow Formula

Managing flow templates (formulas).

## Commands

### List Templates

```bash
/flow-formula list
```

Lists available templates from:
- Local: `.agents/templates/`

### Pour Template

```bash
/flow-formula pour {template_name}
```

Creates a PRD from a template.

### Distill Template

```bash
/flow-formula distill {flow_id} {template_name}
```

Extracts a reusable template from an existing flow.

---

## Phase 1: Parse Command

Determine action: `list`, `pour`, or `distill`

---

## Phase 2: List Action

```bash
ls .agents/templates/*.md
```

Display:
```
Available Templates

=== Local Templates ===

.agents/templates/api-endpoint.md
.agents/templates/frontend-component.md
```

---

## Phase 3: Pour Action

1. Read template file: `.agents/templates/{template_name}.md`
2. Parse placeholders (e.g., `{{feature_name}}`, `{{model_name}}`)
3. Ask user to fill in each placeholder
4. Generate flow_id
5. Replace template placeholders with user values
6. Create Beads epic and tasks
7. Register in flows.md

---

## Phase 4: Distill Action

1. Read flow's spec.md
2. Abstract into template:
   - Replace specific names with placeholders
   - Generalize tasks
   - Keep learnings as guidance

3. Save to `.agents/templates/{name}.md`
4. Verify template is valid and complete

---

## Template Format

```markdown
# Template: {name}

**Description:** {what this template is for}
**Use When:** {when to use this template}

## Default Spec

{template spec with {{placeholders}}}

## Default Plan

## Phase 1: Setup
- [ ] 1. {{setup_task}}

## Phase 2: Core
- [ ] 2. {{core_task_1}}
- [ ] 3. {{core_task_2}}

## Phase 3: Testing
- [ ] 4. Write unit tests
- [ ] 5. Write integration tests

## Guidance

{Tips and patterns for this type of work}
```

---

## Critical Rules

1. **FILE-BASED** - Templates stored in .agents/templates/
2. **ABSTRACT PROPERLY** - Use placeholders
3. **PRESERVE GUIDANCE** - Include learnings
