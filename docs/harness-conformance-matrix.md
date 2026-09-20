# Flow Harness Conformance Matrix

This matrix projects the seven host records and every command invocation from
[`contracts/flow.yaml`](../contracts/flow.yaml). The contract is authoritative;
generated adapters and this document must follow it.

## Capability matrix

| Harness ID | Activation | Command surface | Native question tool | Availability check | Supported modes | Domain choices | Custom answer | Sequential fallback | Plan capability | Recovery routing | State sidecar | Quality gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `antigravity` | plugin rule, router skill, lifecycle skill | `skill_derived` | `ask_question` | `declared_and_allowed` | `binary,single_select,multi_select` | `2-4` | `native_custom_input` | `true` | `native` | direct Markdown read; static hook routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `claude_code` | native skills, SessionStart routing, instruction hierarchy | `slash_command` | `AskUserQuestion` | `declared_and_allowed` | `binary,single_select,multi_select` | `2-4` | `native_custom_input` | `true` | `native` | direct Markdown read; static hook routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `codex_cli` | native skills, SessionStart routing, instruction hierarchy | `natural_language` | `request_user_input` | `declared_and_allowed` | `binary,single_select` | `2-3` | `native_custom_input` | `true` | `native` | direct Markdown read; static hook routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `opencode` | static system transform and discovered Agent Skills | `optional_slash_command` | `question` | `declared_and_allowed` | `binary,single_select,multi_select` | `2-4` | `native_custom_input` | `true` | `reasoning_only` | direct Markdown read; static plugin routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `cursor` | always-applied rule and `AGENTS.md` | `natural_language` | `null` | `not_applicable` | `none` | `n/a` | `sequential_text_only` | `true` | `reasoning_only` | direct Markdown read; static rule routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `vscode_copilot` | repository instructions, custom agents, Agent Skills | `natural_language` | `null` | `not_applicable` | `none` | `n/a` | `sequential_text_only` | `true` | `reasoning_only` | direct Markdown read; static instruction routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |
| `openclaw` | workspace instructions, Agent Skills, runtime subagents | `natural_language` | `null` | `not_applicable` | `none` | `n/a` | `sequential_text_only` | `true` | `none` | direct Markdown read; static workspace routing | lifecycle owner via `flow-state` file tools | correctness review, then mandatory fresh quality review |

`structured-choice-v1` always omits disabled choices and asks one logical
decision at a time. A compatible native transport is used only when its named
tool is currently declared and allowed. Absent, denied, or incompatible tools
use the equivalent sequential-text request, including `Other` for structured
modes. Open questions always use sequential text.

Antigravity has one stricter host rule: a Flow-normalized binary, single-select,
or multi-select request within its 2-4 choice capability **must** use allowed
`ask_question`. If that tool is absent or denied, or the request is
incompatible, Flow renders the same tagged request sequentially and waits for
the answer.

## Exact command spellings

