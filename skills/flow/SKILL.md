---
name: flow
description: "Use when a project has `.agents/`, when the user asks to set up, plan, draft a PRD, research, refine tasks, implement, sync, review, finish, archive, or otherwise work through the Flow lifecycle. Applies to `/flow:*` intents, `.agents/specs/` edits, Beads backend work, and spec-first/TDD workflows that should automatically route into the matching Flow process."
---

# Flow - Context-Driven Development

Use the Flow skill for context-driven development workflows in repos that use `.agents/`. The environment (Beads backend, project root, and tooling) is **automatically detected via hooks** at the start of every session and provided in your `<hook_context>`.

## The Beads-First Mandate

**CRITICAL:** Beads (`bd`) is the **Primary Source of Truth** for task state and persistent context. Markdown files (`spec.md`, `prd.md`) are **Synchronized Views** of this state.

- **PRDs are Epics**: `flow:prd` creates a Master Roadmap by initializing Beads **Epics**.
- **Plans are Task Graphs**: `flow:plan` defines the roadmap by creating Beads **Tasks** linked to the flow epic.
- **Context is Notes**: ALL design decisions, investigation findings, and implementation notes MUST be attached to work items using `bd note <id> "..."`. This ensures context survives session resets and compaction.
- **Sync is Mandatory**: Run `/flow:sync` after any Beads mutation to update the human-readable Markdown view.

## The Zero-Ambiguity Mandate

**CRITICAL:** Every specification (`spec.md`) MUST be a "High-Definition" document. It is NOT a summary; it is a **Worksheet**.

- **PRDs are Sagas**: `flow:prd` acts as the **Orchestrator**, creating a "Master Roadmap" (Sagas) that groups multiple granular flows (Chapters).
- **Deep Research First**: Do NOT defer research to implementation "chapters." ALL analysis, codebase investigation, and architectural decisions MUST be completed during the PRD and Planning phases.
- **Refinement Gate**: You MUST run `flow:refine` autonomously and iteratively until the plan is **Zero-Ambiguity**. A "Ready" plan contains:
  - **Worksheet Granularity**: Specific files, exact line numbers, and code samples for every logic change.
  - **Itemized Todo List**: A step-by-step checklist that a "stateless" or "low-context" executor can follow to succeed 100% correctly without further questions.
- **Agent Autonomy**: You (the agent) are responsible for determining when a plan is granular enough. Do NOT ask the user if refinement is done; iterate until technical completeness is achieved.

## Core Concepts

### Flows

A flow is a logical unit of work (feature or bug fix) backed by a Beads **Epic**. Each flow has:

- **ID format**: `shortname` (e.g., `auth`) — MUST match the Beads Epic ID prefix.
- **Location**: `.agents/specs/{flow_id}/`
- **Files**: spec.md (synchronized view), metadata.json, learnings.md (synced from notes)

### Status Markers (Markdown Sync)

- `[ ]` - Pending/New (Beads: `open`)
- `[~]` - In Progress (Beads: `in_progress`)
- `[x]` - Completed (Beads: `closed`)
- `[!]` - Blocked (Beads: `blocked`)
- `[-]` - Skipped (Beads: `deferred` / `closed:skipped`)

### Beads Integration

Flow supports two persistence modes:

- **Official Beads (`bd`)** - default
- **No Beads** - degraded mode for planning, docs, and lightweight local work

## Universal File Resolution Protocol

**To locate files within Flow context:**

1. **Project Index**: `.agents/index.md`
2. **Flow Registry**: `.agents/flows.md`
3. **Flow Index**: `.agents/specs/{flow_id}/index.md`

**Default Paths:**

- Product: `.agents/product.md`
- Tech Stack: `.agents/tech-stack.md`
- Workflow: `.agents/workflow.md`
- Patterns: `.agents/patterns.md`
- Knowledge Base: `.agents/knowledge/`
- Knowledge Index: `.agents/knowledge/index.md`
- Beads Config: `.agents/beads.json`

## Workflow Commands

| Gemini CLI / OpenCode | Purpose |
|------------------------|---------|
| `/flow:setup` | Initialize project with context files and Beads |
| `/flow:prd` | **Orchestrator**: Create Beads **Epics** and Master Roadmap |
| `/flow:plan` | **Planner**: Create Beads **Tasks** and sync to spec.md |
| `/flow:sync` | **Syncer**: Bridge Beads state (notes/status) to Markdown |
| `/flow:refine` | **Refiner**: Expand coarse tasks into implementation worksheets |
| `/flow:implement` | **Executor**: Execute tasks using TDD + Beads claim/note flow |
| `/flow:status` | Display progress overview from Beads |
| `/flow:archive` | Archive completed flow and elevate patterns |

