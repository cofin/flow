---
description: "Run the canonical flow/research Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: e2b46dfe3245bffe6c0ee0b950dc050dd4b5a7cfdb37b5618c399a61d67a38d7 -->

```json
{
  "agent": null,
  "argument_schema": {
    "optional": [],
    "required": [
      "topic"
    ],
    "syntax": "<topic>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/research",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "evidence_captured"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to research this topic",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-research",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/research.md",
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
    "note",
    "discover"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
