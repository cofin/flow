---
name: flow-refine
description: "Use when a Flow spec, PRD, or implementation plan exists but the task details are still too coarse for reliable first-pass execution. Apply when lightweight agents, delegated workers, or lower-reasoning modes will implement the work and need concrete files, dependencies, test-first steps, verification, and research gaps resolved before coding."
---

# Flow Refine

## Overview

Use this skill to turn a mostly-correct Flow plan into an implementation-ready plan.

The core question is mandatory:

`Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?`

If the answer is no, the plan is not done. Refine it.

This skill does not write production code. It improves `spec.md`, `prd.md`, and related planning artifacts so lighter-weight executors can implement with minimal additional reasoning.

<workflow>

## Workflow

### Step 1: Load Planning Context

Read the relevant artifacts before refining:

- `.agents/specs/<flow_id>/spec.md` for a single flow
- `.agents/specs/<prd_id>/prd.md` plus planned child specs for a saga
- `.agents/patterns.md`
- relevant `.agents/knowledge/*.md` chapters
- the code paths, tests, migrations, config files, or external docs that the tasks depend on

### Step 2: Run the First-Pass Completeness Test

For each phase and each task, ask:

`Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?`

If no, classify the gap:

- missing file or module targets
- missing dependency or execution order
- missing API, schema, or data-shape detail
- missing migration or rollout guidance
- missing test-first instruction
- missing validation or manual verification steps
- missing external research
- missing user decision or scope boundary

### Step 3: Research-and-Refine Loop

For each gap:

1. Read more code until the affected surfaces are known.
2. Use `flow:tracer` for code-path tracing when the dependency chain is unclear.
3. Use `flow:apilookup` when external library, framework, SDK, or platform behavior is involved.
4. Ask the user only for decisions that cannot be inferred safely.
5. Update the plan with the missing detail.

Repeat until the task no longer depends on avoidable guesswork.

### Step 4: Rewrite Tasks for Lightweight Executors

Every refined task should make these explicit when applicable:

- objective and why it exists
- exact files, modules, commands, or configuration surfaces
- prerequisites or dependencies
- the first failing test to write
- implementation constraints and patterns to follow
- verification commands and manual checks
- risks, no-go conditions, or follow-up notes

### Step 5: Close Research Gaps Before Declaring Planning Done

After refining all tasks, ask:

`If implementation started now, what research would still be needed?`

If the answer is anything beyond minor execution noise:

- run the missing research now
- update the relevant `spec.md`, `prd.md`, or knowledge artifact
- repeat the check

Planning is only complete when the roadmap and child plans no longer leave obvious research holes for later.

</workflow>

<guardrails>

## Guardrails

- **Do not write implementation code** while refining tasks.
- **Do not keep vague task text** such as "wire it up", "finish integration", or "handle edge cases" without concrete detail.
- **Do not invent requirements** that are not grounded in the user request, codebase, or confirmed constraints.
- **Do not hide uncertainty**. If a decision remains open, record it explicitly instead of pretending the task is implementation-ready.
- **Do not stop at a high-level roadmap** if child flows still need obvious research to execute correctly.

</guardrails>

<validation>

## Validation Checkpoint

Before declaring a refined plan ready, verify:

- [ ] each task has enough detail for correct first-pass implementation
- [ ] file or module targets are specific where applicable
- [ ] dependencies and ordering are explicit
- [ ] test-first expectations are written into implementation tasks
- [ ] verification steps are concrete
- [ ] remaining research gaps were resolved or explicitly recorded as user decisions
- [ ] lightweight executors would not need major additional discovery for the happy path

</validation>

<example>

## Example

Before:

```markdown
### Phase 2: Integrate auth
- [ ] Add auth to API
```

After:

```markdown
### Phase 2: Integrate auth
- [ ] Task 2.1: Add request-auth middleware to `src/api/middleware/auth.py`
  - Write a failing test in `tests/unit/api/test_auth_middleware.py` for missing bearer token handling.
  - Reuse the existing `ServiceError` pattern from `src/api/errors.py`.
  - Apply middleware only to routes declared in `src/api/routes/private.py`.
  - Verify with `pytest tests/unit/api/test_auth_middleware.py -q`.
  - Manual check: hit `/private/me` with and without a token and confirm `401` vs `200`.
```

</example>

---

## Companion Usage

- Use after `flow:plan` when tasks still feel too coarse.
- Use during `flow:prd` after drafting chapter specs to close research gaps across the roadmap.
- Use before `flow:implement` if lightweight agents or delegated workers will do the coding.
