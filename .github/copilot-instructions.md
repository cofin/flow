<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: 21a821d701625e51f27eb36afd8685fc8b585e6f35071df550ebea324d968bcd -->
<!-- flow-rule-adapter: {"activation":"Repository instructions, custom agents, and Agent Skills activate Flow.","automatic_push":false,"canonical_sha256":"8a6c8792d28a246ac1af833e9efab25af3d21c53921ec6512382194bbf4cb46c","canonical_source":"rules/flow-core.md","contract_sha256":"c714548b58c3d404604bf65a542cc986d36e4afbbb464dcd96ffaf836f43d9db","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"vscode_copilot","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Repository instructions, custom agents, and Agent Skills activate Flow.

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

No native question tool is verified for this host. Render every request sequentially in text and wait for its answer before continuing.

For `binary`, `single_select`, and `multi_select`, show only enabled domain choices (2-4 within the host limit), put the recommended choice first with a space and `(Recommended)`, include each concise description, include multi-select bounds, and finish with `Other - enter a custom response`. For `open`, show only its input guidance and use sequential text. Never invent a tool, argument, mode, slash command, or batch interaction. Before quality, offer only Revise/Refine; after quality, offer Approve/Revise/Refine.