<workflow>

## Task Workflow (TDD) - Beads-First

**See `references/discipline.md` for iron laws, rationalization tables, and red flags.**

1. **Select task** from the active backend's ready queue (`bd ready`).
2. **Mark in progress** and claim the task (`bd update <id> --claim`).
3. **Investigate & Note**: Record findings/decisions with `bd note <id> "..."`.
4. **Write failing tests** (Red phase) - MUST confirm failure for right reason.
5. **Implement** minimal code to pass (Green phase) - MUST confirm all tests pass.
6. **Refactor** with test safety — must stay green.
7. **Commit** with format: `<type>(<scope>): <description>`.
8. **Close task** in Beads with the commit reference (`bd close <id> --reason "[abc1234] Done"`).
9. **Sync to markdown**: Run `/flow:sync` to update spec.md and learnings.md.

</workflow>

<guardrails>

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers to spec.md manually. Beads is the source of truth — after ANY Beads state change, you MUST run `/flow:sync` to keep spec.md in sync.

**CRITICAL:** Read `.agents/workflow.md` before planning or implementation and prefer the repo's canonical commands there. If the repo clearly has better aggregate commands than the workflow currently documents, refresh the workflow or capture the correction in learnings/knowledge.

**CRITICAL:** Be collaborative and constructive. Never use dismissive ownership-deflecting language such as "not my issue" or "not caused by my change." If unrelated failures block progress, describe them factually, offer the smallest helpful next step, and ask the user how to prioritize.

**CRITICAL:** Make minimal targeted changes. Do not silently descope, take shortcuts because the task is messy, or make unrelated opportunistic edits without approval.

</guardrails>

<validation>

### TDD Task Validation Checkpoint

Before marking a task complete, verify:

- [ ] Failing test was confirmed to fail for the RIGHT reason before implementation
- [ ] All tests pass after implementation (not just the new one)
- [ ] Coverage target (>80%) was checked with actual numbers
- [ ] Task was closed in Beads with the commit SHA (`bd close <id> --reason "[abc1234]..."`)
- [ ] `/flow:sync` was run to update spec.md
- [ ] Commit message follows `<type>(<scope>): <description>` format

</validation>

## Knowledge Flywheel (Synthesis Mandate)

You are responsible for the entire knowledge lifecycle. It is NOT a manual copy-paste; it is a **Synthesis**.

