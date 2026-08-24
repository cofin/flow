---
name: researcher
description: "Conduct primary-source technical research across codebases, SDK documentation, and specifications in isolated context."
mode: subagent
permission:
  edit: deny
  bash: allow
  webfetch: allow
---

<!-- Generated from contracts/flow.yaml; generated-sha256: d6b5f537e7042402bc05ecdd508888fbcbe42807ab26210da79ab0c4b97a8fa7 -->

```json
{
  "canonical_id": "researcher",
  "canonical_source": "agents/researcher.md",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
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
    "file_read"
  ]
}
```
