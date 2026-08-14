# Flow Refine

Refinement uses `skills/flow/references/state.md` as the sole plan-identity and mutation contract. Approved plan-bearing edits increment `plan_revision` exactly once, clear `plan_commit`, update all task copies before the spec, and use the documented file-tool transaction protocol; refinement never edits lifecycle/checklist state ad hoc.

Use `skills/flow/references/interaction.md` as the sole procedure authority for
human decisions and approval/refinement gates. Execute the Markdown loop
directly; never invoke a planning evaluator.

<!-- planning-contract: structured-choice-v1 -->
```yaml
interaction_authority: skills/flow/references/interaction.md
planning_loop:
  phases: [research_closed, draft, gap_scan, refine, revision_update, review, approved, revise, blocked]
  gap_scan:
    reject: [deferred_research, unresolved_decisions, stub_body, vague_verification, missing_verification_strategy, overlapping_ownership, oversized_task]
    require: [requirement_to_task_traceability, one_invocation_per_task, one_commit_per_task]
  revision_update:
    on_plan_change: [increment_plan_revision_once, copy_revision_to_spec_and_all_tasks, clear_plan_commit, rerun_validation]
  review:
    max_external_rounds: 3
    blocking_severities: [Critical, Important]
    on_limit: blocked
```

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

- `.agents/bundles/specs/<flow_id>/spec.md` and its `tasks/*.md` files for a single flow
- `.agents/bundles/specs/<prd_id>/spec.md` (the roadmap) plus planned child specs for a saga
- `.agents/bundles/knowledge/patterns.md`
- relevant `.agents/bundles/knowledge/` chapters
- the code paths, tests, migrations, config files, or external docs that the tasks depend on

### Step 2: The Zero-Ambiguity Test

For each task, apply the **Stateless Executor Test**:
`If I handed this task to an agent with zero project context, could they implement it 100% correctly based ONLY on this text and the provided code samples?`

Also require every requirement to map to a task and verification scenario;
every task to declare and justify `verification_strategy`, exact verification
commands/outcomes, and exclusive file ownership; and each task to fit one
invocation and one commit. Select the strategy from the change class using
`skills/flow/references/discipline.md`; never manufacture a red test for work
whose strategy begins from a green or native-validation baseline.
If the answer is "No" or "Maybe," classify the gap and iterate.

### Step 3: Research-and-Refine Loop (Iterative)

**IRON LAW: Iterate until technical completeness is achieved.**

1. **Deep Code Dive**: Read more code until the affected surfaces are known (extract exact line numbers).
2. **Pattern Matching**: Provide code samples for the expected implementation pattern based on `patterns.md` or existing code.
3. **Dependency Analysis**: Use `flow:tracer` if the call chain is unclear.
4. **Autonomous Completion**: You (the agent) are responsible for determining when refinement is done. Do NOT ask the user if it's granular enough; iterate until the **Zero-Ambiguity Standard** is met.
5. **Deterministic rejection:** Do not pass deferred research, unresolved
   decisions, stub bodies, vague verification, missing verification strategy,
   overlapping ownership, missing requirement traceability, or oversized tasks.
6. **True user decisions:** Ask exactly one product/trade-off decision at a
   time through `structured-choice-v1`; never use `open` when choices can be
   responsibly enumerated.

### Step 4: Transform Plans into Worksheets

Rewrite the `Implementation Plan` section in `spec.md` into a **Worksheet**. Every task should include:

- **Exact Targets**: `file_path:line_number`.
- **Implementation Strategy**: Markdown-formatted code snippets.
- **Itemized Checklist**:
  - [ ] Specific change 1
  - [ ] Specific change 2
  - [ ] Verification step
- **Strategy Instructions**: Exact initial proof, expected result, and final evidence required by the selected strategy. For `behavior_tdd` and `regression_tdd`, include the intended failing symptom. For other strategies, name the green/native baseline or negative-state gate proof instead.

### Step 5: Close Research Gaps Before Approval

After refining all tasks, ask:

`If implementation started now, what research would still be needed?`

If the answer is anything beyond minor execution noise:

- run the missing research now
- update the relevant `spec.md`, task file, or knowledge artifact
- repeat the check

Planning is only complete when the roadmap and child plans no longer leave obvious research holes for later.

### Step 6: Revision, Review, and Approval Loop

When refinement changes plan-bearing content, apply one state-contract `revise`:
increment `plan_revision` exactly once, copy it to the spec and every task
before the spec write, clear `plan_commit`, and rerun validation. Preserve
identity when content did not change; only a later verified plan-bind checkpoint
updates `plan_commit`.

Request a fresh `code-reviewer` result for the current revision. Apply all
actionable findings and repeat refinement/revision/validation/review. Cap
external dispatch at three rounds. Remaining Critical or Important findings
after round three return `blocked`, list the findings, and require user
direction; Ready is forbidden.

Before quality passes, the user gate is exactly `Revise|Refine`. After it
passes, it is exactly `Approve|Revise|Refine`, reordered so the contextual
recommendation is first. Approve advances. Revise asks one
`open(free_form_reason=revision_details)` follow-up; Refine asks the next
structured gap. Both apply changes and rerun the loop. Cancellation stops
without approval. Never persist a crucial artifact as approved before a valid
Approve result.

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
- [ ] Strategy-appropriate initial evidence is written into every task; failing-test expectations appear only for behavior and regression TDD.
- [ ] Verification steps are concrete.
- [ ] Every task declares a verification strategy and exact expected outcome.
- [ ] Requirement-to-task/test traceability is complete.
- [ ] File ownership does not overlap and each task fits one invocation/commit.
- [ ] Remaining research gaps were resolved or explicitly recorded as user decisions.
- [ ] Lightweight executors would not need major additional discovery for the happy path.
- [ ] The current revision passed fresh review or is explicitly blocked after
      three unresolved Critical/Important rounds.
