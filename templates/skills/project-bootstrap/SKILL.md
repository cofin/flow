---
name: project-bootstrap
description: Analyze any project and create comprehensive personal Claude commands and agents tailored to that project's tech stack, patterns, and conventions. Use when bootstrapping new projects, setting up Claude commands, or creating skills.
---

# Project Bootstrap Skill

Analyze any project and create comprehensive personal Claude commands and agents tailored to that project's tech stack, patterns, and conventions.

## When to Use This Skill

Use when the user says:
- "Bootstrap this project"
- "Set up Claude commands for this project"
- "Analyze this project and create skills"
- "Create PRD and implement commands"

## Bootstrap Process

When triggered, Claude should:

### Phase 1: Project Analysis

1. **Explore project structure**:
   - Look at root files: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.
   - Check for existing `.claude/` folder with skills or settings
   - Check for `specs/` or `docs/` folder with PRDs or specifications
   - Identify the tech stack (language, framework, build tools)
   - Find CLAUDE.md or similar instruction files

2. **Identify patterns**:
   - Code organization (monorepo, src layout, etc.)
   - Testing patterns and frameworks
   - Linting/formatting tools
   - CI/CD configuration
   - Database usage
   - API patterns

3. **Catalog existing commands**:
   - Check `~/.claude/commands/` for personal commands
   - Check `.claude/commands/` for project commands
   - Check `.claude/skills/` for project skills

### Phase 2: Create Personal Commands

Create these commands in `~/.claude/commands/`:

#### /prd - Product Requirements Document
#### /implement - Implement from PRD
#### /explore-codebase - Deep codebase analysis
#### /test-feature - Generate tests for a feature

### Phase 3: Report

Provide a summary of:
- What was discovered about the project
- What commands were created
- How to use each command

## Command Templates

### /prd Command

Create at: `~/.claude/commands/prd.md`

```markdown
# PRD: Product Requirements Document Generator

Create a comprehensive PRD for the requested feature.

## Instructions

1. **Understand the request**: Ask clarifying questions if needed
2. **Analyze the codebase**: Explore relevant areas to understand existing patterns
3. **Generate PRD** with these sections:

### PRD Template

# PRD: [Feature Name]

## Overview
[2-3 sentence summary of the feature]

## Problem Statement
[What problem does this solve? Why is it needed?]

## Goals
- [Primary goal]
- [Secondary goals]

## Non-Goals
- [What this feature will NOT do]

## User Stories
- As a [user type], I want [action] so that [benefit]

## Technical Approach

### Architecture
[How this fits into the existing system]

### Components to Create/Modify
| Component | Action | Description |
|-----------|--------|-------------|
| [file/module] | Create/Modify | [what changes] |

### Data Model Changes
[Any database or model changes needed]

### API Changes
[Any API endpoints to add/modify]

## Dependencies
- [External dependencies needed]
- [Internal dependencies]

## Testing Strategy
- Unit tests: [approach]
- Integration tests: [approach]
- E2E tests: [if applicable]

## Rollout Plan
1. [Phase 1]
2. [Phase 2]

## Open Questions
- [Questions that need answers before implementation]

## Success Metrics
- [How we'll measure success]

---

4. **Save the PRD**: Write to `specs/prd-[feature-name].md` or `.claude/specs/` if specs doesn't exist
5. **Offer next steps**: Ask if user wants to proceed to implementation
```

### /implement Command

Create at: `~/.claude/commands/implement.md`

```markdown
# Implement: Execute a PRD or Feature Request

Implement a feature based on a PRD or direct request.

## Instructions

### If PRD exists:
1. Read the PRD from `specs/` or `.claude/specs/`
2. Create a todo list from the PRD's components
3. Implement each component following project patterns
4. Run tests after each significant change
5. Update the PRD with any deviations

### If no PRD:
1. Ask if user wants to create a PRD first (recommended for complex features)
2. For simple features, proceed with implementation
3. Document what was built

## Implementation Checklist

For each component:
- [ ] Understand existing patterns in similar code
- [ ] Write the implementation
- [ ] Add/update types if applicable
- [ ] Write tests
- [ ] Update documentation if needed
- [ ] Run linting and type checking

## Quality Gates

Before marking complete:
1. All tests pass
2. Linting passes
3. Type checking passes (if applicable)
4. Code follows project conventions from CLAUDE.md

## Output

Provide a summary:
- What was implemented
- Files created/modified
- Tests added
- Any follow-up tasks
```

### /explore-codebase Command

Create at: `~/.claude/commands/explore-codebase.md`

```markdown
# Explore Codebase: Deep Analysis

Perform comprehensive codebase analysis to understand architecture and patterns.

## Instructions

1. **Map the structure**:
   - Directory layout
   - Entry points
   - Core modules

2. **Identify patterns**:
   - Architectural patterns (MVC, Clean Architecture, etc.)
   - Code organization conventions
   - Naming conventions
   - Error handling patterns
   - Logging patterns

3. **Document dependencies**:
   - External packages and their purposes
   - Internal module dependencies
   - Database connections
   - External service integrations

4. **Find the "how to"**:
   - How to add a new feature
   - How to add a new API endpoint
   - How to add a new test
   - How to add a new database model

5. **Output**: Create a comprehensive report and optionally save to `.claude/CODEBASE.md`
```

### /test-feature Command

Create at: `~/.claude/commands/test-feature.md`

```markdown
# Test Feature: Generate Comprehensive Tests

Generate tests for a specific feature or component.

## Instructions

1. **Understand the feature**:
   - Read the implementation
   - Identify public interfaces
   - Find edge cases

2. **Determine test types needed**:
   - Unit tests for isolated functions
   - Integration tests for component interactions
   - E2E tests for user flows (if applicable)

3. **Follow project test patterns**:
   - Use existing test fixtures
   - Match test file naming conventions
   - Use project's assertion style

4. **Generate tests covering**:
   - Happy path
   - Error cases
   - Edge cases
   - Boundary conditions

5. **Run and verify**: Execute tests to ensure they pass
```
