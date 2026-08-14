---
trigger: model_decision
description: Standard visual rules for rendering interactive GUI dialog modals (ask_question) and sequential question loops whenever any Flow skill or workflow is active.
---

# Flow Antigravity UX Adapter (View Layer)

These operational standards govern the user interface and conversational experience when Flow skills are executed inside the Antigravity or Jetski host environments.

## 1. Native Modal Prompts (`ask_question`)

- **Modal Tool Check:** Whenever a Flow skill needs to gather user choices, single-select decisions, or conduct interactive scaffolding loops, the agent MUST proactively check if the native GUI modal tool `ask_question` is available in its allowed tool declarations.
- **Strict Tool Usage:** If `ask_question` is present, the agent MUST strictly
    use it to render all types of questions (including binary Yes/No decisions
    and multi-option menus) as a native interactive GUI dialog modal, instead of
    outputting raw text-based prompts in the chat stream.
- **Text Fallback:** If `ask_question` is NOT present in the allowed tools (e.g., in pure text-only console environments), the agent MUST fall back to standard formatted text-based choices, following sequential execution barriers (asking questions one at a time).
