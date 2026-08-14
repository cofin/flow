---
description: "Run the canonical flow/sync Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: d58f235e5978ab2bbb18ecd85849387d8e3f474618363e5552a5fd6c0c124459 -->

```json
{
  "agent": "flow-reconciler",
  "argument_schema": {
    "optional": [
      "flow_id"
    ],
    "required": [],
    "syntax": "[flow_id]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/sync",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "transaction_reread"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to sync task state",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-sync",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-sync-status",
  "multi_select": true,
  "mutability": "state_write",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/sync.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1"
  ],
  "state_operations": [
    "reconcile"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
