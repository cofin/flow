---
description: "Run the canonical flow/status Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 8df297847fc6a2ac6d4788107babdd2359f1c645265ba8c447d1b1614e3465b2 -->

```json
{
  "agent": "flow-reconciler",
  "argument_schema": {
    "optional": [
      "flow_id"
    ],
    "required": [],
    "syntax": "[flow_id]"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/status",
  "capability_evidence": "OpenCode built-in question tool documentation",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "direct_markdown_read"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to report status",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "none",
  "invocation": "/flow-status",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-sync-status",
  "multi_select": true,
  "mutability": "read_only",
  "mutual_exclusion": true,
  "plan_capability": "none",
  "procedure_source": "skills/flow/references/status.md",
  "question_capability": null,
  "question_permission_check": "declared_and_allowed",
  "question_tool": "question",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1"
  ],
  "state_operations": [
    "status"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
