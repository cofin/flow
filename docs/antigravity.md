# Installing Flow for Antigravity

Flow is a first-class Antigravity plugin. Install it through Antigravity's
native Plugins & Skills installer, then restart Antigravity after installation
or update so the manifest, rule, hook, agents, and skills reload.

## Shipped surfaces

| Asset | Source | Purpose |
|---|---|---|
| Plugin manifest | `plugin.json` | plugin identity and metadata |
| Operational rule | `rules/flow-antigravity.md` | `model_decision` activation and structured-choice view |
| Hook manifest | `hooks/hooks-agy.json` | static `PreInvocation` routing registration |
| Hook emitter | `hooks/agy-pre-invocation.sh` | one bounded fixed JSON envelope |
| Subagents | `agents/*.md` | canonical lifecycle, state, correctness, and quality agents |
| Skills | `skills/**/SKILL.md` | Flow router and lifecycle procedures |

Antigravity has no SessionStart event, so Flow uses `PreInvocation`. The
manifest target emits a fixed instruction to read the configured Flow index and
state contract. It does not scan tasks, read project state, call a helper, or
synthesize a continuation packet. Agents reconstruct continuity directly from
tracked Markdown.

## Structured decisions

Antigravity's verified native question tool is `ask_question`. For every
Flow-normalized binary, single-select, or multi-select decision with 2-4 domain
choices, custom input, omit-disabled behavior, and valid bounds, Flow **must
use** `ask_question` when the tool is declared and allowed.

If `ask_question` is absent, denied, or incompatible with the request, Flow
renders the same `structured-choice-v1` request sequentially in text and waits
for the answer. The fallback preserves the recommended-first choice,
descriptions, multi-select bounds, disabled-choice omission, and `Other` custom
answer. Open input is always sequential text. Flow never invents a tool
argument or batches logical decisions.

## Project authority and state

Operational project skills live only under `.agents/skills/`. Product,
knowledge, research, and specs live under the configured OKF bundle root;
knowledge chapters may be recursively nested. The `flow-reconciler` applies
`flow-state-v1` with ordinary file read/write/edit tools. Consumer state has no
Python, shell, PowerShell, database, daemon, or Flow executable dependency.

## Usage and validation

Antigravity's exact command spellings are the `/flow-*` values in the
[harness conformance matrix](harness-conformance-matrix.md). After correctness
review, finish and archive always require a fresh read-only quality review on
the exact Git range.

Repository maintainers validate the shipped surfaces with:

```bash
make validate
```
