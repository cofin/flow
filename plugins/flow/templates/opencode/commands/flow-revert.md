---
description: "Run the canonical flow/revert Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 8d6235adc5c827bcedd6532d23417825979327cf2f0279e6eed4121ffdcc8aea -->

```json
{
  "agent": null,
  "argument_schema": {
    "optional": [],
    "required": [
      "target"
    ],
    "syntax": "<target>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/revert",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "explicit_scope",
    "post_revert_validation"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to revert the named target",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-revert",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/revert.md",
  "question_capability": "structured-choice-v1",
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "structured-choice-v1"
  ],
  "state_operations": [
    "reopen",
    "revise",
    "reconcile"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
