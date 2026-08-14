---
description: "Run the canonical flow/validate Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: d02399f248bbccb7226c0461084acaa26652336aef6fce941de4cdc727ca6b38 -->

```json
{
  "agent": null,
  "argument_schema": {
    "optional": [
      "scope"
    ],
    "required": [],
    "syntax": "[scope]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/validate",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "validation_passed"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to validate this repository",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-validate",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "read_only",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/validate.md",
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
    "status"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
