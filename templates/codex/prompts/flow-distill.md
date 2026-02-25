# Flow Distill

Extract reusable template from completed flow.

## Usage

```
/flow:distill <flow_id> <template_name>
```

## Workflow

### Phase 1: Validate Flow

Verify flow exists and is complete (archived or all tasks done).

### Phase 2: Analyze Structure

Identify:
- Patterns that could be templated
- Specific details that become placeholders
- Reusable task structure

### Phase 3: Create Template

Ask user about abstraction:
- Which parts should become {{placeholders}}
- Which parts stay specific

### Phase 4: Generate Template File

Create `.agent/templates/{template_name}.md`:

```markdown
# Template: {template_name}

**Source:** {flow_id}
**Created:** {date}

## Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| {{feature_name}} | Name of feature | user-auth |

## Spec Template

# {{feature_name}}

## Acceptance Criteria
- [ ] {{criteria_1}}

## Plan Template

### Phase 1: Setup
- [ ] 1. Create {{model_name}} model

## Learnings from Source

{Preserved learnings}
```

## Critical Rules

1. **ABSTRACT PROPERLY** - Use meaningful placeholders
2. **PRESERVE LEARNINGS** - Include gotchas and tips
