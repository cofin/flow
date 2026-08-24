---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: 99cd88fb052c3d17615ab58b161a90de7b0777d219ea85299be64e47bd0d19ff -->
<!-- flow-rule-adapter: {"activation":"Plugin rules load before the Flow router and lifecycle skills.","automatic_push":false,"canonical_sha256":"640298521fd9c87d05b13a69ec34ee52776f8da5277eac730adc795732ffeca7","canonical_source":"rules/flow-core.md","contract_sha256":"520b894b8565188fdb41764a029616802826bddb744acfa9a63b4ad6a4b1d106","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"antigravity","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"ask_question","transport":"conditional_native"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Plugin rules load before the Flow router and lifecycle skills.

When a repository has `.agents/`, read its configured root, bundle index, active
spec, authoritative task worksheet, and applicable recursively nested knowledge
before acting. Operational skills resolve only from `.agents/skills/`.

Route through the `flow` skill and exactly one lifecycle skill. Refine plans
until every worksheet is executable, follow the selected worksheet without
improvising, and route contradictions through revise/refine. Apply direct Markdown
frontmatter state synchronization and reconcile task-first.

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
