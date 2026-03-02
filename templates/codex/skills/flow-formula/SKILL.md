---
name: flow-formula
description: "List and manage flow templates"
---

# Flow Formula

List and manage flow templates.

## Usage

```
$flow:formula [list|pour|distill] [template_name]
```

## Commands

### List Templates

```bash
$flow:formula list
```

Lists templates from:
- Local: `.agent/templates/`

### Pour Template

```bash
$flow:formula pour {template_name}
```

Creates a flow from a template.

### Distill Template

```bash
$flow:formula distill {flow_id} {template_name}
```

Extracts a template from an existing flow.

## List Action

Scan `.agent/templates/` directory and display available templates with descriptions.

## Pour Action

1. Read `.agent/templates/{template_name}.md`
2. Customize placeholders and create Beads tasks

## Distill Action

1. Read flow's spec.md
2. Abstract into template with placeholders
3. Save to `.agent/templates/{name}.md`

## Critical Rules

1. **FILE-BASED** - Templates stored in `.agent/templates/`
2. **ABSTRACT PROPERLY** - Use placeholders
