# Flow Decision Interaction (`structured-choice-v1`)

This document is the sole procedure authority for Flow's `structured-choice-v1` decision requests, Design-Tree Frontier interviewing ("Grilling"), native tool transport, sequential text fallback, and draft approval gates.

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
  before_quality: [revise, refine]
  after_quality: [approve, revise, refine]
```

## 1. Design-Tree Frontier Discovery ("Grilling") & Request Rules

1. **Separate Facts from Decisions**:
   - **Facts** (existing signatures, DI wiring, config keys, test fixtures, framework versions) belong to the agent's research duty. Read the repository or dispatch `@researcher` first—never ask the user a question that reading the codebase can answer.
   - **Decisions** (product scope, public seam shape, trade-offs between deep-module designs, risk appetite) belong to the user.
2. **Walk the Design Tree in Frontier Rounds**:
   - Treat unresolved decisions as a dependency tree. Identify the current **frontier**—decisions whose prerequisite choices are settled—and ask **one logical decision at a time**, waiting for the normalized result before advancing to dependent branches.
3. **Request Variant Rules**:
   - Every choice has `{id, label, description}` (`id` matches `[a-z][a-z0-9_-]{0,31}`, `label` is `1–60` chars, `description` is `1–160` chars stating the concrete `path/to/file::Symbol` trade-off or impact).
   - Place the recommended choice **first** in `choices`, set `recommended_choice_id` to its `id`, and display its label with the ` (Recommended)` suffix.
   - Omit unavailable or disabled options (`disabled_choice_policy: omit`).
   - Use `open` (`choices: []`, `free_form_reason: user_defined_identifier | revision_details | other_constraint`) **only** when the value cannot be enumerated (such as a custom identifier/path or free-form `Revise` details). Never use `open` for approval, mode selection, or enumerable architectural alternatives.

## 2. Harness Tool Transport & Fallback Matrix

Inspect active tool declarations and use the host's native structured-question tool when declared, allowed, and compatible with the request variant; otherwise render the exact same request sequentially in numbered Markdown text (including each choice label, description, `(Recommended)` marker, and `Other - enter a custom response`):

| Harness | Native Question Tool | Supported Modes & Limits |
| --- | --- | --- |
| **Google Antigravity (IDE & CLI)** | `ask_question` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom `Other` input automatic; always emit visible context text before calling `ask_question`) |
| **Claude Code** | `AskUserQuestion` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom `Other` input) |
| **Codex CLI** | `request_user_input` | `binary`, `single_select` (`2–3` choices, custom input; fallback to sequential text for 4 choices or `multi_select`) |
| **Cursor** | `AskUserQuestion` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices) |
| **OpenCode V2** | `question` | `binary`, `single_select`, `multi_select` (`2–4` choices, custom input) |
| **VS Code / Copilot** | `ask_question` / `vscode_askQuestions` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices) |

Fallback reasons are recorded in canonical order when falling back to sequential text: `tool_absent`, `tool_denied`, `mode_unsupported`, `choice_count_unsupported`, `bounds_unsupported`, `custom_unsupported`, `disabled_policy_unsupported`.

## 3. Result Normalization

- **`selected`**: One selected `id` for `binary`/`single_select`, or an in-bounds list of `selected_choice_ids` (`1 <= min_selections <= len <= max_selections`) for `multi_select`.
- **`custom` / `selected_with_custom`**: Non-blank trimmed `custom_text` entered via the `Other` affordance.
- **`submitted`**: Non-blank trimmed `open_text` for `open` requests.
- **`cancelled`**: Stops the loop immediately without approval or file mutation.

## 4. Draft Approval Loop (`Approve | Revise | Refine`)

At every specification or PRD draft checkpoint, use `single_select` and reorder choices so the contextually recommended action is first:

- **Before deterministic gap scan and Goldfish review pass**: Offer `Revise | Refine` (`Approve` is omitted until quality gates pass).
- **After deterministic gap scan and Goldfish review pass**: Offer `Approve (Recommended) | Revise | Refine`.
  - **`Approve`**: Stamps `plan_commit = HEAD` across `spec.md` and `tasks/*.md` and advances to `/flow:implement`.
  - **`Revise`**: Collects `open(free_form_reason=revision_details)`, rewrites affected `spec.md` and `tasks/<id>-<slug>.md` sections in place in present tense ([`revise.md`](revise.md)), increments `plan_revision` once, re-runs Zero-Context Goldfish Review on the changed surface, and re-presents the gate.
  - **`Refine`**: Steps through the next structured gap or task-granularity question via [`revise.md`](revise.md), updates and revalidates the worksheets, and re-presents the gate.
