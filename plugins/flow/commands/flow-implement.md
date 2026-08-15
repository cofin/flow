---
description: "Run the canonical flow/implement Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 43dbec7e875e71ba01de722650b0f7d4f21207b54ec69b47636fa3e8eea01caa -->

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
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
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
  "host": "claude_code",
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
  "question_tool": "AskUserQuestion",
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
