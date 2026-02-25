# Flow Formula

List and manage flow templates (Beads formulas).

## Usage

```
/flow:formula [list|pour|distill] [template_name]
```

## Commands

### List Templates

```bash
/flow:formula list
```

Lists templates from:
- Local: `.agent/templates/`
- Beads: `br mol list`

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

```bash
br mol list
```

Display available templates with usage counts.

## Pour Action

```bash
br mol pour {template_name}
```

Then customize placeholders and create Beads tasks.

## Distill Action

1. Read flow's spec.md and plan.md
2. Abstract into template with placeholders
3. Save to `.agent/templates/{name}.md`
4. Register: `br mol distill {epic_id} {template_name}`

## Critical Rules

1. **BEADS INTEGRATION** - Use br mol commands
2. **ABSTRACT PROPERLY** - Use placeholders
