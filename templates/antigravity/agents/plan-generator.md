---
name: plan-generator
description: "Generate zero-ambiguity Flow specs and implementation worksheets after codebase analysis."
subagent: true
mainAgent: false
model: inherit
commandExecutionPolicy: off
---

<!-- Generated from contracts/flow.yaml; generated-sha256: f88bef067117582f5ab4a1092214bd2d0d159c031e8cade03f4e50ccfcd18598 -->

```json
{
  "canonical_id": "plan-generator",
  "canonical_source": "agents/plan-generator.md",
  "git_tags": "forbidden",
  "host": "antigravity",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "structured_choice_optional",
  "invariant_ids": [
    "flow-state-v1",
    "structured-choice-v1",
    "planning-convergence-v1",
    "git-no-tags-v1"
  ],
  "kind": "flow_agent_adapter",
  "question_capability": {
    "bounds_enforcement": "agent_validated",
    "choice_max": 4,
    "choice_min": 2,
    "custom_answer_behavior": "native_custom_input",
    "disabled_choice_policy": "omit",
    "evidence": "Antigravity allowed-tool contract for ask_question",
    "multi_select": true,
    "mutual_exclusion": true,
    "permission_check": "declared_and_allowed",
    "sequential_fallback": true,
    "supported_modes": [
      "binary",
      "single_select",
      "multi_select"
    ],
    "tool": "ask_question",
    "transport": "conditional_native"
  },
  "tool_capability_requirements": [
    "file_read",
    "file_write",
    "structured_choice"
  ]
}
```
