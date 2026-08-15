---
name: executor
description: "Execute Flow implementation tasks with TDD, task file notes, verification, and sync discipline."
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 2297358f7b41161f2dfc4b494469dc67f948fe754db92dcf9471827f62c0ff06 -->

```json
{
  "canonical_id": "executor",
  "canonical_source": "agents/executor.md",
  "git_tags": "forbidden",
  "host": "vscode_copilot",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "worksheet-execution-v1",
    "flow-state-v1",
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
    "repository_commands"
  ]
}
```
