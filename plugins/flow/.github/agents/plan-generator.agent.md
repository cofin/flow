---
name: plan-generator
description: "Generate zero-ambiguity Flow specs and implementation worksheets after codebase analysis."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: ab65f191534192c4235fbb05e3b831afc45c099caf445fca69a573fd31c53ad6 -->

```json
{
  "canonical_id": "plan-generator",
  "canonical_source": "agents/plan-generator.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
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
    "bounds_enforcement": "unsupported",
    "choice_max": null,
    "choice_min": null,
    "custom_answer_behavior": "sequential_text_only",
    "disabled_choice_policy": "omit",
    "evidence": "No verified Flow-native VS Code Copilot question tool",
    "multi_select": false,
    "mutual_exclusion": false,
    "permission_check": "not_applicable",
    "sequential_fallback": true,
    "supported_modes": [],
    "tool": null,
    "transport": "sequential_text"
  },
  "tool_capability_requirements": [
    "file_read",
    "file_write",
    "sequential_choice"
  ]
}
```