| Operation | antigravity | claude_code | codex_cli | opencode | cursor | vscode_copilot | openclaw |
|---|---|---|---|---|---|---|---|
| `flow/setup` | `/flow-setup` | `/flow-setup` | `Use Flow to set up this repository` | `/flow-setup` | `Use Flow to set up this repository` | `Use Flow to set up this repository` | `Use Flow to set up this repository` |
| `flow/prd` | `/flow-prd` | `/flow-prd` | `Use Flow to create a PRD` | `/flow-prd` | `Use Flow to create a PRD` | `Use Flow to create a PRD` | `Use Flow to create a PRD` |
| `flow/plan` | `/flow-plan` | `/flow-plan` | `Use Flow to plan this work` | `/flow-plan` | `Use Flow to plan this work` | `Use Flow to plan this work` | `Use Flow to plan this work` |
| `flow/refine` | `/flow-refine` | `/flow-refine` | `Use Flow to refine the plan` | `/flow-refine` | `Use Flow to refine the plan` | `Use Flow to refine the plan` | `Use Flow to refine the plan` |
| `flow/sync` | `/flow-sync` | `/flow-sync` | `Use Flow to sync task state` | `/flow-sync` | `Use Flow to sync task state` | `Use Flow to sync task state` | `Use Flow to sync task state` |
| `flow/research` | `/flow-research` | `/flow-research` | `Use Flow to research this topic` | `/flow-research` | `Use Flow to research this topic` | `Use Flow to research this topic` | `Use Flow to research this topic` |
| `flow/docs` | `/flow-docs` | `/flow-docs` | `Use Flow to update documentation` | `/flow-docs` | `Use Flow to update documentation` | `Use Flow to update documentation` | `Use Flow to update documentation` |
| `flow/implement` | `/flow-implement` | `/flow-implement` | `Use Flow to implement the current task` | `/flow-implement` | `Use Flow to implement the current task` | `Use Flow to implement the current task` | `Use Flow to implement the current task` |
| `flow/status` | `/flow-status` | `/flow-status` | `Use Flow to report status` | `/flow-status` | `Use Flow to report status` | `Use Flow to report status` | `Use Flow to report status` |
| `flow/revert` | `/flow-revert` | `/flow-revert` | `Use Flow to revert the named target` | `/flow-revert` | `Use Flow to revert the named target` | `Use Flow to revert the named target` | `Use Flow to revert the named target` |
| `flow/validate` | `/flow-validate` | `/flow-validate` | `Use Flow to validate this repository` | `/flow-validate` | `Use Flow to validate this repository` | `Use Flow to validate this repository` | `Use Flow to validate this repository` |
| `flow/revise` | `/flow-revise` | `/flow-revise` | `Use Flow to revise the plan` | `/flow-revise` | `Use Flow to revise the plan` | `Use Flow to revise the plan` | `Use Flow to revise the plan` |
| `flow/archive` | `/flow-archive` | `/flow-archive` | `Use Flow to archive the completed flow` | `/flow-archive` | `Use Flow to archive the completed flow` | `Use Flow to archive the completed flow` | `Use Flow to archive the completed flow` |
| `flow/refresh` | `/flow-refresh` | `/flow-refresh` | `Use Flow to refresh project context` | `/flow-refresh` | `Use Flow to refresh project context` | `Use Flow to refresh project context` | `Use Flow to refresh project context` |
| `flow/task` | `/flow-task` | `/flow-task` | `Use Flow to create an exploration task` | `/flow-task` | `Use Flow to create an exploration task` | `Use Flow to create an exploration task` | `Use Flow to create an exploration task` |
| `flow/finish` | `/flow-finish` | `/flow-finish` | `Use Flow to finish the current flow` | `/flow-finish` | `Use Flow to finish the current flow` | `Use Flow to finish the current flow` | `Use Flow to finish the current flow` |
| `flow/review` | `/flow-review` | `/flow-review` | `Use Flow to review the current flow` | `/flow-review` | `Use Flow to review the current flow` | `Use Flow to review the current flow` | `Use Flow to review the current flow` |
| `flow/cleanup` | `/flow-cleanup` | `/flow-cleanup` | `Use Flow to clean up completed flows` | `/flow-cleanup` | `Use Flow to clean up completed flows` | `Use Flow to clean up completed flows` | `Use Flow to clean up completed flows` |

OpenCode slash commands require the project command templates in
`templates/opencode/commands/` to be installed through a supported project
configuration. Without those templates, use the Flow skill/plugin context in
natural language. Codex plugins do not expose plugin-defined Flow slash
commands; the natural-language spellings above are its public interface.

## Canonical, generated, and packaged boundaries

- Canonical lifecycle and state procedures live in `skills/`; agent sources
  live in `agents/`; the operational rule lives in `rules/flow-core.md`; and
  host semantics live in `contracts/flow.yaml`.
- Host command, agent, and rule adapters are generated. They must not become a
  second procedure authority.
- `plugins/flow/` is regenerated by `make sync-codex-package`. It includes the
  current generated commands, agents, rules, the script-free `flow-state`
  skill, `debloat`, and `skills/flow/references/interaction.md`.
