---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

# Flow Operational Rule

When a repository (or its primary Git worktree) contains `.agents/`, resolve the configured bundle root from `.agents/setup-state.json` (default `.agents/bundles/`): inside a linked `git worktree`, reuse the symlinked `.venv` (`uv run --no-sync`, skipping `make install`), work in the worktree's `.agents/` when `ignore_policy` is `shared`, and work in the primary checkout's `.agents/` when `ignore_policy` is `local-only`. Read `index.md`, the active specification (`specs/<flow_id>/spec.md`), active chapter (`specs/<flow_id>/chapters/<ch_id>/spec.md` when `has_chapters: true`), task worksheets (`tasks/<id>-<slug>.md`), and applicable `.agents/bundles/knowledge/` chapters before acting.

## Lifecycle Routing & Proportional Scaling

Route work through [the Flow router](../skills/flow/SKILL.md) and the matching lifecycle skill:

- **`flow-setup`** (`/flow:setup`): Bootstrap or align `.agents/bundles/`, configure `ignore_policy` (`shared` vs. `local-only` with worktree guidance) and `model_routing`, and synthesize `.agents/skills/` + `.agents/agents/`.
- **`flow-planning`**:
  - `/flow:prd <goal>` & `/flow:spec <goal_or_flow_id>` (alias `/flow:plan`): Scale layout to change size (`Small` `<= 400` LOC single-module &rarr; coordinator writes single-chapter `spec.md` + `compact` worksheets directly; `Medium` `<= 1,500` LOC / `<= 3` modules &rarr; `chapters/index.md` + `<= 4` chapters via `flow-spec-planning` and `1` combined reviewer; `Large` / `/flow:prd` &rarr; parallel per-chapter planners without truncating scope or docs). Validate OKF v0.2 writes immediately via `/flow:validate` and warn explicitly whenever `planning_quality: degraded` indicates planning fell back from the primary frontier thinking model.
  - `/flow:revise <flow_id> [chapter_id] [changes]` (alias `/flow:refine`): Rewrite affected chapter blueprints AND root `specs/<flow_id>/spec.md` + `chapters/index.md` in place in present tense, validate OKF, re-run zero-context review on changed chapters, and re-anchor `plan_commit = HEAD`.
  - `/flow:research <topic>` (alias `/flow:task`): Primary-source research and time-boxed `.agents/scratch/<slug>/` spikes promoted to OKF v0.2 `research/<topic>_<YYYYMMDD>.md`.
- **`flow-execution`**:
  - `/flow:implement [flow_id] [chapter_id]`: Execute strictly **one chapter** (`1..4` tasks) per invocation using **Chapter-Batch Execution** (`flow-chapter-pipeline`), editing shared files once across the chapter, validating **once** with the Fast Chapter Gate (`< 60s`: `make lint` + targeted unit test file, skipping slow `> 60s` full test suites mid-flow), committing code/tests first to capture `<CODE_SHA>`, syncing present-tense OKF/docs + checklists, passing Zero-Context Chapter Review, stamping `last_reviewed_commit`, and stopping cleanly at the chapter boundary.
  - `/flow:status`: Report active flows, `planning_quality` warnings, completed vs. remaining chapters, `empirical_dependent` triggers, and ready tasks.
- **`flow-learn`** (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`): Anytime drift assessment, worktree reorientation, OKF v0.2 knowledge resynthesis, and `.agents/skills/` + `.agents/agents/` sync.
- **`flow-docs`** (`/flow:docs`): User guides, module/API docs, READMEs, changelogs, signed commits, and clean pull requests (`## Summary` + `## Key Changes` only).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Zero-context review, single full-release-gate run at `/flow:finish`, anti-skip Git ownership verification, OKF contraction, and archival.

## Quota-Aware Model Routing & Packaged Workflows

- **Google Antigravity Dispatch**: Always pass `type_name="self"` in `run_workflow` `agent(...)` and `invoke_subagent(...)` calls with [`plan-schema-card.md`](../templates/agent/plan-schema-card.md) or [`executor-schema-card.md`](../templates/agent/executor-schema-card.md), and prefer shipped workflows (`flow-scout`, `flow-spec-planning`, `flow-chapter-pipeline`, `flow-dual-review`) over ad-hoc scripts ([`skills-subagents-and-mcp-limits.md`](../skills/multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)).
- **Right-Sized Model Allocation**: Keep planning **and** zero-context reviews (`@code-reviewer`, `@quality-reviewer`, spec review) on primary frontier models (preferring next-generation models when available: Gemini Pro / Pro-Next via `inherit` or `pro` on Antigravity with automatic quota fallback to next-gen `flash`; **Opus** on Claude Code with quota fallback to `sonnet`; `high` reasoning on Codex), route multi-file scouts to `flash` (Antigravity) / `sonnet` (Claude Code), and **strictly limit `flash_lite` and `haiku` to narrow `<= 3`-file fetches and trivial mechanical checks—never planning, code/quality review, or closeout**.
- **Anti-Skip Discipline**: Never mark a chapter or task `completed` without `exit 0` verification and Git commits touching declared `files:`/`tests:`, and never mark anything `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

## Structured Decisions (`structured-choice-v1`)

Ask `1` question at a time for dependent architectural forks, and batch `2–3` orthogonal leaf questions per round once on a settled frontier (`skills/flow/references/interaction.md`) with `2–4` choices and `<Label> (Recommended)` first.
