# Flow Refine

Use this process to enforce the **Zero-Ambiguity Mandate** by turning a mostly-correct Flow plan into an implementation-ready **Worksheet**.

## Overview

Refinement is an autonomous, iterative process that MUST continue until the plan is **High-Definition**. A plan is only "Ready" when a stateless, low-context executor can complete it 100% correctly in one pass without further questions.

**THE ZERO-AMBIGUITY STANDARD:**

- **Exact Line Numbers**: All file targets MUST include exact line numbers for logic insertion or modification.
- **Code Samples**: Provide idiomatic code snippets for all logic that is more complex than a standard boilerplate pattern.
- **Itemized Todo List**: Every task MUST be broken down into a complete itemized checklist of specific changes.
- **No Guesswork**: Forbid vague instructions like "wire up", "handle edge cases", or "integrate logic."

## Workflow

### Step 1: Load Planning Context

Read the relevant artifacts before refining:

- `.agents/specs/<flow_id>/spec.md` for a single flow
- `.agents/specs/<prd_id>/prd.md` plus planned child specs for a saga
- `.agents/patterns.md`
- relevant `.agents/knowledge/*.md` chapters
- the code paths, tests, migrations, config files, or external docs that the tasks depend on

### Step 2: The Zero-Ambiguity Test

For each task, apply the **Stateless Executor Test**:
`If I handed this task to an agent with zero project context, could they implement it 100% correctly based ONLY on this text and the provided code samples?`

If the answer is "No" or "Maybe," you MUST classify the gap and iterate.

### Step 3: Research-and-Refine Loop (Iterative)

**IRON LAW: Iterate until technical completeness is achieved.**

1. **Deep Code Dive**: Read more code until the affected surfaces are known (extract exact line numbers).
2. **Pattern Matching**: Provide code samples for the expected implementation pattern based on `patterns.md` or existing code.
3. **Dependency Analysis**: Use `flow:tracer` if the call chain is unclear.
4. **Autonomous Completion**: You (the agent) are responsible for determining when refinement is done. Do NOT ask the user if it's granular enough; iterate until the **Zero-Ambiguity Standard** is met.

### Step 4: Transform Plans into Worksheets

Rewrite the `Implementation Plan` section in `spec.md` into a **Worksheet**. Every task should include:

- **Exact Targets**: `file_path:line_number`.
- **Implementation Strategy**: Markdown-formatted code snippets.
- **Itemized Checklist**:
  - [ ] Specific change 1
  - [ ] Specific change 2
  - [ ] Verification step
- **Test-First Instructions**: Exact failure reason for the initial failing test.

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
