---
trigger: model_decision
description: Flow operational and structured-decision rules evaluated before skills.
---

# Flow Operational Rule

When a repository (or its primary Git worktree) contains `.agents/`, resolve the bundle root from `.agents/setup-state.json` (default `.agents/bundles/`). Inside a linked `git worktree`, reuse the symlinked `.venv` (`uv run --no-sync`), edit worktree `.agents/` when `ignore_policy` is `shared`, and edit the primary checkout's `.agents/` when `local-only`. Read `index.md`, the active specification (`specs/<flow_id>/spec.md`), active chapter (`specs/<flow_id>/chapters/<ch_id>/spec.md` when `has_chapters: true`), task worksheets (`tasks/<id>-<slug>.md`), and applicable `.agents/bundles/knowledge/` chapters before acting.

Use Flow's plain vocabulary ([`vocabulary.md`](../skills/flow/references/vocabulary.md)) in replies, specs, and status updates.

## Lifecycle Routing & Scaling

Route work through [the Flow router](../skills/flow/SKILL.md) and the matching lifecycle skill:

- **`flow-setup`** (`/flow:setup`): Bootstrap or align `.agents/bundles/`, configure `ignore_policy` (`shared` vs. `local-only` with worktree guidance) and `model_routing`, and build `.agents/skills/` + `.agents/agents/`.
- **`flow-planning`**:
  - `/flow:prd <goal>` & `/flow:spec <goal_or_flow_id>` (alias `/flow:plan`): Default cohesive deliverables to a single-chapter `spec.md` + `compact` worksheets (`full` for complex public contracts). Split into `chapters/index.md` + `ch01..chNN` only for real review checkpoints, parallel subsystems (`per_chapter` parallel planning in `flow-spec-planning` for `>= 2` chapters, `1` combined reviewer up to `4` chapters), or `empirical_dependent` boundaries. Validate OKF v0.2 writes via `/flow:validate` and warn whenever `planning_quality: degraded` indicates fallback from the `strong` model role.
  - `/flow:revise <flow_id> [chapter_id] [changes]` (alias `/flow:refine`): Rewrite affected chapter worksheets, root `specs/<flow_id>/spec.md`, and `chapters/index.md` in place in present tense. Validate OKF, re-run independent review on changed chapters, and re-anchor `plan_commit = HEAD`.
  - `/flow:research <topic>` (alias `/flow:task`): Primary-source research and time-boxed `.agents/scratch/<slug>/` spikes promoted to OKF v0.2 `research/<topic>_<YYYYMMDD>.md`.
- **`flow-execution`**:
  - `/flow:implement [flow_id] [chapter_id] [--all]`: Execute one active chapter per run (or consecutive ready non-`empirical_dependent` chapters with `--all`, closing out each chapter before the next). Build task steps and briefs (`<= 250` LOC, `<= 3` files) via `node <plugin_root>/sidecars/studio/flow-cli.mjs tasks plan --flow <id> --chapter <ch> --briefs`. Run steps (`workers` up to `4` on separate files) via **Small Swarm** or `flow-chapter-pipeline`, run `flow-cli.mjs spec sync` between steps, validate once at closeout, and pass independent review ([`orchestration.md`](../skills/flow/references/orchestration.md)). Large uncoordinated swarms (`> 4` workers) remain forbidden.
  - `/flow:status`: Report active flows, `planning_quality` warnings, completed vs. remaining chapters, `empirical_dependent` triggers, and ready tasks.
- **`flow-learn`** (`/flow:learn`, aliases `refresh`, `sync`): Anytime drift audit, worktree catch-up, OKF v0.2 knowledge update, and `.agents/skills/` + `.agents/agents/` sync.
- **`flow-docs`** (`/flow:docs`): User guides, module/API docs, READMEs, changelogs, signed commits, and clean pull requests (`## Summary` + `## Key Changes` only).
- **`flow-completion`** (`/flow:review`, `/flow:finish`, `/flow:archive`, `/flow:cleanup`, `/flow:revert`, `/flow:validate`): Independent review, single full-release check at `/flow:finish`, Git completion verification, OKF capture, and archival.

## Model Routing & Workflows

- **Orchestration CLI & Profiles**: Resolve `(model, effort)` pairs and materialize profiles via `node <plugin_root>/sidecars/studio/flow-cli.mjs` (`models route`, `tasks plan`, `harness delegate`, `spec sync`, `worktree`) ([`orchestration.md`](../skills/flow/references/orchestration.md)). Keep `type_name="self"` as default fallback in `run_workflow` `agent(...)` and `invoke_subagent(...)` calls with [`plan-schema-card.md`](../templates/agent/plan-schema-card.md) or [`executor-schema-card.md`](../templates/agent/executor-schema-card.md) ([`skills-subagents-and-mcp-limits.md`](../skills/multi-harness-plugins/references/skills-subagents-and-mcp-limits.md)). Note that `post_message`, `read_board`, and `swarm_wait` exist only in Coordinator turns (never inside `run_workflow` scripts).
- **Strongest Model for Planning & Review**: Reserve the `strong` model role for planning, independent spec review, semantic validation, and cross-vendor adversarial review. Stamp `planning_quality: degraded` whenever quota constraints force fallback during planning.
- **Completion Discipline**: Never mark a chapter or task `completed` without `exit 0` verification and Git commits touching declared `files:`/`tests:`. Never mark anything `deferred`/`skipped` without `deferred_by: "user"` and `deferred_reason`.

## Structured Decisions

Ask `1` question at a time for dependent architectural forks. Batch `2–3` independent leaf questions per round once open decisions are settled (`skills/flow/references/interaction.md`) with `2–4` choices and `<Label> (Recommended)` first.
