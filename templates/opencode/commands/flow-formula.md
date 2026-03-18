---
description: List and manage flow templates
agent: flow
---

# Flow Formula

Managing flow templates (formulas).

## Commands

### List Templates

```bash
/flow:formula list
```

Lists templates from `.agents/templates/`.

### Pour Template

```bash
/flow:formula pour {template_name}
```

Creates a flow from a template.

### Distill Template

```bash
/flow:formula distill {flow_id} {template_name}
```

Extracts a template from an existing flow.

## List Action

Scan `.agents/templates/` directory and display available templates with descriptions.

## Pour Action

1. Read `.agents/templates/{template_name}.md`
2. Prompt user to fill in placeholders
3. Generate spec.md from template
4. Create Beads tasks under new epic

## Distill Action

1. Read flow's spec.md
2. Abstract into template with placeholders
3. Save to `.agents/templates/{name}.md`

## Critical Rules

1. **FILE-BASED** - Templates stored in `.agents/templates/`
2. **ABSTRACT PROPERLY** - Use placeholders
