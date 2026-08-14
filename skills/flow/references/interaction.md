# Flow Decision Interaction

This file is the sole procedure authority for Flow's `structured-choice-v1`
request, transport, rendering, and result contract. Planning agents link here
and do not restate or weaken the union.

## Contents

- [Request union](#request-union)
- [Sequencing and transport](#one-decision-sequencing-and-transport)
- [Result union](#result-union)
- [Draft approval loop](#draft-approval-loop)

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

## Request union

Every request has exactly the keys declared above. Unknown keys are invalid.
`contract_id` is `structured-choice-v1`; `decision_id` is non-empty and stable
for the logical decision; `question` asks one decision; and
`disabled_choice_policy` is always `omit`. Unavailable actions are removed
before transport and never rendered as selectable.

Every choice has exactly `{id, label, description}`. Aliases such as
`choice_id`, `reason`, and `impact`, and all unknown keys, are invalid. Choice
`id` values are unique and match `[a-z][a-z0-9_-]{0,31}`. Labels contain 1-60
characters and never store the literal ` (Recommended)` suffix. Descriptions
contain 1-160 characters and state a context-specific reason or impact.

The exact tagged request variants are:

- `binary`: exactly two mutually exclusive domain choices,
  `recommended_choice_id` equal to the first choice id, `allow_custom: true`,
  null `min_selections`, `max_selections`, `free_form_reason`, and
  `input_guidance`.
- `single_select`: two to four mutually exclusive domain choices, the same
  recommendation/custom rules as binary, and null min/max/open fields.
- `multi_select`: two to four independently combinable domain choices, the
  same recommendation/custom rules, null open fields, and integer bounds
  satisfying `1 <= min_selections <= max_selections <= len(choices)`.
- `open`: `choices: []`, `recommended_choice_id: null`,
  `allow_custom: false`, null min/max, one `free_form_reason` from
  `user_defined_identifier|revision_details|other_constraint`, and non-empty
  `input_guidance`.

Custom/Other is a separate affordance and does not count toward a structured
variant's domain-choice limit. Renderers append ` (Recommended)` to the first
choice's displayed label without changing the stored label.

Use `open` only when the value cannot responsibly be enumerated: an exact
user-defined name or path, requested edits after Revise, or an unlisted Other
constraint. For example, `open(user_defined_identifier)` may ask for the exact
package name and `open(revision_details)` may ask what to change. Never use
`open` for approval, mode selection, known architecture alternatives, or known
module lists; those decisions use binary, single-select, or multi-select.

## One-decision sequencing and transport

Ask exactly one logical decision and wait for its normalized result before
asking another. Select native transport only when the named tool is currently
declared and allowed and its verified capability record supports the request's
mode, domain-choice count, selection bounds, custom-answer behavior, and
omit-disabled policy. Otherwise render the exact same request sequentially in
text. Never invent a tool name, argument, feature, slash command, or batched
interaction.

Structured text renders the mode, each choice label and description, the first
choice recommendation, multi bounds when present, and a final
`Other - enter a custom response`. Open text renders only `input_guidance`.

The verified capability records are:

| Host family | Native tool | Verified support |
| --- | --- | --- |
| Antigravity | `ask_question` | binary/single/multi, 2-4 choices, custom input, agent-validated multi bounds, omit-disabled; no open |
| Claude Code | `AskUserQuestion` | binary/single/multi, 2-4 choices, custom input, agent-validated multi bounds, omit-disabled; no open |
| OpenCode | `question` | binary/single/multi, 2-4 choices, custom input, agent-validated multi bounds, omit-disabled; no open |
| Codex | `request_user_input` | binary/single only, 2-3 choices, custom input, omit-disabled; no multi/open |
| Cursor | none | sequential text only |
| VS Code/Copilot | none | sequential text only |
| OpenClaw | none | sequential text only |

Antigravity's normalized structured requests fit its verified record and must
use allowed `ask_question`. Every conditional tool falls back when absent,
denied, or request-incompatible. A tool that becomes unavailable records that
capability failure and falls back; any other tool error stops and surfaces the
diagnostic.

Fallback reasons are unique and use only this order:
`tool_absent`, `tool_denied`, `mode_unsupported`,
`choice_count_unsupported`, `bounds_unsupported`, `custom_unsupported`,
`disabled_policy_unsupported`. Absence and denial are mutually exclusive and
short-circuit compatibility checks. A host with no named tool has
`tool_name: null` and exactly `[tool_absent]`; a missing named tool retains its
name and exactly `[tool_absent]`; a denied tool uses exactly `[tool_denied]`.
For an allowed tool, collect every incompatibility once in canonical order.
Thus Codex handling a four-choice multi-select produces exactly
`[mode_unsupported, choice_count_unsupported, bounds_unsupported]`.

## Result union

Every result has exactly the keys declared above, repeats the request's
`decision_id` and `selection_mode`, and rejects unknown keys. Selected ids are
unique known choice ids ordered as in the request.

- Structured `selected` has one selected id for binary/single or an in-bounds
  non-empty id list for multi; both text fields are null.
- Binary/single `custom` has no selected ids, non-blank Unicode-trimmed
  `custom_text`, and null `open_text`.
- Multi `selected_with_custom` has zero or more selected ids, non-blank
  Unicode-trimmed `custom_text`, and null `open_text`. Other counts as exactly
  one selection, so the total is `len(selected_choice_ids) + 1`. Other-only is
  valid exactly when the bounds contain one; selections already at maximum
  plus Other, blank custom text, below-min, and above-max totals are invalid.
- Open `submitted` has no selected ids, null `custom_text`, and non-blank
  Unicode-trimmed `open_text`.
- Any mode may return `cancelled` with no selected ids and both text fields
  null. Cancellation stops the loop without approval or mutation.

`transport` is `native|sequential_text`. Native has the compatible tool name
and `fallback_reasons: []`. Sequential text has the applicable ordered,
non-empty fallback list and otherwise normalizes identically to native.

## Draft approval loop

At every draft checkpoint use `single_select` and omit disabled actions. Before
the deterministic quality gates pass, offer only `Revise|Refine`. After they
pass, offer exactly `Approve|Revise|Refine`. Reorder the active set so the
contextually recommended action is first; rendering marks that first action as
recommended.

- Approve advances to the next lifecycle gate.
- Revise asks one `open(free_form_reason=revision_details)` follow-up, applies
  the requested edits, updates plan identity when plan-bearing content changed,
  reruns validation/review, and presents a fresh gate.
- Refine asks the next unresolved structured gap, applies the answer, updates
  and revalidates the artifacts, and presents a fresh gate.

Repeat until valid approval, explicit cancellation, or the planning review
limit blocks Ready. Never persist an unapproved crucial artifact as approved.
