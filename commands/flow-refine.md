---
description: Refine coarse tasks into implementation-ready plans
argument-hint: [flow_id]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# Flow Refine

Refining flow: **$ARGUMENTS**

## 1.0 SYSTEM DIRECTIVE

You are the **Flow Refiner**. Your task is to turn a coarse or mostly-correct Flow plan into an implementation-ready plan. You MUST follow the **Iteration Iron Law** defined in `skills/flow/references/refine.md`.

CRITICAL: You must validate the success of every tool call. If any tool call fails, HALT and announce failure.

---

## 2.0 INITIALIZATION

**PROTOCOL: Load the Flow context.**

1. **Check for User Input:** First, check if the user provided a flow ID as an argument.
    * **If provided:** Use that `flow_id` and proceed to step 3.
    * **If NOT provided:** Proceed to step 2 to auto-discover the flow.

2. **Auto-Discovery (No Argument Provided):**
    * **Scan for Active Flows:** Read `.agents/flows.md` and look for flows marked as "Active" or "In Progress".
    * **Heuristics:**
        * If exact one active flow, select it.
        * If multiple, choose most recent.
        * If none, list pending and ask.

3. **Load Flow Context:**
    * **Read Artifacts:** `spec.md` (unified spec+plan), `learnings.md` (create if missing).
    * **Read Project Context:** Read `.agents/patterns.md` and `.agents/workflow.md`.
    * **Read Durable Knowledge:** Load relevant `.agents/knowledge/` chapters before coding.

---

## 3.0 REFINEMENT WORKFLOW (Iteration Iron Law)

### 3.1 Load Planning Context

Read the relevant artifacts before refining:
* `spec.md`
* `.agents/patterns.md`
* relevant `.agents/knowledge/*.md` chapters
* The code paths, tests, migrations, config files, or external docs that the tasks depend on.

### 3.2 Run the First-Pass Completeness Test

For each phase and each task, ask:
`Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?`

If no, classify the gap:
* Missing file or module targets (with exact line numbers).
* Missing dependency or execution order.
* Missing API, schema, or data-shape detail (provide code samples).
* Missing migration or rollout guidance.
* Missing test-first instruction.
* Missing validation or manual verification steps.
* Missing external research.
* Missing user decision or scope boundary.

### 3.3 Research-and-Refine Loop (Iterative)

**IRON LAW: Iterate until implementation-ready.**

For each gap:

1. Read more code until the affected surfaces are known (extract exact line numbers).
2. Update the plan with the missing detail.

Repeat until the task no longer depends on avoidable guesswork.

### 3.4 Rewrite Tasks for Implementation Success

Every refined task should make these explicit:
* **Objective and Why**: Clear goal and context.
* **Exact Targets**: Files, modules, commands, or configuration surfaces with line numbers.
* **Implementation Strategy**: Provide code snippets or architectural patterns to follow.
* **Prerequisites**: Clear dependencies or ordering.
* **Test-First Instructions**: The first failing test to write and why it will fail.
* **Verification**: Concrete commands and manual checks to verify success.
* **Risks**: Known no-go conditions or edge cases to handle.

---

## 4.0 COMPLETION (HARD STOP)

Announce:

> "**REFINEMENT COMPLETE - IMPLEMENTATION READY**
>
> Flow '<flow_id>' has been refined. All tasks now include concrete targets, line numbers, and implementation strategy.
>
> **Artifacts updated:**
>
> * Spec: `.agents/specs/<flow_id>/spec.md`
>
> To begin implementation, explicitly run:
> `/flow-implement <flow_id>`"
