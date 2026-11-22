# Flow Decision Interaction

This document defines Flow's structured decision prompts, open-decision discovery, native tool transport, sequential text fallback, and draft approval checks.

<!-- planning-contract: structured-choice -->
```yaml
request:
  exact_keys: [decision_id, selection_mode, question, disabled_choice_policy, choices, recommended_choice_id, allow_custom, min_selections, max_selections, free_form_reason, input_guidance]
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
draft_check:
  before_quality: [revise, refine]
  after_quality: [approve, revise, refine]
```

## 1. Open Decisions & Request Rules

1. **Separate Facts from Decisions**:
   - **Facts** (existing signatures, DI wiring, config keys, test fixtures, framework versions, OKF chapters, user docs) belong to the agent's research duty. Read the repo or dispatch read-only `@researcher` subagents first—never ask what reading the code can answer.
   - **Decisions** (product scope, public interface shape, trade-offs between deep module designs, error semantics, doc targets, risk appetite) belong to the user.
2. **Skip Settled Areas; Walk Unresolved Forks & Batches**:
   - Treat unresolved decisions as a dependency tree, and skip any area already settled by the user's request and repository code.
   - **Dependent Fork (`1` question)**: When downstream choices depend on the answer (such as selecting the deep module interface or storage strategy), ask **1** question and wait for the result before advancing.
   - **Independent Leaf Batch (`2-3` questions)**: Once a branch reaches independent leaf decisions (such as an edge-case error contract, test fixture policy, and doc target), batch **2–3 independent questions** in one multi-question tool call. Fall back to sequential prompts on Codex `request_user_input` when arrays are unsupported.
3. **Pre-Draft Coverage Check**:
   - Before dispatching Chapter Planner subagents or drafting `spec.md`, resolve these five areas (by verified repo facts, user instructions, or targeted questions where ambiguous):
     1. **Deep Module Interface Selection**: Which interface shape won across depth, locality, and adapter count?
     2. **Concrete Data/Type Contracts & Error Semantics**: What exact public structs/types, empty/null/concurrency/timeout boundaries, and error contracts apply?
     3. **Public Interfaces & Canonical Tests**: Which public interfaces and existing module test files verify the task without mocking the module under test?
     4. **Documentation (`README.md` / `docs/**`) & OKF Scope**: Which user-facing docs and `.agents/bundles/knowledge/**` / `.agents/skills/**` chapters are created or updated?
     5. **Feature Decomposition (`spec.md` / `ch01..chNN`)**: Whether a single-chapter `spec.md` covers the feature or staged checkpoints, parallel subsystems, or `empirical_dependent` triggers require `chapters/`.
4. **Request Variant Rules**:
   - Every choice has `{id, label, description}` (`id` matches `[a-z][a-z0-9_-]{0,31}`, `label` is `1-60` chars, `description` is `1-160` chars stating the `path/to/file::Symbol` trade-off).
   - Place the recommended choice **first** in `choices`, set `recommended_choice_id` to its `id`, and display its label with ` (Recommended)`.
   - Omit unavailable or disabled options (`disabled_choice_policy: omit`).
   - Use `open` (`choices: []`, `free_form_reason: user_defined_identifier | revision_details | other_constraint`) **only** when the value cannot be enumerated (such as a custom identifier or free-form `Revise` details). Never use `open` for approval, mode selection, or architectural options.

## 2. Harness Tool Transport & Fallback

Inspect active tool declarations and use the host's native structured-question tool when compatible with the request variant.
Otherwise render the exact same request in numbered Markdown text with each choice label, description, `(Recommended)` marker, and `Other - enter a custom response`:

| Harness | Native Question Tool | Supported Modes & Limits |
| --- | --- | --- |
| **Google Antigravity (IDE & CLI)** | `ask_question` | `binary`, `single_select`, `multi_select` (`2-4` choices, `1-3` independent questions per call, automatic `Other` input; always emit visible context text first) |
| **Claude Code** | `AskUserQuestion` | `binary`, `single_select`, `multi_select` (`2-4` choices, `1-3` independent questions per call, custom `Other` input) |
| **Codex CLI** | `request_user_input` | `binary`, `single_select` (`2-3` choices, `1` question per call, custom input; fallback to sequential text for 4 choices or `multi_select`) |
| **Cursor** | `AskUserQuestion` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2-4` choices, `1-3` independent questions per call) |
| **OpenCode V2** | `question` | `binary`, `single_select`, `multi_select` (`2-4` choices, `1-3` independent questions per call, custom input) |
| **VS Code / Copilot** | `ask_question` / `vscode_askQuestions` (when declared) or sequential text | `binary`, `single_select`, `multi_select` (`2-4` choices, `1-3` independent questions per call) |

Record fallback reasons in order: `tool_absent`, `tool_denied`, `mode_unsupported`, `choice_count_unsupported`, `bounds_unsupported`, `custom_unsupported`, `disabled_policy_unsupported`.

## 3. Result Normalization

- **`selected`**: One selected `id` for `binary`/`single_select`, or an in-bounds list of `selected_choice_ids` (`1 <= min_selections <= len <= max_selections`) for `multi_select`.
- **`custom` / `selected_with_custom`**: Non-blank trimmed `custom_text` entered via `Other`.
- **`submitted`**: Non-blank trimmed `open_text` for `open` requests.
- **`cancelled`**: Stops the loop without approval or file mutation.

## 4. Draft Approval Loop (`Approve | Revise | Refine`)

At every spec or PRD draft checkpoint, use `single_select` and place the recommended action first:

- **Before gap scan and independent review pass**: Offer `Revise | Refine` (`Approve` is omitted until quality checks pass).
- **After gap scan and independent review pass**: Offer `Approve (Recommended) | Revise | Refine`.
  - **`Approve`**: Stamps `status = stable` and `plan_commit = HEAD` across root `spec.md`, any `chapters/<ch_id>/spec.md`, and all `tasks/*.md`, and advances to `/flow:implement`.
  - **`Revise`**: Collects `open(free_form_reason=revision_details)`, rewrites affected chapter and root `spec.md`, `chapters/index.md`, and `tasks/<id>-<slug>.md` in place in present tense ([`revise.md`](revise.md)), increments `plan_revision` once, re-runs independent review, and re-presents the prompt.
  - **`Refine`**: Steps through the next structured gap, edge-case, or chapter-granularity question via [`revise.md`](revise.md), updates and revalidates the worksheets in present tense, and re-presents the prompt.
