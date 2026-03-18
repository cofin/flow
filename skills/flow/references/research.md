
# Flow Research

Conduct pre-PRD research including codebase analysis and documentation lookup.

## Usage

```
flow-research <topic>
```

## Workflow

### Phase 1: Research Initialization

1. **Define Topic:** Use provided argument or ask user
2. **Classify Type:** New Feature, Bug Investigation, Integration, Refactoring, Performance

### Phase 2: Codebase Exploration

1. Map relevant modules and files
2. Identify existing patterns
3. Analyze dependencies

### Phase 3: External Documentation

1. Lookup relevant library documentation
2. Note APIs, best practices, gotchas

### Phase 4: Prior Art

1. Check git history for similar work
2. Research external patterns

### Phase 5: Risk Assessment

1. Identify technical risks
2. Plan recovery strategy

### Phase 6: Create Research Document

Create `.agents/research/{research_id}/research.md` with:
- Executive Summary
- Codebase Analysis
- Library Documentation
- Prior Art
- Risk Assessment
- Recommended Approach

## Critical Rules

1. **THOROUGH EXPLORATION** - Analyze codebase before external research
2. **ACTIONABLE OUTPUT** - Research should inform PRD creation
