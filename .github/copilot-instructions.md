<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: f61b11ed0ae0a183a4161ad2d77fa7dd2025999f959d20c7aed59de76dd52cca -->
<!-- flow-rule-adapter: {"activation":"Repository instructions, custom agents, and Agent Skills activate Flow.","automatic_push":false,"canonical_sha256":"ca56d471abc7fc69ff5d5d6317035e62f557cb786e07b64c9236917281ee2a25","canonical_source":"rules/flow-core.md","contract_sha256":"d6006f25602084ed88d9af2099cd3bce17bfeabd4cb56eff85c22aa9c8de7b05","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"vscode_copilot","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Repository instructions, custom agents, and Agent Skills activate Flow.

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

No native question tool is verified for this host. Render every request sequentially in text and wait for its answer before continuing.

For `binary`, `single_select`, and `multi_select`, show only enabled domain choices (2-4 within the host limit), put the recommended choice first with a space and `(Recommended)`, include each concise description, include multi-select bounds, and finish with `Other - enter a custom response`. For `open`, show only its input guidance and use sequential text. Never invent a tool, argument, mode, slash command, or batch interaction. Before quality, offer only Revise/Refine; after quality, offer Approve/Revise/Refine.
