# Flow for Claude Code

Use the Flow skill for context-driven development workflows in repos that use `.agents/`.

## Defaults

- Use official Beads (`bd`) when task persistence is needed.
- Default initialization should use stealth mode and a prefix derived from the repo name.
- Prefer `.git/info/exclude` for local-only ignores.
- Use `.gitignore` only when the user explicitly wants a shared repo policy.

## Flow Intent Triggers

Use Flow when the user asks to:

- set up a project
- plan or revise a flow
- research or document a flow
- implement a flow
- sync status or refresh context
- review, finish, archive, or revert a flow

When Flow planning is active:

- route setup work through `flow-setup`, PRD/spec/refine work through `flow-planning`, implementation through `flow-execution`, sync/status through `flow-sync-status`, and review/finish/archive work through `flow-completion`
- automatically use the matching Flow workflow instead of staying in generic chat mode
- keep the workflow in research/planning mode while researching, questioning, drafting, and revising planning artifacts
- refine coarse tasks before implementation so lighter-weight executors do not have to guess
- do not finish PRD/planning while obvious research gaps remain
- revalidate `workflow.md` on existing installs when workflow settings or canonical commands may be stale

When Flow implementation is active:

- load `flow-execution` after the `flow` router skill so the monolithic Flow skill does not carry implementation-only detail into unrelated requests
- read `.agents/workflow.md` and prefer the repo's canonical commands for setup, lint, test, typecheck, and full verification
- preserve context for subagents with `spec.md`, parent PRD context, `patterns.md`, relevant `knowledge/` chapters, `learnings.md`, affected files, and verification requirements
- prefer refined tasks before dispatching lighter-weight agents
- use TDD and verification workflows before claiming completion
- make minimal targeted changes, avoid opportunistic unrelated edits, and never silently descope
- be collaborative when blockers appear; describe them factually and avoid blamey ownership-deflecting language

## Host Notes

- Use `claude plugin marketplace add` and `claude plugin install` for extension lifecycle work.
- Restart the Claude Code session after plugin management operations.
- Flow artifacts belong in `.agents/specs/`, not `docs/superpowers/`.
- Prefer refined tasks before dispatching lighter-weight agents.
