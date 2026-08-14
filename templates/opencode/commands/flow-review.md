---
description: "Run the canonical flow/review Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: dbac97549bca4b29218c89275bbf68132c9a4673551ee58778c716008848cd31 -->

```json
{
  "agent": "code-reviewer",
  "argument_schema": {
    "optional": [
      "flow_id"
    ],
    "required": [],
    "syntax": "[flow_id]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/review",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "code_review",
    "quality_review"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to review the current flow",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-review",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "state_write",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/review.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "quality-review-v1"
  ],
  "state_operations": [
    "status",
    "note"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
