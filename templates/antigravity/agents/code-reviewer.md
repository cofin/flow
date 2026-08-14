---
name: code-reviewer
description: "Review Flow specs, plans, and implementation changes for correctness, risk, and missing verification."
subagent: true
mainAgent: false
model: inherit
commandExecutionPolicy: off
---

<!-- Generated from contracts/flow.yaml; generated-sha256: f9e0f3e84f721c4c024fc81e56b5dcd68bb2d0a5e1f74c5bfbeaac098d3d61d4 -->

```json
{
  "canonical_id": "code-reviewer",
  "canonical_source": "agents/code-reviewer.md",
  "git_tags": "forbidden",
  "host": "antigravity",
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
    "repository_diff"
  ]
}
```
