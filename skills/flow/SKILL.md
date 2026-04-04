---
name: flow
description: "REQUIRED when .agents/ directory exists. Context-driven dev workflow with Beads integration. Produces spec-first plans, TDD-driven implementations with cross-session memory, and structured phase completions with verification evidence. Auto-activate when: .agents/ directory present; Flow workflow intents such as setup, plan, PRD, design, research, docs, implement, sync, status, refresh, validate, revise, review, finish, archive, revert, or task; any /flow:* command in hosts that support it; editing spec.md or files in .agents/; beads/br commands; TDD workflow; spec-first planning; cross-session memory. Not for standalone code edits outside the .agents/ workflow, simple file changes that don't need spec tracking, or direct tool use that doesn't involve Flow state."
---

# Flow - Context-Driven Development

## Auto-Activation

This skill activates when:

- `.agents/` directory exists in the project root
- User mentions "flow", "spec", "plan", "prd", "design", "research", "docs", "implement", "sync", "status", "refresh", "validate", "revise", "review", "finish", "archive", "revert", or "task"
- User requests a Flow workflow in natural language
- User invokes `/flow:*` commands in hosts that support them

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

### Beads Integration (Required)

Flow requires Beads for persistent cross-session memory:

- Each flow becomes a Beads epic
- Tasks sync bidirectionally
- Notes survive context compaction
- Run `br status` + `br ready` at session start

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

<workflow>

## Task Workflow (TDD) - Beads-First

**See `references/discipline.md` for iron laws, rationalization tables, and red flags.**

1. **Select task** from `br ready` (Beads is source of truth)
2. **Mark in progress**: `br update {id} --status in_progress`
3. **Write failing tests** (Red phase) - MUST confirm failure for right reason
4. **Implement** minimal code to pass (Green phase) - MUST confirm all tests pass
   - If `superpowers:subagent-driven-development` is available, use it for implementation subagent orchestration
5. **Refactor** with test safety — must stay green
6. **Verify coverage** (>80% target)
7. **Commit** with format: `<type>(<scope>): <description>`
8. **Attach git notes** with task summary
9. **Sync to Beads**: `br close {id} --reason "commit: {sha}"`
10. **Sync to markdown**: run `/flow:sync` to update spec.md.

</workflow>

<guardrails>

**CRITICAL:** Never write `[x]`, `[~]`, `[!]`, or `[-]` markers to spec.md manually. Beads is the source of truth — after ANY Beads state change, you MUST run `/flow:sync` to keep spec.md in sync.

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

## Knowledge Flywheel

1. **Capture** - After each task, append learnings to flow's `learnings.md`
2. **Sync** - Auto-sync to Beads notes
3. **Elevate** - At phase/flow completion, move reusable patterns to `patterns.md`
4. **Synthesize** - During sync and archive, integrate learnings directly into cohesive, logically organized knowledge base chapters in `.agents/knowledge/`.
5. **Inherit** - New flows read `patterns.md` + scan `.agents/knowledge/` chapters.

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
7. Record checkpoint in Beads: `br comments add {epic_id} "Phase {N} checkpoint: {sha}"`
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

When Superpowers skills are available, the following protocols MUST be followed:

1. **Brainstorming & Planning Overrides:**
    - All brainstorming sessions (`superpowers:brainstorming`) MUST write their results to `.agents/specs/<flow_id>/spec.md`.
    - All implementation plans (`superpowers:writing-plans`) MUST be written to `.agents/specs/<flow_id>/spec.md`.
    - **NEVER** use `docs/superpowers/` for Flow-related artifacts.
    - If a skill tries to use a default path, you MUST intercept and redirect to `.agents/specs/<flow_id>/`.

2. **Implementation Orchestration:**
    - When running `/flow:implement`, you MUST explicitly recommend the "Subagent-Driven" approach to the user if `superpowers:subagent-driven-development` is available.
    - You MUST use `superpowers:subagent-driven-development` to orchestrate the implementation of tasks.

3. **Self-Review & Quality Gate:**
    - Before finalizing any PRD (`/flow:prd`) or Plan (`/flow:plan`), you MUST invoke `code-reviewer` (or use the internal `Spec Review Loop`) to validate the artifacts against project patterns and requirements.
    - For PRDs, ensure they follow the "Master Roadmap" structure.
    - For Plans, ensure they are "Unified Specs" (Requirements + TDD Tasks).

4. **TDD & Verification:**
    - Always use `superpowers:test-driven-development` for task implementation.
    - Always use `superpowers:verification-before-completion` before closing a task in Beads or marking it complete.

## Proactive Behaviors

When Flow skill is active:

- Check for resume state at session start.
- Run `br status` and `br ready` for context.
- Scan `knowledge/index.md` for relevant past learnings when starting a new flow.
- Prompt for learnings capture after tasks.
- Suggest pattern elevation at phase completion.
- Warn if tech-stack changes without documentation.
- Enforce mandatory `/flow:sync` after any Beads state change.
- **Mandatory Superpowers Integration:** If Superpowers is detected, all workflows (PRD, Plan, Implement) MUST follow the **Superpowers Protocol** above.
- Invoke `flow:apilookup` proactively for external API/docs/version/migration questions.

## References Index

For detailed instructions and directives for specific flow commands, refer to the following documents in `references/`:

- **[Setup](references/setup.md)** - `/flow:setup`
- **[PRD](references/prd.md)** - `/flow:prd`
- **[Plan](references/plan.md)** - `/flow:plan`
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
| writing-plans | `consensus` for architectural decisions, `architecture-critic` for structural quality |

</context>

## Official References

- <https://github.com/cofin/flow>
- <https://raw.githubusercontent.com/cofin/flow/main/README.md>
- <https://github.com/Dicklesworthstone/beads_rust>
- <https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/README.md>
- <https://docs.rs/beads_rust/latest/beads_rust/>
- <https://geminicli.com/docs/extensions/reference/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
