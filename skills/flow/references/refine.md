# Flow Refine

Use this process to turn a mostly-correct Flow plan into an implementation-ready plan.

## Overview

Refinement is an iterative process that must continue until the agent can confidently implement the plan in one pass without asking for more info. Every refined task MUST include:

- Concrete file targets and **line numbers** where applicable.
- **Code samples** for complex logic, API usage, or patterns to follow.
- Specific dependencies and execution order.
- Test-first instructions with expected failure reasons.
- Concrete verification commands and manual checks.

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

- missing file or module targets (with exact line numbers)
- missing dependency or execution order
- missing API, schema, or data-shape detail (provide code samples)
- missing migration or rollout guidance
- missing test-first instruction
- missing validation or manual verification steps
- missing external research
- missing user decision or scope boundary

### Step 3: Research-and-Refine Loop (Iterative)

**IRON LAW: Iterate until implementation-ready.**

For each gap:

1. Read more code until the affected surfaces are known (extract exact line numbers).
2. Use `flow:tracer` for code-path tracing when the dependency chain is unclear.
3. Use `flow:apilookup` when external library, framework, SDK, or platform behavior is involved.
4. Provide code samples for the expected implementation pattern.
5. Ask the user only for decisions that cannot be inferred safely.
6. Update the plan with the missing detail.

Repeat until the task no longer depends on avoidable guesswork.

### Step 4: Rewrite Tasks for Implementation Success

Every refined task should make these explicit:

- **Objective and Why**: Clear goal and context.
- **Exact Targets**: Files, modules, commands, or configuration surfaces with line numbers.
- **Implementation Strategy**: Provide code snippets or architectural patterns to follow.
- **Prerequisites**: Clear dependencies or ordering.
- **Test-First Instructions**: The first failing test to write and why it will fail.
- **Verification**: Concrete commands and manual checks to verify success.
- **Risks**: Known no-go conditions or edge cases to handle.

### Step 5: Close Research Gaps Before Approval

After refining all tasks, ask:

`If implementation started now, what research would still be needed?`

If the answer is anything beyond minor execution noise:

- run the missing research now
- update the relevant `spec.md`, `prd.md`, or knowledge artifact
- repeat the check

Planning is only complete when the roadmap and child plans no longer leave obvious research holes for later.

---

## Guardrails

- **Do not write implementation code** while refining tasks.
- **Do not keep vague task text** such as "wire it up", "finish integration", or "handle edge cases" without concrete detail.
- **Do not invent requirements** that are not grounded in the user request, codebase, or confirmed constraints.
- **Do not hide uncertainty**. If a decision remains open, record it explicitly instead of pretending the task is implementation-ready.
- **Do not stop at a high-level roadmap** if child flows still need obvious research to execute correctly.

---

## Validation Checkpoint

Before declaring a refined plan ready, verify:

- [ ] Each task has enough detail for correct first-pass implementation (zero guesswork).
- [ ] File or module targets are specific with line numbers where applicable.
- [ ] Code samples or snippets are provided for complex logic.
- [ ] Dependencies and ordering are explicit.
- [ ] Test-first expectations are written into implementation tasks.
- [ ] Verification steps are concrete.
- [ ] Remaining research gaps were resolved or explicitly recorded as user decisions.
- [ ] Lightweight executors would not need major additional discovery for the happy path.
