---
name: researcher
description: "Conduct primary-source technical research across codebases, SDK documentation, and specifications in isolated context."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: af1eb7c89f04c760e65cd4ae25f58c91ca3f462874c60a31470702c51ea3d962 -->

```json
{
  "canonical_id": "researcher",
  "canonical_source": "agents/researcher.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
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
    "file_read"
  ]
}
```
