---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

# Flow Operational Rule

When a repository contains `.agents/`, resolve the configured bundle root from `.agents/setup-state.json` (default `.agents/bundles/`), read its `index.md`, active specification (`specs/<flow_id>/spec.md`), authoritative task worksheet (`specs/<flow_id>/tasks/<id>-<slug>.md`), and applicable nested `.agents/bundles/knowledge/` chapters and `.agents/skills/index.md` before acting.

## Lifecycle Routing & Planning Hierarchy

Route work through [the Flow router](../skills/flow/SKILL.md) and the matching lifecycle skill:

- **`flow-setup`** (`/flow:setup`): Bootstrap or migrate `.agents/bundles/`, dynamically synthesize project-local domain and review skills under `.agents/skills/`, and generate paired project-local subagents under `.agents/agents/`.
- **`flow-planning`**:
  - `/flow:prd <goal>`: Multi-flow initiative roadmap (`.agents/bundles/specs/<prd_id>/spec.md`) with locked architectural decisions and ordered `state: draft` child flow charters.
  - `/flow:plan <goal_or_flow_id>`: Single-feature specification (`spec.md`) decomposed into `1–8` disjoint vertical-slice task worksheets (`tasks/<id>-<slug>.md`), reviewed by zero-context focused reviewers and adjudicated (`ADOPT` vs. `CONTEST` with evidence).
  - `/flow:revise <flow_id> [changes]` (alias `/flow:refine`): Rewrite affected `spec.md` and `tasks/<id>-<slug>.md` sections in place in present tense, increment `plan_revision` once, re-run zero-context focused review on the changed surface, and re-anchor `plan_commit = HEAD`.
  - `/flow:research <topic>` (alias `/flow:task`): Primary-source codebase/external research and time-boxed spikes (using untracked `.agents/scratch/<slug>/` for throwaway prototypes) promoted to `research/<topic>_<YYYYMMDD>.md`.
- **`flow-execution`**:
  - `/flow:implement [flow_id] [task_id]`: Execute one approved task worksheet per subagent turn with strategy-appropriate verification against the real System Under Test, atomic commit discipline, and direct Markdown frontmatter + `spec.md` checklist synchronization.
  - `/flow:status`: Report active flows, task states, and next actions directly from `.agents/bundles/specs/*/spec.md` and `tasks/*.md`.
- **`flow-learn`** (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`): Anytime project-wide drift assessment, mid-flow or post-flow knowledge resynthesis (`.agents/bundles/knowledge/**`), active spec/task true-up, and dynamic `.agents/skills/` + `.agents/agents/` synchronization.
- **`flow-docs`** (`/flow:docs`): Write clean user guides, API reference pages (`zensical`, `mkdocstrings`), READMEs, changelogs, signed commits, and pull requests (`## Summary` + `## Key Changes` only, zero slop or internal ceremony).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Zero-context correctness and debloat quality review, PR/release verification, spec contraction into durable OKF knowledge chapters, and archival.
- **`multi-harness-plugins`**: Standards for authoring extension-wide plugins and project-local `.agents/` skills, subagents, hooks, rules, and MCP configs across all supported harnesses.

## Multi-Agent & Dynamic Workflow Orchestration

- Default every subagent invocation (`invoke_subagent`, `run_workflow` `agent(...)`, or host subagent tool) to `model: inherit` unless the user explicitly requests a different model.
- When the `run_workflow` tool is available in the active harness (Google Antigravity), prefer async Python workflow orchestration (`phase()`, `parallel()`, `pipeline()`, `agent(..., schema=..., model="inherit")`, `log()`) for parallel zero-context spec/code review fan-out, persistent multi-turn reviewer verification handles, sequential task worksheet pipelines, and parallel subsystem discovery. Otherwise, dispatch standard isolated subagents (`@code-reviewer`, `@quality-reviewer`, `@researcher`, `@executor`, `@plan-generator`, `@prd-orchestrator`, or project-local `.agents/agents/*`).
- Pass **only disk paths** (`spec.md`, `tasks/*.md`, matching `.agents/skills/`, and `.agents/bundles/knowledge/` chapters) to reviewers—never pass conversational planning transcripts.

## Code, Testing & Git Discipline

- Write direct, zero-slop prose and code (`skills/debloat/SKILL.md`): avoid count-prefixed buzzwords, AI puffery, and inline `#` restatement comments in Python (use Google-style docstrings and PEP 585/604 types).
- Place tests in the existing canonical module test files (never create standalone `test_*remediation*.py` or `test_*audit*.py` files) and test the real System Under Test rather than mocking internal wiring.
- Commits remain local unless the user explicitly asks to push or open a PR. Never create, move, force-update, or delete Git tags.

## Structured Decisions (`structured-choice-v1`)

Present unresolved design decisions one at a time (`skills/flow/references/interaction.md`). Use `ask_question` (Antigravity / VS Code), `AskUserQuestion` (Claude Code / Cursor), `request_user_input` (Codex CLI), or `question` (OpenCode) when declared and allowed for `2–4` choices with the recommended option first (`<Label> (Recommended)`), or fall back cleanly to sequential numbered text prompts.
