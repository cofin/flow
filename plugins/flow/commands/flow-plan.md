---
description: "Run the canonical flow/plan Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 41c81a85f717c297a578e9ed648805bbee2c886bd12e175f929fd0cf456f4750 -->

```json
{
  "agent": "plan-generator",
  "argument_schema": {
    "optional": [],
    "required": [
      "goal"
    ],
    "syntax": "<goal>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/plan",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "research_closed",
    "gap_scan",
    "code_review",
    "user_approval"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to plan this work",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-plan",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "required",
  "procedure_source": "skills/flow/references/plan.md",
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
    "create",
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
