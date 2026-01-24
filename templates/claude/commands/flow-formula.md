---
description: List and manage track templates (Beads formulas)
argument-hint: [list|pour|distill] [template_name]
allowed-tools: Read, Write, Glob, Bash
---

# Flow Formula

Managing Beads track templates (formulas).

## Commands

### List Templates

```bash
/flow-formula list
```

Lists available templates from:
- Local: `.agent/templates/`
- Beads: `bd mol list`

### Pour Template

```bash
/flow-formula pour {template_name}
```

Creates a new track from a template.

### Distill Template

```bash
/flow-formula distill {track_id} {template_name}
```

Extracts a reusable template from an existing track.

---

## Phase 1: Parse Command

Determine action: `list`, `pour`, or `distill`

---

## Phase 2: List Action

```bash
bd mol list
```

Display:
```
Available Templates

=== Beads Molecules ===

feature-crud
  Description: Standard CRUD feature template
  Tasks: 8
  Used: 15 times

bugfix-standard
  Description: Standard bug fix template
  Tasks: 4
  Used: 32 times

=== Local Templates ===

.agent/templates/api-endpoint.md
.agent/templates/frontend-component.md
```

---

## Phase 3: Pour Action

```bash
bd mol pour {template_name}
```

Then customize:
1. Generate track_id
2. Replace template placeholders
3. Create Beads epic and tasks
4. Register in prds.md

---

## Phase 4: Distill Action

1. Read track's spec.md and plan.md
2. Abstract into template:
   - Replace specific names with placeholders
   - Generalize tasks
   - Keep learnings as guidance

3. Save to `.agent/templates/{name}.md`
4. Register with Beads:
   ```bash
   bd mol distill {epic_id} {template_name}
   ```

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

1. **BEADS INTEGRATION** - Use bd mol commands
2. **ABSTRACT PROPERLY** - Use placeholders
3. **PRESERVE GUIDANCE** - Include learnings
