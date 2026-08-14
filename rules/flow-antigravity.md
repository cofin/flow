---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: 0cfb07f61c8a187c387e268395cd18e23a0a67f5007a8abcda41151e9720fa40 -->
<!-- flow-rule-adapter: {"activation":"Plugin rules load before the Flow router and lifecycle skills.","automatic_push":false,"canonical_sha256":"ca56d471abc7fc69ff5d5d6317035e62f557cb786e07b64c9236917281ee2a25","canonical_source":"rules/flow-core.md","contract_sha256":"d6006f25602084ed88d9af2099cd3bce17bfeabd4cb56eff85c22aa9c8de7b05","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"antigravity","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"ask_question","transport":"conditional_native"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Plugin rules load before the Flow router and lifecycle skills.

When a repository has `.agents/`, read its configured root, bundle index, active
spec, authoritative task worksheet, and applicable recursively nested knowledge
before acting. Operational skills resolve only from `.agents/skills/`.

Route through the `flow` skill and exactly one lifecycle skill. Refine plans
until every worksheet is executable, follow the selected worksheet without
improvising, and route contradictions through revise/refine. Apply explicit,
revision-guarded, recoverable Markdown state operations and reconcile task-first.

Use `structured-choice-v1` for unresolved decisions: one decision at a time,
only through a currently allowed compatible native tool or the equivalent
sequential-text fallback. Run correctness review and then the mandatory fresh
quality review before finish/archive.

Commits and optional Git notes remain local unless the user explicitly asks for
delivery. Never create, move, force-update, or delete Git tags.

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
