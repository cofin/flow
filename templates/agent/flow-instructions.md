<!-- Generated from rules/flow-core.md and contracts/flow.yaml; generated-sha256: 19a49556de7c3bb38553ea8d030eb8c4f17cad802d87ac3faa23cd8ae37ca19e -->
<!-- flow-rule-adapter: {"activation":"Use the supported host instruction surface and then native Flow skills.","automatic_push":false,"canonical_sha256":"8a6c8792d28a246ac1af833e9efab25af3d21c53921ec6512382194bbf4cb46c","canonical_source":"rules/flow-core.md","contract_sha256":"c714548b58c3d404604bf65a542cc986d36e4afbbb464dcd96ffaf836f43d9db","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"cross_harness","host_activation":{"antigravity":"Plugin rules load before the Flow router and lifecycle skills.","claude_code":"Native skills, hooks, and the instruction hierarchy activate Flow.","codex_cli":"Native skills, hooks, and the instruction hierarchy activate Flow.","cursor":"The always-applied repository rule and AGENTS.md activate Flow.","openclaw":"Workspace instructions, Agent Skills, and runtime subagents activate Flow.","opencode":"The system transform and discovered Agent Skills activate Flow.","vscode_copilot":"Repository instructions, custom agents, and Agent Skills activate Flow."},"host_capabilities":{"antigravity":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"ask_question","transport":"conditional_native"},"claude_code":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"AskUserQuestion","transport":"conditional_native"},"codex_cli":{"bounds_enforcement":"unsupported","choice_max":3,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":false,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select"],"tool":"request_user_input","transport":"conditional_native"},"cursor":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"},"openclaw":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"},"opencode":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"question","transport":"conditional_native"},"vscode_copilot":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"}},"interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"unsupported","choice_max":null,"choice_min":null,"custom_answer_behavior":"sequential_text_only","disabled_choice_policy":"omit","multi_select":false,"permission_check":"not_applicable","sequential_fallback":true,"supported_modes":[],"tool":null,"transport":"sequential_text"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]} -->

# Flow Operational Rule

Activation: Use the supported host instruction surface and then native Flow skills.

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

- [State operations and recovery](../../skills/flow/references/state.md)
- [Structured decisions](../../skills/flow/references/interaction.md)
- [Worksheet execution](../../skills/flow/references/implement.md)
- [Completion quality](../../skills/flow/references/review.md)
- [Lifecycle router](../../skills/flow/SKILL.md)

## Structured decision transport

- `antigravity`: Plugin rules load before the Flow router and lifecycle skills. conditionally use `ask_question` for binary, single_select, multi_select with 2-4 choices; fall back sequentially when absent, denied, or incompatible.
- `claude_code`: Native skills, hooks, and the instruction hierarchy activate Flow. conditionally use `AskUserQuestion` for binary, single_select, multi_select with 2-4 choices; fall back sequentially when absent, denied, or incompatible.
- `codex_cli`: Native skills, hooks, and the instruction hierarchy activate Flow. conditionally use `request_user_input` for binary, single_select with 2-3 choices; fall back sequentially when absent, denied, or incompatible.
- `opencode`: The system transform and discovered Agent Skills activate Flow. conditionally use `question` for binary, single_select, multi_select with 2-4 choices; fall back sequentially when absent, denied, or incompatible.
- `cursor`: The always-applied repository rule and AGENTS.md activate Flow. sequential text only; no verified native question tool.
- `vscode_copilot`: Repository instructions, custom agents, and Agent Skills activate Flow. sequential text only; no verified native question tool.
- `openclaw`: Workspace instructions, Agent Skills, and runtime subagents activate Flow. sequential text only; no verified native question tool.

Every renderer preserves omit-disabled, recommended-first `(Recommended)`, concise descriptions, custom/Other, zero-choice open input, selection bounds, and the pre/post-quality action sets from `structured-choice-v1`. Ask and await one decision at a time.
