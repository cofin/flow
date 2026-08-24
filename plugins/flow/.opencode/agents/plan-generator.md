---
name: plan-generator
description: "Generate zero-ambiguity Flow specs and implementation worksheets after codebase analysis."
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

<!-- Generated from contracts/flow.yaml; generated-sha256: a749137cc55dfa0fcc1aeb1455857bf7531c2fbc604386e551287c9249b0abac -->

```json
{
  "canonical_id": "plan-generator",
  "canonical_source": "agents/plan-generator.md",
  "git_tags": "forbidden",
  "host": "opencode",
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
    "evidence": "OpenCode built-in question tool documentation",
    "multi_select": true,
    "mutual_exclusion": true,
    "permission_check": "declared_and_allowed",
    "sequential_fallback": true,
    "supported_modes": [
      "binary",
      "single_select",
      "multi_select"
    ],
    "tool": "question",
    "transport": "conditional_native"
  },
  "tool_capability_requirements": [
    "file_read",
    "file_write",
    "structured_choice"
  ]
}
```