1. **Capture**: After each task, append discoveries to the flow's `learnings.md`.
2. **Elevate**: At phase/flow completion, autonomously identify reusable patterns and move them to `.agents/patterns.md`.
3. **Synthesize**: During sync and archive, integrate learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/` (e.g., `architecture.md`, `conventions.md`).
    - **Update the State**: Revise chapters to reflect the *current* authoritative state of the codebase.
    - **Do NOT Outline History**: Your goal is to produce a formal, up-to-date guide for future agents, not a log of past activities.
4. **Inherit**: New flows MUST read `patterns.md` and scan `.agents/knowledge/` chapters before planning.

Treat repeated user corrections or visible frustration as high-signal workflow gaps. Capture them in `learnings.md`, elevate them into `.agents/patterns.md`, and refine `.agents/skills/flow-memory-keeper/SKILL.md` (if present) so the same miss does not recur.

## The Cleanup Mandate

**CRITICAL:** The `.agents/` directory must be in its most authoritative and implementation-ready state.

- **Knowledge Re-synthesis**: Consolidate `.agents/knowledge/` into a single, unified, authoritative "Current State" guide. Focus on "how," not "why" or history.
- **Spec & Beads Integrity**: Audit all flows in `.agents/specs/`. Verify task status against SOURCE CODE. Sync status with Beads (create if missing).
- **Archive Requirement**: Every completed flow MUST be archived and moved out of the `specs/` folder following the archive policy.
- **Artifact Consolidation**: Synthesize stale `.agents/research/` and `.agents/plans/` into active specs or knowledge chapters.
- **Pattern Optimization**: Reorganize, index, and synthesize `.agents/patterns.md` and `learnings.md` into high-fidelity guidance.

<workflow>

## Phase Completion Protocol

**No completion claims without fresh verification evidence.** See `references/discipline.md`.

When a phase completes:

1. **Run full test suite** — read output, confirm 0 failures
2. **Verify coverage** for phase files — confirm with actual numbers
3. **Dispatch code review** (recommended) — see `references/review.md`
4. **Create checkpoint commit**
5. Propose manual verification steps
6. Await user confirmation
7. Record checkpoint in Beads using the active backend's comment/note mechanism
8. Sync to markdown: run `/flow:sync` (MANDATORY)

</workflow>

<validation>

### Phase Completion Validation Checkpoint

Before claiming a phase is complete, verify:

- [ ] Full test suite was run and output was read (not assumed passing)
- [ ] Coverage was verified with actual numbers for phase files
- [ ] `/flow:sync` was run after Beads state change (MANDATORY)
- [ ] No spec.md markers were written manually

</validation>

## Superpowers Protocol (MANDATORY)

When Superpowers skills are available, the following protocols MUST be followed.
If a referenced companion skill is unavailable in the current host, execute the same protocol inline instead of skipping it:

1. **Brainstorming & Planning Overrides:**
    - All brainstorming sessions (`superpowers:brainstorming`) MUST write their results to `.agents/specs/<flow_id>/spec.md`.
    - All implementation plans (`superpowers:writing-plans`) MUST be written to `.agents/specs/<flow_id>/spec.md`.
    - **NEVER** use `docs/superpowers/` for Flow-related artifacts.
    - If a skill tries to use a default path, you MUST intercept and redirect to `.agents/specs/<flow_id>/`.
    - Do not declare PRD or planning work complete while obvious research gaps remain.
    - Before approving a plan for execution, you MUST invoke the iterative refinement gate: ask "Do I have enough task information written for this PRD/flow to complete it correctly in the first pass?". If not, you MUST run `/flow:refine` (following the **Iteration Iron Law** in `references/refine.md`) until the plan is implementation-ready with concrete file targets, line numbers, and code samples.

2. **Implementation Orchestration:**
    - When running `/flow:implement`, you MUST explicitly recommend the "Subagent-Driven" approach to the user if `superpowers:subagent-driven-development` is available.
    - You MUST use `superpowers:subagent-driven-development` to orchestrate the implementation of tasks.
    - If the subagent workflow is unavailable, execute the same TDD, review, and context-preservation protocol in single-agent mode.
    - Before delegating, you MUST ensure the task has undergone iterative refinement. Preserve subagent context by passing the relevant spec or PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements.

3. **Self-Review & Quality Gate:**
    - Before finalizing any PRD (`/flow:prd`) or Plan (`/flow:plan`), you MUST invoke `code-reviewer` (or use the internal `Spec Review Loop`) to validate the artifacts against project patterns and requirements.
    - For PRDs, ensure they follow the "Master Roadmap" structure.
    - For Plans, ensure they are "Unified Specs" (Requirements + TDD Tasks).

4. **TDD & Verification:**
    - Always use `superpowers:test-driven-development` for task implementation.
    - Always use `superpowers:verification-before-completion` before closing a task in Beads or marking it complete.
    - If those skills are unavailable, follow the same TDD and verification discipline inline. The process remains mandatory.

## Proactive Behaviors

When Flow skill is active:

- **Check Hook Context First**: ALWAYS scan `<hook_context>` for `## Flow Environment Context`. Use the injected **Flow Root**, **Beads Backend**, and **Canonical Commands** as authoritative ground truth. Skip manual discovery steps if this information is present.
- **Check for resume state** at session start if hook context is missing.
- **Detect the active Beads backend** (if not in hook context) and load its current context.
- Scan `knowledge/index.md` for relevant past learnings when starting a new flow.
- Prompt for learnings capture after tasks.
- Suggest pattern elevation at phase completion.
- If `.agents/skills/flow-memory-keeper/SKILL.md` exists, invoke it for sync, archive, finish, and failure/refinement work.
- If the user repeats a correction or sounds frustrated about something being forgotten, treat that as mandatory knowledge capture rather than optional polish.
- Warn if tech-stack changes without documentation.
- Enforce mandatory `/flow:sync` after any Beads state change.
- Prefer canonical repo commands (setup, lint, test, typecheck, verify) as defined in the **Core Project Truths** section of the hook context or in `.agents/workflow.md`.
- Treat repeated reminders like "use make lint" or "don't forget to test" as workflow failures that must be captured and elevated.
- **Mandatory Superpowers Integration:** If Superpowers is detected, all workflows (PRD, Plan, Implement) MUST follow the **Superpowers Protocol** above.
- Invoke `flow:apilookup` proactively for external API/docs/version/migration questions.

