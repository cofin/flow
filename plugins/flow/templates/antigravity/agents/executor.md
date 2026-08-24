---
name: executor
description: "Execute Flow implementation tasks with TDD, task file notes, verification, and sync discipline."
subagent: true
mainAgent: false
model: inherit
commandExecutionPolicy: off
---

<!-- Generated from contracts/flow.yaml; generated-sha256: 87a065897b71896d54fd9b9ceadb2749ca85c08936e8ecf7fffbe3c0cdc816d6 -->

```json
{
  "canonical_id": "executor",
  "canonical_source": "agents/executor.md",
  "git_tags": "forbidden",
  "host": "antigravity",
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
    "file_write",
    "repository_commands"
  ]
}
```
