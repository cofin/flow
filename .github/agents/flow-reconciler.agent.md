---
name: flow-reconciler
description: "Reconcile Flow Markdown state transactions and report a compact status dashboard."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 468f71fbacdf328d4de678bc6ad9ebdcd55d733cdb789f0de5de1174d99f4e15 -->

```json
{
  "canonical_id": "flow-reconciler",
  "canonical_source": "agents/flow-reconciler.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "flow-state-v1",
    "markdown-transaction-v1",
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
    "file_write"
  ]
}
```
