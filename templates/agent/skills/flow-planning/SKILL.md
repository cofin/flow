---
name: flow-planning
description: "Project-tailored Flow planning skill. Use when drafting PRDs, researching, planning, refining, revising, or creating specs for this repository."
---

# Flow Planning (Project-Tailored)

<!-- lifecycle-ownership: owner=flow-planning; operations=prd,plan,refine,revise,research,task -->

## Trigger

Use for `prd|plan|refine|revise|research|task`.

## Project Design Frontier & Architectural Invariants

Every plan generated for this repository must satisfy these mandatory design boundaries:

1. **Scope Boundary**: Planning edits only files under `.agents/bundles/specs/<flow_id>/`. Never edit application source code during planning.
2. **Flow Design Frontier**: Map requirements as a design tree. Evaluate unblocked decisions and present the frontier in structured rounds with opinionated recommendations (`❓ Choice [ID] ... ➡️ Recommendation`).
3. **Multi-Interface Exploration**: Explore competing interface designs before finalizing `spec.md`.
4. **Anti-Fragile Worksheets**: Author task worksheets in `tasks/<id>.md` specifying public interfaces, types, behaviors, and testing seams. Prohibit fragile line numbers and drifting file paths.

## Task Worksheet Standard

A plan is NOT ready if any task is an unrefined stub. Every task file under `.agents/bundles/specs/<flow_id>/tasks/<short_id>.md` must contain:

```markdown
# Task <short_id>: <title>

## Objective
Exact behavioral goal in 1-2 sentences.

## Context
- Files: Target repository paths.
- Tech Stack References: Relevant sections in `.agents/bundles/knowledge/patterns.md`.

## Steps
1. Numbered, exact implementation steps.
2. Symbols, function signatures, and schemas to create or modify.

## Verification
- **Strategy:** `behavior_tdd` | `regression_tdd` | `characterization` | `static_validation`
- **Focused Command:** `{focused_test_command}`
- **Aggregate Command:** `{aggregate_verification_command}`

## Acceptance Criteria
- [ ] Checkable statement 1
- [ ] Checkable statement 2
```

## Workflow

1. **Research Closure**: Resolve codebase facts autonomously. Spawn parallel research subagents for open inquiries.
2. **Draft Spec & Tasks**: Write `spec.md` and complete worksheets in `.agents/bundles/specs/<flow_id>/tasks/`.
3. **Gap Scan**: Reject stubs, vague verification, missing strategies, or stack invariant violations.
4. **Review & Refine**: Run review cycles until Critical/Important findings are zero.

<!-- project-customization: start -->
## Custom Project Planning Rules
<!-- project-customization: end -->
