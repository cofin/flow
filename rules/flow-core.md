---
rule_id: flow-operational-v1
revision: 1
shared_contracts:
  - flow-state-v1
  - structured-choice-v1
  - worksheet-execution-v1
  - quality-review-v1
lifecycle_skills:
  - flow-setup
  - flow-planning
  - flow-execution
  - flow-sync-status
  - flow-completion
host_activation:
  antigravity: Plugin rules load before the Flow router and lifecycle skills.
  claude_code: Native skills, hooks, and the instruction hierarchy activate Flow.
  codex_cli: Native skills, hooks, and the instruction hierarchy activate Flow.
  opencode: The system transform and discovered Agent Skills activate Flow.
  cursor: The always-applied repository rule and AGENTS.md activate Flow.
  vscode_copilot: Repository instructions, custom agents, and Agent Skills activate Flow.
  openclaw: Workspace instructions, Agent Skills, and runtime subagents activate Flow.
---

# Flow Operational Rule

When a repository has `.agents/`, read its configured root, bundle index, active
spec, authoritative task worksheet, and applicable recursively nested knowledge
before acting. Operational skills resolve only from `.agents/skills/`.

Route through the `flow` skill and exactly one lifecycle skill. Refine plans
until every worksheet is executable, follow the selected worksheet without
improvising, and route contradictions through revise/refine. Rewrite revised
worksheets in place in present tense without historical transcripts, and keep
Markdown checklist markers (`[x]`, `[~]`, `[ ]`) synchronized with task `state`.
Apply direct Markdown frontmatter state synchronization and reconcile task-first.

Close and archive completed specs on the working branch without waiting for branch
merge; when scope grows beyond the active spec, finish the current spec and open a
follow-up spec via `/flow:plan`. Before deleting any spec during archive,
curate evidence-backed OKF chapters across nested domain, architecture, pattern,
testing, and gotcha folders (`knowledge/index.md`).

Write direct, zero-slop prose and code: avoid AI puffery, negative parallelisms,
formulaic transitions, and inline `#` comments in Python (use docstrings and PEP
585 types). Proactively fix adjacent lint, typing, or dead-code issues in touched
in-scope files and suggest the exact canonical `/flow:<action>` command next.

Use `structured-choice-v1` for unresolved decisions: one decision at a time,
only through a currently allowed compatible native tool or the equivalent
sequential-text fallback. Run correctness review and then the mandatory fresh
quality review before finish/archive.

Commits remain local unless the user explicitly asks for delivery. Never create, move, force-update, or delete Git tags.

## Host activation

- Antigravity evaluates plugin rules before routing to installed skills.
- Claude Code and Codex use native skills, hooks, and their instruction hierarchy.
- OpenCode uses its system transform plus discovered Agent Skills.
- Cursor and VS Code/Copilot use repository instruction surfaces.
- OpenClaw uses workspace instructions, Agent Skills, and runtime subagents; Flow
  does not ship a fabricated static manifest or question tool for it.

## Contract links

- [State operations and recovery](../skills/flow/references/state.md)
- [Structured decisions](../skills/flow/references/interaction.md)
- [Worksheet execution](../skills/flow/references/implement.md)
- [Completion quality](../skills/flow/references/review.md)
- [Lifecycle router](../skills/flow/SKILL.md)
