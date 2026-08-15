---
name: quality-reviewer
description: "Review an exact Git range for unnecessary semantic surface and weak tests or gates without editing the repository."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 5e932ab7f8b41f7bbf251231fc2526a6e636cd3a12ace7755d0e5dcffbb82c1f -->

```json
{
  "canonical_id": "quality-reviewer",
  "canonical_source": "agents/quality-reviewer.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "quality-review-mandatory-v1",
    "quality-review-read-only-v1",
    "quality-findings-evidence-v1",
    "quality-behavior-preservation-v1",
    "quality-test-gate-debloat-v1",
    "quality-review-range-v1",
    "quality-no-opportunism-v1",
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
