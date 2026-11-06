# Flow Decision Interaction (`structured-choice-v1`)

This document is the sole procedure authority for Flow's `structured-choice-v1` decision requests, Design-Tree Frontier discovery, native tool transport, sequential text fallback, and draft approval gates.

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

## 1. Design-Tree Frontier Discovery & Request Rules

1. **Separate Facts from Decisions**:
   - **Facts** (existing signatures, DI wiring, config keys, test fixtures, framework versions, existing OKF chapters, user docs) belong to the agent's research duty. Read the repository or dispatch read-only Scout / `@researcher` subagents first—never ask the user a question that reading the codebase can answer.
   - **Decisions** (product scope, public seam shape, trade-offs between deep-module designs, boundary error semantics, documentation targets, risk appetite) belong to the user.
2. **Dependent Fork (`1` Question) vs. Orthogonal Frontier Batch (`2–3` Questions per Round)**:
   - Treat unresolved decisions as a dependency tree.
   - **Dependent Fork (`1` question)**: When downstream architectural or behavioral choices depend on the answer (such as selecting the deep-module seam or storage strategy), ask **1** question and wait for the normalized result before advancing to dependent branches.
   - **Orthogonal Frontier Batch (`2–3` questions)**: Once a branch reaches independent leaf decisions whose answers do not invalidate one another (for example, an edge-case failure contract, canonical test fixture policy, and user documentation target), batch **2–3 orthogonal questions** in a single `ask_question` / `AskUserQuestion` / `question` multi-question call so discovery closes high-detail contracts without excessive round-trips (falling back to sequential `1`-at-a-time prompts on Codex `request_user_input` when multi-question arrays are unsupported).
3. **Pre-Draft Question Coverage Gate**:
   - Before dispatching parallel Chapter Planner subagents to author `spec.md` and `tasks/*.md`, verify that all five coverage areas are resolved (either by verified repository facts or explicit user decisions):
     1. **Deep-Module Seam & Interface Alternative Selection**: Which interface shape won across depth, locality, and adapter count?
     2. **Concrete Data/Type Contracts & Edge-Case / Failure Semantics**: What exact public structs/types, empty/null/concurrency/timeout boundaries, and error/exception contracts apply?
     3. **Public Seams & Canonical Test Strategy**: Which confirmed public seams and existing canonical module test files verify the slice without mocking the System Under Test?
     4. **Documentation (`README.md` / `docs/**`) & OKF Knowledge Scope**: Which user-facing docs and `.agents/bundles/knowledge/**` / `.agents/skills/**` chapters are created or updated?
     5. **Full Chapter Decomposition (`ch01..chNN`)**: How is the full scope decomposed into context-bounded chapters (`1–4` vertical-slice tasks per chapter, zero scope truncation, zero upper cap on chapter count), and do any downstream chapters require `planning_status: empirical_dependent`?
4. **Request Variant Rules**:
   - Every choice has `{id, label, description}` (`id` matches `[a-z][a-z0-9_-]{0,31}`, `label` is `1–60` chars, `description` is `1–160` chars stating the concrete `path/to/file::Symbol` trade-off or impact).
   - Place the recommended choice **first** in `choices`, set `recommended_choice_id` to its `id`, and display its label with the ` (Recommended)` suffix.
   - Omit unavailable or disabled options (`disabled_choice_policy: omit`).
   - Use `open` (`choices: []`, `free_form_reason: user_defined_identifier | revision_details | other_constraint`) **only** when the value cannot be enumerated (such as a custom identifier/path or free-form `Revise` details). Never use `open` for approval, mode selection, or enumerable architectural alternatives.

## 2. Harness Tool Transport & Fallback Matrix

Inspect active tool declarations and use the host's native structured-question tool when declared, allowed, and compatible with the request variant; otherwise render the exact same request sequentially in numbered Markdown text (including each choice label, description, `(Recommended)` marker, and `Other - enter a custom response`):

| Harness | Native Question Tool | Supported Modes & Limits |
| --- | --- | --- |
| **Google Antigravity (IDE & CLI)** | `ask_question` | `binary`, `single_select`, `multi_select` (`2–4` choices, `1–3` orthogonal questions per call, custom `Other` input automatic; always emit visible context text before calling `ask_question`) |
| **Claude Code** | `AskUserQuestion` | `binary`, `single_select`, `multi_select` (`2–4` choices, `1–3` orthogonal questions per call, custom `Other` input) |
| **Codex CLI** | `request_user_input` | `binary`, `single_select` (`2–3` choices, `1` question per call, custom input; fallback to sequential text for 4 choices or `multi_select`) |
| **Cursor** | `AskUserQuestion` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices, `1–3` orthogonal questions per call) |
| **OpenCode V2** | `question` | `binary`, `single_select`, `multi_select` (`2–4` choices, `1–3` orthogonal questions per call, custom input) |
| **VS Code / Copilot** | `ask_question` / `vscode_askQuestions` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2–4` choices, `1–3` orthogonal questions per call) |

Fallback reasons are recorded in canonical order when falling back to sequential text: `tool_absent`, `tool_denied`, `mode_unsupported`, `choice_count_unsupported`, `bounds_unsupported`, `custom_unsupported`, `disabled_policy_unsupported`.

## 3. Result Normalization

- **`selected`**: One selected `id` for `binary`/`single_select`, or an in-bounds list of `selected_choice_ids` (`1 <= min_selections <= len <= max_selections`) for `multi_select`.
- **`custom` / `selected_with_custom`**: Non-blank trimmed `custom_text` entered via the `Other` affordance.
- **`submitted`**: Non-blank trimmed `open_text` for `open` requests.
- **`cancelled`**: Stops the loop immediately without approval or file mutation.

## 4. Draft Approval Loop (`Approve | Revise | Refine`)

At every specification or PRD draft checkpoint, use `single_select` and reorder choices so the contextually recommended action is first:

- **Before deterministic gap scan and zero-context review pass**: Offer `Revise | Refine` (`Approve` is omitted until quality gates pass).
- **After deterministic gap scan and zero-context review pass**: Offer `Approve (Recommended) | Revise | Refine`.
  - **`Approve`**: Stamps `status = stable` and `plan_commit = HEAD` across root `spec.md`, any `chapters/<ch_id>/spec.md`, and all `tasks/*.md`, and advances to `/flow:implement`.
  - **`Revise`**: Collects `open(free_form_reason=revision_details)`, rewrites affected chapter and root `spec.md`, `chapters/index.md`, and `tasks/<id>-<slug>.md` sections in place in present tense ([`revise.md`](revise.md)), increments `plan_revision` once, re-runs Zero-Context Review on the changed surface, and re-presents the gate.
  - **`Refine`**: Steps through the next structured gap, edge-case, or chapter-granularity question via [`revise.md`](revise.md), updates and revalidates the blueprints in present tense, and re-presents the gate.