- The package hook payload contains only the Codex hook manifest and its direct
  fixed-envelope SessionStart emitter. Maintainer diagnostics and dynamic
  continuity scanners are not installed.
- Consumers recover by reading tracked Markdown and apply `flow-state-v1`
  through ordinary file tools. No consumer state service or executable is
  required. Operational project skills resolve only from `.agents/skills/`;
  nested knowledge chapters remain supported under the configured knowledge
  root.

## Install, cache, and reload behavior

- Antigravity uses `agy plugin install https://github.com/cofin/flow`. Restart
  after install or update so plugin rules, hooks, agents, and skills reload.
- Claude Code uses `claude plugin marketplace add`, `claude plugin install`,
  `claude plugin marketplace update`, and `claude plugin update`. Updating the
  catalog and the installed plugin are separate steps; run `/reload-plugins`
  or restart afterward.
- Codex uses `codex plugin marketplace add`, then `/plugins` to enable Flow.
  Marketplace state and the installed package cache are distinct; use the
  marketplace upgrade command and restart the session after an update.
- OpenCode project files reload after restarting OpenCode. A global npm install
  remains deferred until Flow publishes an npm plugin; OpenCode caches npm
  packages under `~/.cache/opencode/node_modules/`.
- Cursor consumes Flow's workspace rules, skills, and `.cursor/hooks.json`.
  Native Cursor plugins are supported by the host, but Flow does not yet ship
  `.cursor-plugin/plugin.json`.
- VS Code/Copilot supports workspace agents/skills and native plugin installation
  from a marketplace or Git source. Flow's documented workspace integration does
  not establish that every plugin hook has been tested in Copilot.
- OpenClaw uses runtime skill discovery and `sessions_spawn`; file-backed skill
  changes normally refresh on the next turn, while managed library selections
  stay pinned until explicitly refreshed.

## Native hook contracts and evidence

Reviewed against first-party documentation on 2026-09-20. These are schema and
source checks; Flow's test suite does not launch all seven native applications.

| Harness | Native contract | Flow surface and limitation |
| --- | --- | --- |
| [Antigravity](https://antigravity.google/docs/hooks) | Named root hooks; `PreInvocation` returns `injectSteps` | `hooks.json` and static ephemeral-message emitter; plugin updates require reload/restart |
| [Claude Code](https://code.claude.com/docs/en/hooks) | Nested event matcher groups; `SessionStart` returns `hookSpecificOutput.additionalContext` | `hooks/hooks-claude.json`; omitted matcher and `*` both match all |
| [Codex](https://developers.openai.com/codex/hooks) | Nested event matcher groups; same SessionStart output as Claude; hooks require trust | Canonical `hooks/hooks-codex.json`, generated root and package copies; avoid registering the same hook at multiple scopes |
| [Cursor](https://cursor.com/docs/hooks) | Project `.cursor/hooks.json`; `sessionStart` returns `additional_context` | Workspace manifest runs a dedicated static emitter from the project root |
| [OpenCode](https://opencode.ai/docs/plugins/) | Local or npm JavaScript plugins; native Agent Skills discovery | Static plugin transform; npm packages cached under `~/.cache/opencode/node_modules/` |
| [VS Code/Copilot](https://code.visualstudio.com/docs/agent-customization/agent-plugins) | Workspace customization and native plugins; Claude-format matchers are parsed but currently ignored | Workspace agents/skills; check tool identity inside any future shared policy hook |
| [OpenClaw](https://docs.openclaw.ai/tools/skills) | Runtime skill catalog with file-backed refresh; native subagent sessions | Workspace skills; no Flow plugin manifest |

`tools/sync-hook-surfaces.py` generates native static output envelopes from
`hooks/primer.txt`. It is a development tool, never an installed runtime dependency.
The shell manifests require Bash (including Git Bash on Windows); the native
PowerShell/CMD emitters alone do not establish automatic Windows dispatch.

The package and workspace adapters share a canonical definition, not a runtime
registration: install the plugin once rather than duplicating its hook into each
consumer workspace. Changes to generated outputs must be made at the canonical
source and regenerated explicitly. `make check` checks formatting and generation
without first repairing drift.
