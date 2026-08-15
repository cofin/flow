---
description: "Run the canonical flow/prd Flow lifecycle."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 1421557ce176d7f5b2c1362bd823f3c1c37aaab05db6d86a4e31679235a303a1 -->

```json
{
  "agent": "prd-orchestrator",
  "argument_schema": {
    "optional": [],
    "required": [
      "goal"
    ],
    "syntax": "<goal>"
  },
  "bounds_enforcement": "agent_validated",
  "canonical_id": "flow/prd",
  "capability_evidence": "Claude Code declared AskUserQuestion contract",
  "choice_max": 4,
  "choice_min": 2,
  "completion_gates": [
    "research_closed",
    "gap_scan",
    "code_review",
    "user_approval"
  ],
  "custom_answer_behavior": "native_custom_input",
  "disabled_choice_policy": "omit",
  "fallback": "Use Flow to create a PRD",
  "git_tags": "forbidden",
  "host": "claude_code",
  "instruction": "Load the lifecycle owner and follow the canonical procedure source directly.",
  "interaction_mode": "structured_choice",
  "invocation": "/flow-prd",
  "kind": "flow_command_adapter",
  "lifecycle_owner": "flow-planning",
  "multi_select": true,
  "mutability": "planning_write",
  "mutual_exclusion": true,
  "plan_capability": "required",
  "procedure_source": "skills/flow/references/prd.md",
  "question_capability": "structured-choice-v1",
  "question_permission_check": "declared_and_allowed",
  "question_tool": "AskUserQuestion",
  "question_transport": "conditional_native",
  "runtime_dependency": "agent_file_tools_only",
  "sequential_fallback": true,
  "shared_contracts": [
    "flow-state-v1",
    "structured-choice-v1"
  ],
  "state_operations": [
    "create",
    "revise",
    "checkpoint"
  ],
  "supported_selection_modes": [
    "binary",
    "single_select",
    "multi_select"
  ]
}
```