## References Index

For detailed instructions and directives for specific flow commands, refer to the following documents in `references/`:

- **[Setup](references/setup.md)** - `/flow:setup`
- **[PRD](references/prd.md)** - `/flow:prd`
- **[Plan](references/plan.md)** - `/flow:plan`
- **[Refine](references/refine.md)** - `/flow:refine`
- **[Implement](references/implement.md)** - `/flow:implement`
- **[Sync](references/sync.md)** - `/flow:sync`
- **[Status](references/status.md)** - `/flow:status`
- **[Revert](references/revert.md)** - `/flow:revert`
- **[Validate](references/validate.md)** - `/flow:validate`
- **[Revise](references/revise.md)** - `/flow:revise`
- **[Archive](references/archive.md)** - `/flow:archive`
- **[Task](references/task.md)** - `/flow:task`
- **[Docs](references/docs.md)** - `/flow:docs`
- **[Research](references/research.md)** - `/flow:research`
- **[Refresh](references/refresh.md)** - `/flow:refresh`
- **[Finish](references/finish.md)** - `/flow:finish`
- **[Review](references/review.md)** - `/flow:review`
- **[Discipline](references/discipline.md)** - TDD, debugging, and verification iron laws

<context>

## Companion Skills

These Flow skills enhance specific phases of development. They activate automatically based on context, but can also be invoked explicitly.

### Thinking Tools

- **`flow:challenge`** — Use when evaluating claims, reviewing feedback, or when agreement feels reflexive. Forces structured critical reassessment.
- **`flow:consensus`** — Use when evaluating decisions with multiple valid approaches. Rotates through advocate/critic/neutral stances. Sequential mode for bounded decisions, subagent mode for high-stakes architectural choices.
- **`flow:deepthink`** — Use when a problem resists quick answers or investigation is going in circles. Tracks hypothesis, evidence, and confidence level to prevent circular reasoning.
- **`flow:perspectives`** — Shared foundation providing stance prompts and critical thinking frameworks. Loaded automatically by other companion skills.

### Analysis Tools

- **`flow:tracer`** — Use for systematic code exploration: execution traces, dependency mapping, and data flow analysis. Start at a known point, follow connections outward, build a map.
- **`flow:docgen`** — Use for systematic documentation generation with progress tracking. File-by-file analysis ensuring complete coverage.
- **`flow:apilookup`** — Use for documentation lookups. Checks local skill references first, then targets known URLs, then falls back to web search.
- **`flow:refine`** — Use (via `references/refine.md`) when a PRD or spec exists but the task details are still too coarse for reliable first-pass implementation.
- **`integrating-agent-platforms`** — Use for host plugin, extension, marketplace, cache, and update behavior.
- **`presenting-install-menus`** — Use when optional tooling should be offered with concise menu-driven choices.

### Reviewer Personas

These can be dispatched as specialized subagents during code review or design evaluation:

- **`flow:devils-advocate`** — Adversarial reviewer applying critic stance. Surfaces risks and untested assumptions.
- **`flow:security-auditor`** — OWASP-informed security review. Checks injection, auth, data exposure, input validation, dependencies.
- **`flow:architecture-critic`** — Evaluates structural quality: boundaries, coupling, cohesion, testability, simplicity.
- **`flow:performance-analyst`** — Identifies bottlenecks: query patterns, memory, I/O, caching, concurrency, resource lifecycle.

### When to Use During Superpowers Workflows

| Superpowers Skill | Companion Skills |
| ----------------- | ---------------- |
| brainstorming | `consensus` for approach evaluation, `challenge` if convergence is too fast, `architecture-critic` for structural implications |
| systematic-debugging | `tracer` for systematic exploration, `deepthink` if hypothesis testing stalls |
| requesting-code-review | `devils-advocate`, `security-auditor`, `architecture-critic`, `performance-analyst` as specialized reviewers |
| receiving-code-review | `challenge` to evaluate feedback before implementing |
| writing-plans | `flow:refine` to expand coarse tasks, `consensus` for architectural decisions, `architecture-critic` for structural quality |

</context>

## Official References

- <https://github.com/cofin/flow>
- <https://raw.githubusercontent.com/cofin/flow/main/README.md>
- <https://github.com/steveyegge/beads>
- <https://github.com/steveyegge/beads/releases>
- <https://geminicli.com/docs/extensions/reference/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<example>
## Example

Add example instructions here.
</example>
