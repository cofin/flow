---
name: flow-reconciler
description: "Reconcile Flow Markdown state transactions and report a compact status dashboard."
mode: subagent
permission:
  edit: allow
  bash: deny
  webfetch: deny
---

<!-- Generated from contracts/flow.yaml; generated-sha256: ea0262e32b1ad454158bb9e4d8546777a2dc7d736dcda215a9f3915cd266d2b0 -->

```json
{
  "canonical_id": "flow-reconciler",
  "canonical_source": "agents/flow-reconciler.md",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "flow-state-v1",
    "markdown-transaction-v1",
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
    "file_write"
  ]
}
```
