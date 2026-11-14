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
  - `/flow:implement [flow_id] [chapter_id]`: Execute strictly **one chapter** (`1..4` tasks) per invocation. When `tools/model_router.py check-disjoint` confirms `2..4` ready tasks with disjoint `files:`/`tests:` write sets AND worker Flash quota exceeds `25%` on Antigravity, orchestrate a bounded **Small Swarm** (`<= 4` workers total: `1..3` `[Flow Swarm Worker]` `workspace: "share"` writers + `1` zero-context `workspace: "inherit"` verifier, cherry-picking commits in task order before closing). Otherwise run **Chapter-Batch Execution** (`flow-chapter-pipeline`), editing shared files once, validating **once** with the Fast Chapter Gate (`< 60s`), committing code/tests first to capture `<CODE_SHA>`, syncing present-tense OKF/docs + checklists, passing Zero-Context Chapter Review, stamping `last_reviewed_commit`, and stopping cleanly at the chapter boundary. Uncoordinated large swarms (`> 4` workers) remain forbidden.
  - `/flow:status`: Report active flows, `planning_quality` warnings, completed vs. remaining chapters, `empirical_dependent` triggers, and ready tasks.
- **`flow-learn`** (`/flow:learn`, aliases `resynthesize`, `refresh`, `sync`): Anytime drift assessment, worktree reorientation, OKF v0.2 knowledge resynthesis, and `.agents/skills/` + `.agents/agents/` sync.
- **`flow-docs`** (`/flow:docs`): User guides, module/API docs, READMEs, changelogs, signed commits, and clean pull requests (`## Summary` + `## Key Changes` only).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Zero-context review, single full-release-gate run at `/flow:finish`, anti-skip Git ownership verification, OKF contraction, and archival.

## Quota-Aware Model Routing & Packaged Workflows

- **Google Antigravity Dispatch**: Use `tools/model_router.py` with live `swarm(action="models", all=True)` telemetry before planning, scouting, execution, or review. Keep `type_name="self"` as default fallback in `run_workflow` `agent(...)` and `invoke_subagent(...)` calls with [`plan-schema-card.md`](../templates/agent/plan-schema-card.md) or [`executor-schema-card.md`](../templates/agent/executor-schema-card.md), or materialize ephemeral conversation-scoped `runtime-<role>/agent.json` profiles (`materialize-agents`) outside tracked repo files so `run_workflow` binds exact tiers cleanly ([`skills-subagents-and-mcp-limits.md`](../skills/multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)). Note that `post_message`, `read_board`, and `swarm_wait` exist only in Coordinator turns (never inside `run_workflow` scripts).
- **Quota-Aware Model Allocation**: Keep Coordinator, Planner, and Spec Review on the highest-quota frontier Pro model with `>= 25%` quota remaining (Opus on Claude Code; `high` reasoning on Codex), flagging `planning_quality: degraded` whenever quota forces Flash fallback. Route execution writers, diff verifiers, code/quality reviewers, and multi-turn scouts onto high/extra-thinking Flash (`sonnet` on Claude Code), restrict `small_swarm` activation to live worker Flash quota strictly `> 25%`, and restrict lightweight `fast_flash`/`flash_lite`/`haiku` strictly to narrow `<= 3`-file fetches.
- **Anti-Skip Discipline**: Never mark a chapter or task `completed` without `exit 0` verification and Git commits touching declared `files:`/`tests:`, and never mark anything `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

## Structured Decisions (`structured-choice-v1`)

Ask `1` question at a time for dependent architectural forks, and batch `2–3` orthogonal leaf questions per round once on a settled frontier (`skills/flow/references/interaction.md`) with `2–4` choices and `<Label> (Recommended)` first.
