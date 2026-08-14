---
description: "Run the canonical flow/docs Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: c4287088b6f639c03ec88703309518b269377610e5d09d339508aa8566b450c1 -->

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
  "canonical_id": "flow/docs",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "documentation_validation"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to update documentation",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-docs",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "preferred",
  "procedure_source": "skills/flow/references/docs.md",
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
    "note",
    "checkpoint"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
