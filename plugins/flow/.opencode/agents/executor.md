---
name: executor
description: "Execute Flow implementation tasks with TDD, task file notes, verification, and sync discipline."
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 7b9c89c8e011a495ee3145e804821eb3bdbe9ba06f59ca405e025fc060fdf2e4 -->

```json
{
  "canonical_id": "executor",
  "canonical_source": "agents/executor.md",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "none",
  "invariant_ids": [
    "worksheet-execution-v1",
    "flow-state-v1",
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
    "file_write",
    "repository_commands"
  ]
}
```
