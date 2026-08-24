---
name: code-reviewer
description: "Review Flow specs, plans, and implementation changes for correctness, risk, and missing verification."
mode: subagent
permission:
  edit: deny
  bash: allow
  webfetch: allow
---

<!-- Generated from contracts/flow.yaml; generated-sha256: ccea9f6ab204454cbbab5fc4b7b7c5baf6d51a23df7f2d2cadb3e020a8b9acb6 -->

```json
{
  "canonical_id": "code-reviewer",
  "canonical_source": "agents/code-reviewer.md",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "review-findings-v1",
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
    "repository_diff"
  ]
}
```
