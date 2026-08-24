---
name: code-reviewer
description: "Review Flow specs, plans, and implementation changes for correctness, risk, and missing verification."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 3e3842e243213c7070f8add53cce9f5e06e9ebfc9b85510a9b1f223147ceb719 -->

```json
{
  "canonical_id": "code-reviewer",
  "canonical_source": "agents/code-reviewer.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "review-findings-v1",
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
    "repository_diff"
  ]
}
```
