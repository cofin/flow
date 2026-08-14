---
description: "Run the canonical flow/refine Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 99fc249d64c3077c0862ebd491416d705b1c64741d67a25831c88f66bc9d6637 -->

```json
{
  "agent": "plan-generator",
  "argument_schema": {
    "optional": [],
    "required": [
      "flow_id"
    ],
    "syntax": "<flow_id>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/refine",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "gap_scan",
    "code_review",
    "user_approval"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to refine the plan",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-refine",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "required",
  "procedure_source": "skills/flow/references/refine.md",
  "question_capability": "structured-choice-v1",
  "question_permission_check": "declared_and_allowed",
  "question_tool": "AskUserQuestion",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "structured-choice-v1"
  ],
  "state_operations": [
    "discover",
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
