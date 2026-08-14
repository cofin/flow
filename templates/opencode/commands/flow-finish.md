---
description: "Run the canonical flow/finish Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 3408ebe0ed54561f172b600ed835e68a3ab2fe24aa673d0bcf88634bd9076a6d -->

```json
{
  "agent": "code-reviewer",
  "argument_schema": {
    "optional": [],
    "required": [
      "flow_id"
    ],
    "syntax": "<flow_id>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/finish",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "verification",
    "code_review",
    "quality_review",
    "finish"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to finish the current flow",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-finish",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/finish.md",
  "question_capability": "structured-choice-v1",
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "structured-choice-v1",
    "quality-review-v1"
  ],
  "state_operations": [
    "checkpoint",
    "complete",
    "archive",
    "note"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
