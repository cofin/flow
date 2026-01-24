---
description: Create a PRD with research integration, recovery guidelines, and comprehensive specs
argument-hint: <description>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__sequential-thinking__sequentialthinking, mcp__pal__planner
---

# Flow PRD

Creating PRD for: **$ARGUMENTS**

## Phase 0: Setup Check

Using the **Universal File Resolution Protocol**, verify:
- **Product Definition** (`.agent/product.md`)
- **Tech Stack** (`.agent/tech-stack.md`)
- **Workflow** (`.agent/workflow.md`)

If ANY missing: "Flow not set up. Run `/flow-setup` first." → HALT

---

## Phase 1: Research Integration Check

### 1.1 Detect Available Research

Check if `.agent/research/` exists and contains research documents.

**If Research Exists:**
> "I found existing research that may be relevant:
> 1. [research_id]: [topic] (Created: [date])
>
> Would you like to:
> A) Use this research as basis for PRD
> B) Create PRD without prior research
> C) Run `/flow-research` first to conduct new research"

**If Research Selected:** Read and store context for specification generation.

**If No Research:** Proceed with note about running `/flow-research` for complex features.

---

## Phase 2: Get PRD Description

1. **If `$ARGUMENTS` provided:** Use as PRD description
2. **If research selected:** Use research topic as starting point
3. **If empty:** Ask user for description

**Infer PRD Type:** Feature, Bug, Refactor, or Chore (do NOT ask user).

---

## Phase 3: Interactive Specification Generation

### 3.1 Questioning Phase

Ask questions **sequentially** (one at a time) to gather spec details:

- **FEATURE:** 3-5 questions about functionality, UI, logic, interactions
- **BUG:** 2-3 questions about reproduction, expected vs actual behavior
- **REFACTOR/CHORE:** 2-3 questions about scope, constraints, success criteria

**Guidelines:**
- Provide 2-3 plausible options (A, B, C) for each question
- Last option MUST be "Type your own answer"
- Refer to Product Definition and Tech Stack for context

### 3.2 Specification Template

```markdown
# [PRD Title]

## Overview
[Brief description - what and why]

## Research Reference
[Link to research or "No prior research conducted"]

## Functional Requirements
### Must Have
- [ ] [Requirement 1]

### Should Have
- [ ] [Requirement 2]

### Nice to Have
- [ ] [Requirement 3]

## Non-Functional Requirements
- **Performance:** [Targets]
- **Security:** [Considerations]
- **Accessibility:** [Requirements]

## Technical Approach
### Recommended Implementation
[Based on research and codebase patterns]

### Files to Modify
[From codebase analysis]

## Acceptance Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]

## Out of Scope
- [Excluded items]

## Dependencies
- [Internal and external dependencies]

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Strategy] |

### Recovery Strategy
**Rollback Trigger:** [Conditions]
**Rollback Steps:** [How to revert]
**Safe Checkpoints:** [After each phase]
```

### 3.3 User Confirmation

Present drafted `spec.md` for review. Revise until confirmed.

---

## Phase 4: Plan Generation

1. Read confirmed spec.md
2. Read **Workflow** file
3. Generate `plan.md` with Phases, Tasks, Sub-tasks

**Requirements:**
- Status markers `[ ]` for EVERY task/sub-task
- Follow TDD methodology from Workflow
- Include checkpoint task per phase: `[ ] Task: Checkpoint - Verify Phase X complete`
- Inject Phase Completion tasks from Workflow

Present drafted `plan.md` for user confirmation.

---

## Phase 5: Create PRD Artifacts

### 5.1 Generate PRD ID

Slug format from description:
- Lowercase, hyphens for spaces
- Remove special characters
- Example: "Add User Authentication" → `user-auth`

Check `.agent/specs/` for existing PRD with same name. If exists, suggest different name.

### 5.2 Create Files

```bash
mkdir -p .agent/specs/{prd_id}
```

Create:
- `.agent/specs/{prd_id}/spec.md`
- `.agent/specs/{prd_id}/plan.md`
- `.agent/specs/{prd_id}/metadata.json`
- `.agent/specs/{prd_id}/index.md`

### 5.3 Update PRD Registry

Append to `.agent/prds.md`:
```markdown
---
- [ ] **PRD: {description}**
*Link: [./specs/{prd_id}/](./specs/{prd_id}/)*
*Risk Level: [low|medium|high]*
```

---

## Phase 6: Quality Gates

Before completion, verify:
- [ ] Functional requirements are specific and testable
- [ ] Acceptance criteria are measurable
- [ ] Technical approach references codebase patterns
- [ ] Risk assessment includes at least 2 risks
- [ ] Recovery strategy defined
- [ ] Plan aligns with workflow (TDD, coverage)

---

## Phase 7: Completion

> "PRD '{prd_id}' created.
>
> **Summary:**
> - Specification: `.agent/specs/{prd_id}/spec.md`
> - Plan: `.agent/specs/{prd_id}/plan.md`
> - Risk Level: [level]
>
> **IMPORTANT:** I will NOT automatically start implementation.
> Run `/flow-implement` when ready to begin."

**CRITICAL:** Never auto-implement. Wait for explicit `/flow-implement` command.

---

## Critical Rules

1. **SEQUENTIAL QUESTIONS** - One question at a time
2. **USER CONFIRMATION** - Spec and plan must be approved before writing
3. **NO AUTO-IMPLEMENT** - Never start implementation automatically
4. **QUALITY GATES** - Verify all requirements before completion
