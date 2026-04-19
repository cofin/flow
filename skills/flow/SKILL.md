---
name: flow
description: "Use when a project has `.agents/`, when the user asks to set up, plan, draft a PRD, research, refine tasks, implement, sync, review, finish, archive, or otherwise work through the Flow lifecycle. Applies to `/flow:*` intents, `.agents/specs/` edits, Beads backend work, and spec-first/TDD workflows that should automatically route into the matching Flow process."
---

# Flow - Context-Driven Development

Use the Flow skill for context-driven development workflows in repos that use `.agents/`. The environment (Beads backend, project root, and tooling) is **automatically detected via hooks** at the start of every session and provided in your `<hook_context>`.

## The Zero-Ambiguity Mandate

**CRITICAL:** Every specification (`spec.md`) MUST be a "High-Definition" document. It is NOT a summary; it is a **Worksheet**.

- **PRDs are Sagas**: `flow:prd` acts as the **Orchestrator**, creating a "Master Roadmap" (Sagas) that groups multiple granular flows (Chapters).
- **Deep Research First**: Do NOT defer research to implementation "chapters." ALL analysis, codebase investigation, and architectural decisions MUST be completed during the PRD and Planning phases.
- **Refinement Gate**: You MUST run `flow:refine` autonomously and iteratively until the plan is **Zero-Ambiguity**. A "Ready" plan contains:
  - **Worksheet Granularity**: Specific files, exact line numbers, and code samples for every logic change.
  - **Itemized Todo List**: A step-by-step checklist that a "stateless" or "low-context" executor can follow to succeed 100% correctly without further questions.
- **Agent Autonomy**: You (the agent) are responsible for determining when a plan is granular enough. Do NOT ask the user if refinement is done; iterate until technical completeness is achieved.

## Core Concepts

### Flows (formerly PRDs)

A flow is a logical unit of work (feature or bug fix). Each flow has:

- **ID format**: `shortname` (e.g., `auth`)
- **Location**: `.agents/specs/{flow_id}/`
- **Files**: spec.md (unified spec+plan), metadata.json, learnings.md

### Status Markers

- `[ ]` - Pending/New
- `[~]` - In Progress
- `[x]` - Completed (with commit SHA: `[x] abc1234`)
- `[!]` - Blocked (logged in blockers.md)
- `[-]` - Skipped (logged in skipped.md)

### Beads Integration

Flow supports three persistence modes:

- **Official Beads (`bd`)** - preferred default
- **Compatibility (`br`)** - for older Flow repos and existing `br`-centric workflows
- **No Beads** - degraded mode for planning, docs, and lightweight local work

Use `choosing-beads-backend` when selecting or migrating the backend.

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

**Host note:** Claude Code uses `/flow-command` and Gemini CLI / OpenCode use `/flow:command`.
Codex currently runs the same workflows via the installed Flow skill and natural-language requests such as
`Use Flow to set up this project` or `Use Flow to create a PRD for user authentication`.

| Claude Code | Gemini CLI / OpenCode | Purpose |
|-------------|------------------------|---------|
| `/flow-setup` | `/flow:setup` | Initialize project with context files |
| `/flow-prd` | `/flow:prd` | Create feature/bug flow |
| `/flow-plan` | `/flow:plan` | Plan flow with unified spec.md |
| `/flow-sync` | `/flow:sync` | Sync Beads state to spec.md |
| `/flow:refine` | `/flow:refine` | Expand coarse tasks into implementation-ready plan |
| `/flow-implement` | `/flow:implement` | Execute tasks (TDD workflow) |
| `/flow-status` | `/flow:status` | Display progress overview |
| `/flow-revert` | `/flow:revert` | Git-aware revert |
| `/flow-validate` | `/flow:validate` | Validate project integrity |
| `/flow-revise` | `/flow:revise` | Update spec/plan mid-work |
| `/flow-archive` | `/flow:archive` | Archive completed flow |
| `/flow-task` | `/flow:task` | Ephemeral exploration task |
| `/flow-docs` | `/flow:docs` | Documentation workflow |
| `/flow-refresh` | `/flow:refresh` | Sync context with codebase |
| `/flow-finish` | `/flow:finish` | Complete flow: verify, review, merge/PR |
| `/flow-review` | `/flow:review` | Dispatch code review with Beads git range |
| `/flow-cleanup` | `/flow:cleanup` | **Groundskeeper**: Global maintenance and optimization of .agents/ |

<workflow>

## Task Workflow (TDD) - Beads-First

**See `references/discipline.md` for iron laws, rationalization tables, and red flags.**

1. **Select task** from the active backend's ready queue
2. **Mark in progress** using the active backend
3. **Write failing tests** (Red phase) - MUST confirm failure for right reason
4. **Implement** minimal code to pass (Green phase) - MUST confirm all tests pass
   - If `superpowers:subagent-driven-development` is available, use it for implementation subagent orchestration
5. **Refactor** with test safety — must stay green
6. **Verify coverage** (>80% target)
7. **Commit** with format: `<type>(<scope>): <description>`
8. **Attach git notes** with task summary
9. **Sync to Beads** using the active backend
10. **Sync to markdown**: run `/flow:sync` to update spec.md.

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
- [ ] Beads state was synced BEFORE editing spec.md
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

- Check for resume state at session start.
- Detect the active Beads backend and load its current context.
- Scan `knowledge/index.md` for relevant past learnings when starting a new flow.
- Prompt for learnings capture after tasks.
- Suggest pattern elevation at phase completion.
- If `.agents/skills/flow-memory-keeper/SKILL.md` exists, invoke it for sync, archive, finish, and failure/refinement work.
- If the user repeats a correction or sounds frustrated about something being forgotten, treat that as mandatory knowledge capture rather than optional polish.
- Warn if tech-stack changes without documentation.
- Enforce mandatory `/flow:sync` after any Beads state change.
- Prefer canonical repo commands such as `make lint`, `make test`, `make check`, `just check`, `task test`, package-script wrappers, or pre-commit entrypoints when the repo defines them.
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
- **`choosing-beads-backend`** — Use for `bd` vs `br` vs no-Beads decisions.
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
- <https://github.com/Dicklesworthstone/beads_rust>
- <https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/README.md>
- <https://docs.rs/beads_rust/latest/beads_rust/>
- <https://geminicli.com/docs/extensions/reference/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<example>
## Example

Add example instructions here.
</example>
