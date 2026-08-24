---
description: "Run the canonical flow/setup Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 7e72c43a87c8b5d30b3e0f299e341175259030523ee8e1e537da2a114433eeed -->

```json
{
  "agent": null,
  "argument_schema": {
    "optional": [
      "goal"
    ],
    "required": [],
    "syntax": "[goal]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/setup",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "setup_validation",
    "migration_integrity"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to set up this repository",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-setup",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-setup",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/setup.md",
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
    "create",
    "activate",
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
