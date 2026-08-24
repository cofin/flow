---
description: "Run the canonical flow/task Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: f5e9486752ddaf9c14eac13ef3c54698db1b4b0adc9e3d6d2056d79541baf37c -->

```json
{
  "agent": "executor",
  "argument_schema": {
    "optional": [],
    "required": [
      "exploration"
    ],
    "syntax": "<exploration>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/task",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "worksheet_complete",
    "evidence_captured"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to create an exploration task",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-task",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/task.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "worksheet-execution-v1"
  ],
  "state_operations": [
    "create",
    "claim",
    "discover",
    "release",
    "close"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
