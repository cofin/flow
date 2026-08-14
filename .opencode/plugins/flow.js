/** Generated from rules/flow-core.md and contracts/flow.yaml. */
// generated-sha256: 2f641c6de16e5d03c295b083788ca43152c0347938af660a89ed0967bd80897b
// flow-rule-adapter:start
const FLOW_RULE_ADAPTER = Object.freeze({"activation":"The system transform and discovered Agent Skills activate Flow.","automatic_push":false,"canonical_sha256":"ca56d471abc7fc69ff5d5d6317035e62f557cb786e07b64c9236917281ee2a25","canonical_source":"rules/flow-core.md","contract_sha256":"d6006f25602084ed88d9af2099cd3bce17bfeabd4cb56eff85c22aa9c8de7b05","contract_source":"contracts/flow.yaml","git_tags":"forbidden","host":"opencode","interaction_contract":{"choice_keys":["id","label","description"],"custom_label":"Other","fallback_reason_order":["tool_absent","tool_denied","mode_unsupported","choice_count_unsupported","bounds_unsupported","custom_unsupported","disabled_policy_unsupported"],"id":"structured-choice-v1","one_decision_at_a_time":true,"post_quality":["approve","revise","refine"],"pre_quality":["revise","refine"],"procedure_source":"skills/flow/references/interaction.md","recommended_choice":"first_with_suffix","recommended_suffix":" (Recommended)"},"kind":"flow_rule_adapter","lifecycle_skills":["flow-setup","flow-planning","flow-execution","flow-sync-status","flow-completion"],"nested_knowledge":true,"question_capability":{"bounds_enforcement":"agent_validated","choice_max":4,"choice_min":2,"custom_answer_behavior":"native_custom_input","disabled_choice_policy":"omit","multi_select":true,"permission_check":"declared_and_allowed","sequential_fallback":true,"supported_modes":["binary","single_select","multi_select"],"tool":"question","transport":"conditional_native"},"rule_id":"flow-operational-v1","rule_revision":1,"shared_contracts":["flow-state-v1","structured-choice-v1","worksheet-execution-v1","quality-review-v1"]});
// flow-rule-adapter:end
const FLOW_RULE_PROMPT = "Flow rule v1 is rules/flow-core.md. When .agents exists, rules precede skills; load the router/lifecycle skill and the journal-first direct-read continuity contract in skills/flow/references/state.md. For structured-choice-v1, inspect allowed tools and use verified question only for compatible binary/single_select/multi_select requests with 2-4 choices, recommended first, Other, omitted disabled choices, and valid bounds; otherwise ask sequentially. Read nested knowledge. Never auto-push or mutate Git tags.";

function isFlowDisabledByManagedConfig(ctx) {
  const managed = ctx?.config?.managedConfig ?? ctx?.config?.managed ?? null;
  if (!managed) return false;
  if (managed.disabledPlugins?.includes('flow')) return true;
  return Boolean(managed.allowedPlugins && !managed.allowedPlugins.includes('flow'));
}

export default async (ctx) => {
  if (isFlowDisabledByManagedConfig(ctx)) return {};

  return {
    'experimental.chat.system.transform': async (_input, output) => {
      output.system.push(FLOW_RULE_PROMPT);
    },
  };
};
