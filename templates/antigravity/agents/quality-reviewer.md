---
name: quality-reviewer
description: "Review an exact Git range for unnecessary semantic surface and weak tests or gates without editing the repository."
subagent: true
mainAgent: false
model: inherit
commandExecutionPolicy: off
---

<!-- Generated from contracts/flow.yaml; generated-sha256: eb34e2138e7d1a0babfce5cbf3172d0eec590cea65c6cce18267f3dc053899a6 -->

```json
{
  "canonical_id": "quality-reviewer",
  "canonical_source": "agents/quality-reviewer.md",
  "git_tags": "forbidden",
  "host": "antigravity",
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
