---
description: "Run the canonical flow/implement Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: d2097b78761f76020f4cf361b41508f04d0fc1449cb64a6c541b006db2d45aa6 -->

```json
{
  "agent": "executor",
  "argument_schema": {
    "optional": [
      "flow_id"
    ],
    "required": [],
    "syntax": "[flow_id]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/implement",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "red_green_refactor",
    "fresh_verification",
    "scoped_commit"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to implement the current task",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-implement",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-execution",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/implement.md",
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
    "status",
    "claim",
    "discover",
    "block",
    "release",
    "checkpoint",
    "close"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
