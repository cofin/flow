---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: 1ecfac7b24c07241e5f74ac4250f4c34ef5e7296938ce402376d0d9b45b3326b -->
<!-- flow-rule-adapter: {"activation":"Plugin rules load before the Flow router and lifecycle skills.","automatic_push":false,"canonical_sha256":"8a6c8792d28a246ac1af833e9efab25af3d21c53921ec6512382194bbf4cb46c","canonical_source":"rules/flow-core.md","contract_sha256":"c714548b58c3d404604bf65a542cc986d36e4afbbb464dcd96ffaf836f43d9db","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"antigravity","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"ask_question","transport":"conditional_native"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Plugin rules load before the Flow router and lifecycle skills.

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

## Structured decision view

Inspect current tool declarations and permission before asking. MUST use `ask_question` only when it is declared, allowed, and compatible with modes binary, single_select, multi_select, 2-4 domain choices, custom input, omit-disabled, and any required agent-validated bounds. If absent, denied, or incompatible, render the same request sequentially in text and wait for its answer. Stop and surface any other tool error.

For `binary`, `single_select`, and `multi_select`, show only enabled domain choices (2-4 within the host limit), put the recommended choice first with a space and `(Recommended)`, include each concise description, include multi-select bounds, and finish with `Other - enter a custom response`. For `open`, show only its input guidance and use sequential text. Never invent a tool, argument, mode, slash command, or batch interaction. Before quality, offer only Revise/Refine; after quality, offer Approve/Revise/Refine.
