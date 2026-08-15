---
name: prd-orchestrator
description: "Analyze broad goals and produce Flow PRD roadmaps with implementation-ready child flows."
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

<!-- Generated from contracts/flow.yaml; generated-sha256: c2e5ea8a08905cb31cdf4b750627af4d6d03aa9b49af5b1e7b7da122e2b99340 -->

```json
{
  "canonical_id": "prd-orchestrator",
  "canonical_source": "agents/prd-orchestrator.md",
  "git_tags": "forbidden",
  "host": "opencode",
  "instruction": "Read and follow the canonical agent source directly.",
  "interaction_requirement": "structured_choice_optional",
  "invariant_ids": [
    "flow-state-v1",
    "structured-choice-v1",
    "planning-convergence-v1",
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
    "structured_choice"
  ]
}
```
