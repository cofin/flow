---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

# Flow Operational Rule

When a repository contains `.agents/`, resolve the configured bundle root from `.agents/setup-state.json` (default `.agents/bundles/`), read its `index.md`, active specification (`specs/<flow_id>/spec.md`), active chapter (`specs/<flow_id>/chapters/<ch_id>/spec.md` when `has_chapters: true`), authoritative task worksheet (`tasks/<id>-<slug>.md`), and applicable nested `.agents/bundles/knowledge/` chapters and `.agents/skills/index.md` before acting.

## Lifecycle Routing & Chaptered Hierarchy

Route work through [the Flow router](../skills/flow/SKILL.md) and the matching lifecycle skill:

- **`flow-setup`** (`/flow:setup`): Bootstrap or migrate `.agents/bundles/`, dynamically synthesize project-local domain and review skills under `.agents/skills/`, and generate paired project-local subagents under `.agents/agents/`.
- **`flow-planning`**:
  - `/flow:prd <goal>` & `/flow:plan <goal_or_flow_id>`: Keep the coordinator thin (`< 25k` exploration tokens) by fanning out read-only `SubsystemDigest` scouts. Whenever work exceeds `4` tasks or crosses `>= 2` module boundaries, decompose into `specs/<flow_id>/spec.md` (full-plan roadmap), frontmatter-free `specs/<flow_id>/chapters/index.md`, and `specs/<flow_id>/chapters/ch01-<slug>/..chNN-<slug>/{spec.md,tasks/*.md}` (`1–4` vertical-slice tasks per chapter, zero upper cap on chapter count), authoring **all chapters and 8-section task blueprints upfront in parallel Chapter Planner subagents** without truncating engineering or documentation detail.
  - `/flow:revise <flow_id> [chapter_id] [changes]` (alias `/flow:refine`): Rewrite affected chapter blueprints AND root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense (current state, remaining chapters, and full plan—zero revision history inside specs), re-run zero-context review, and re-anchor `plan_commit = HEAD`.
  - `/flow:research <topic>` (alias `/flow:task`): Primary-source codebase/external research and time-boxed `.agents/scratch/<slug>/` spikes promoted to OKF v0.2 `research/<topic>_<YYYYMMDD>.md`.
- **`flow-execution`**:
  - `/flow:implement [flow_id] [chapter_id]`: Execute strictly **one chapter** (`1–4` tasks) per invocation via isolated per-task `@executor` subagents, then sync affected `.agents/bundles/knowledge/**`, `docs/**`, `chapters/index.md`, and root `specs/<flow_id>/spec.md` in present tense, pass Zero-Context Chapter Code & Markdown-Sync Review (`@code-reviewer` + `@quality-reviewer`), stamp `last_reviewed_commit`, and stop cleanly at the chapter boundary.
  - `/flow:status`: Report active flows, completed vs. remaining chapters across the full plan, `empirical_dependent` triggers, and ready tasks.
- **`flow-learn`** (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`): Anytime project-wide drift assessment, subagent-sharded OKF v0.2 knowledge resynthesis (`.agents/bundles/knowledge/**`), present-tense roadmap projection, and dynamic `.agents/skills/` + `.agents/agents/` synchronization.
- **`flow-docs`** (`/flow:docs`): Write clean user guides, module and API documentation, READMEs, agent context files, changelogs, signed commits, and pull requests (`## Summary` + `## Key Changes` only, zero slop, zero historical layering, and zero internal ceremony).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Zero-context correctness, Markdown-sync, and debloat quality review, release gate verification, spec contraction into durable OKF knowledge chapters, and archival.
- **`multi-harness-plugins`**: Standards for authoring extension-wide plugins and project-local `.agents/` skills, subagents, hooks, rules, and MCP configs across all supported harnesses.

## Multi-Agent & Dynamic Workflow Orchestration

- Default every subagent invocation (`invoke_subagent`, `run_workflow` `agent(...)`, or host subagent tool) to `model: inherit` unless the user explicitly requests a different model.
- **Google Antigravity Full-Capability Subagent Dispatch**: On Google Antigravity, always pass `type_name="self"` (`TypeName="self"`, `model="inherit"`) in `run_workflow` `agent(...)` and `invoke_subagent(...)` calls, supplying the on-disk `agents/<role>.md` (or `.agents/agents/<domain>-*.md`) path in the brief so subagents inherit full file, shell, search, and MCP tools; verify `git status --porcelain` is unchanged after read-only scout and review dispatches.
- When `run_workflow` is available, use `phase()`, `parallel()`, and `pipeline()` for sharded `SubsystemDigest` scouts, upfront parallel Chapter Planner subagents, per-chapter zero-context reviews with persistent multi-turn handles, sequential single-chapter task pipelines, and sharded OKF/documentation synthesis.
- Pass **only disk paths** (`spec.md`, `chapters/`, `tasks/*.md`, matching `.agents/skills/`, and `.agents/bundles/knowledge/` chapters) to reviewers—never pass conversational planning transcripts.

## Code, Living Markdown, Testing & Git Discipline

- Keep all living Markdown (`specs/**`, `knowledge/**`, `README.md`, `docs/**`) synchronized in present tense with current verified state, remaining chapters, and the full plan; record chronological history solely in `.agents/bundles/log.md` and Git commits.
- Write direct, zero-slop prose and code (`skills/debloat/SKILL.md`): avoid count-prefixed buzzwords, AI puffery, standalone `---` body rules in OKF bundles, and inline `#` restatement comments in Python (use Google-style docstrings and PEP 585/604 types).
- Place parameterized tests in existing canonical module test files (never create standalone `test_*remediation*.py` or `test_*audit*.py` files) and test the real System Under Test rather than mocking internal wiring.
- Commits remain local unless the user explicitly asks to push or open a PR. Never create, move, force-update, or delete Git tags.

## Structured Decisions (`structured-choice-v1`)

Ask `1` question at a time for dependent architectural forks, and batch `2–3` orthogonal leaf questions per round once on a settled frontier (`skills/flow/references/interaction.md`). Use `ask_question` (Antigravity / VS Code), `AskUserQuestion` (Claude Code / Cursor), `request_user_input` (Codex CLI, sequential `1`-question fallback when needed), or `question` (OpenCode) with `2–4` choices and the recommended option first (`<Label> (Recommended)`).
