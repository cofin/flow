---
description: "Run the canonical flow/cleanup Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: f6756bbc608ac70cf1f05b6b6ce7332c186f0fef78e234112349ea7b1f34e06a -->

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
  "canonical_id": "flow/cleanup",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "archive_candidate",
    "verification",
    "code_review",
    "quality_review",
    "archive"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to clean up completed flows",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-cleanup",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-completion",
  "multi_select": true,
  "mutability": "repository_write",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/cleanup.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "AskUserQuestion",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "quality-review-v1"
  ],
  "state_operations": [
    "status",
    "archive",
    "recover"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
