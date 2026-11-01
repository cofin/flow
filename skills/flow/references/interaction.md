# Flow Decision Interaction (`structured-choice-v1`)

This document is the sole procedure authority for Flow's `structured-choice-v1` decision requests, native tool transport, sequential text fallback, and draft approval gates.

<!-- planning-contract: structured-choice-v1 -->
```yaml
contract_id: structured-choice-v1
request:
  exact_keys: [contract_id, decision_id, selection_mode, question, disabled_choice_policy, choices, recommended_choice_id, allow_custom, min_selections, max_selections, free_form_reason, input_guidance]
  exact_choice_keys: [id, label, description]
  variants:
    binary:
      choice_count: [2, 2]
    single_select:
      choice_count: [2, 4]
    multi_select:
      choice_count: [2, 4]
    open:
      choice_count: [0, 0]
      free_form_reasons: [user_defined_identifier, revision_details, other_constraint]
result:
  exact_keys: [decision_id, selection_mode, outcome, selected_choice_ids, custom_text, open_text, transport, tool_name, fallback_reasons]
  fallback_reason_order: [tool_absent, tool_denied, mode_unsupported, choice_count_unsupported, bounds_unsupported, custom_unsupported, disabled_policy_unsupported]
draft_gate:
  before_quality: [revise]
  after_quality: [approve, revise]
```

## 1. Request Rules

- Ask **one decision at a time** and wait for the user's answer before asking the next question.
- Ground every architectural question in concrete repository evidence (`path/to/file::Symbol`). Never ask the user a question that can be answered by reading the repository.
- Place the recommended choice **first** in `choices`, set `recommended_choice_id` to its `id`, and display its label with the ` (Recommended)` suffix.
- Omit unavailable or disabled options (`disabled_choice_policy: omit`).

## 2. Harness Tool Transport & Fallback Matrix

Inspect active tool declarations and use the host's native structured-question tool when declared, allowed, and compatible with the request variant; otherwise render the same choices sequentially in numbered Markdown text:

| Harness | Native Question Tool | Supported Modes & Limits |
| --- | --- | --- |
| **Google Antigravity (IDE & CLI)** | `ask_question` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom `Other` input automatic) |
| **Claude Code** | `AskUserQuestion` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom `Other` input) |
| **Codex CLI** | `request_user_input` | `binary`, `single_select` (`2–3` choices, custom input) |
| **Cursor** | `AskUserQuestion` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices) |
| **OpenCode V2** | `question` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom input) |
| **VS Code / Copilot** | `ask_question` / `vscode_askQuestions` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices) |

## 3. Draft Approval Gate

After Zero-Context Focused Review and Finding Adjudication (`ADOPT` vs. `CONTEST`) complete:

- Present `Approve (Recommended)` and `Revise` via `single_select`.
- **Approve**: Stamps `plan_commit = HEAD` across `spec.md` and `tasks/*.md` and advances to `/flow:implement`.
- **Revise**: Collects revision details, rewrites affected `spec.md` and `tasks/<id>-<slug>.md` sections in place in present tense ([`revise.md`](revise.md)), increments `plan_revision` once, re-runs Zero-Context Focused Review on the changed surface, and re-presents the gate.
