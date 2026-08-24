---
description: "Run the canonical flow/revise Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 14bcbbdf4e4340df43ff62b1e2683e9e153b88310cf6cdde44e54d2c0126aec9 -->

```json
{
  "agent": "plan-generator",
  "argument_schema": {
    "optional": [
      "changes"
    ],
    "required": [
      "flow_id"
    ],
    "syntax": "<flow_id> [changes]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/revise",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "gap_scan",
    "code_review",
    "user_approval"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to revise the plan",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-revise",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "required",
  "procedure_source": "skills/flow/references/revise.md",
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
    "discover",
    "block",
    "release",
    "revise",
    "checkpoint"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
