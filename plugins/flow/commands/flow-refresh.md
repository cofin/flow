---
description: "Run the canonical flow/refresh Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: ab1ad662aa8515ffc7b2329b778a951728110f95908292cc18100ec080236b5f -->

```json
{
  "agent": null,
  "argument_schema": {
    "optional": [
      "flow_id"
    ],
    "required": [],
    "syntax": "[flow_id]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/refresh",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "drift_inventory",
    "transaction_reread"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to refresh project context",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-refresh",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-sync-status",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/refresh.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "AskUserQuestion",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1"
  ],
  "state_operations": [
    "status",
    "recover",
    "discover",
    "release",
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
